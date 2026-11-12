import os
import re
import asyncio
import aiohttp
from urllib.parse import urlencode, urljoin
import time
import json
from youtube_search import YoutubeSearch

# Naye env names jaan-bujhkar rakhe hain (DOWNLOAD_API_*) taaki Render par purane
# API_URL / API_KEY (nexor wale) galti se override na kar dein.
DOWNLOAD_API_URL = os.environ.get("DOWNLOAD_API_URL", "https://api.riteshyt.in")
DOWNLOAD_API_KEY = os.environ.get("DOWNLOAD_API_KEY", "riteshfreebc037f3c187a34610b8a04dc")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def search_youtube(query: str):
    """YouTube pe search karta hai, pehla result deta hai (raw dict, library format)."""
    loop = asyncio.get_event_loop()

    def _search():
        results = YoutubeSearch(query, max_results=1).to_dict()
        return results[0] if results else None

    return await loop.run_in_executor(None, _search)


async def search_track(query: str):
    """search_youtube ka normalized wrapper — id/title/duration/thumbnail/url deta hai."""
    result = await search_youtube(query)
    if not result:
        return None

    thumbnails = result.get("thumbnails") or []
    video_id = result.get("id")

    return {
        "id": video_id,
        "title": result.get("title", "Unknown"),
        "duration": result.get("duration", ""),
        "thumbnail": thumbnails[0] if thumbnails else None,
        "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
    }


# ---------------------------------------------------------------------------
# YouTube LINK support — /play /vplay /cplay /cvplay sab jagah query ki jagah
# link do (youtube.com/watch?v=, youtu.be/, shorts/, live/, embed/, music.youtube.com)
# to link se video id nikaal kar wahi track chalta hai (search nahi hota).
# ---------------------------------------------------------------------------
_YT_ID = r"([0-9A-Za-z_-]{11})(?![0-9A-Za-z_-])"
_YT_PATTERNS = [
    re.compile(r"youtu\.be/" + _YT_ID),
    re.compile(r"youtube(?:-nocookie)?\.com/(?:shorts|embed|live|v)/" + _YT_ID),
    re.compile(r"youtube\.com/watch\?(?:[^\s#]*&)?v=" + _YT_ID),
]


def extract_video_id(text: str):
    """Text/link mein YouTube video id dhoondta hai (nahi mile to None)."""
    for pat in _YT_PATTERNS:
        m = pat.search(text or "")
        if m:
            return m.group(1)
    return None


def _fmt_duration(sec) -> str:
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return ""
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


async def track_from_id(video_id: str):
    """Video id se track dict (id/title/duration/thumbnail/url) banata hai.
    1) YouTube search (id se) 2) yt-dlp metadata 3) oEmbed (duration ke bina)."""
    loop = asyncio.get_event_loop()
    url = f"https://www.youtube.com/watch?v={video_id}"

    def _by_search():
        for r in YoutubeSearch(video_id, max_results=5).to_dict() or []:
            if r.get("id") == video_id:
                return r
        return None

    try:
        r = await loop.run_in_executor(None, _by_search)
    except Exception:
        r = None
    if r:
        thumbs = r.get("thumbnails") or []
        return {
            "id": video_id, "title": r.get("title", "Unknown"),
            "duration": r.get("duration", ""),
            "thumbnail": thumbs[0] if thumbs else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "url": url,
        }

    def _by_ytdlp():
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await asyncio.wait_for(loop.run_in_executor(None, _by_ytdlp), timeout=30)
        if info and info.get("title"):
            return {
                "id": video_id, "title": info["title"],
                "duration": _fmt_duration(info.get("duration")),
                "thumbnail": info.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "url": url,
            }
    except Exception:
        pass

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.youtube.com/oembed", params={"url": url, "format": "json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    return {
                        "id": video_id, "title": data.get("title", "Unknown"), "duration": "",
                        "thumbnail": data.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                        "url": url,
                    }
    except Exception:
        pass
    return None


async def resolve_track(query: str):
    """Query mein YouTube link ho to uski video id se, warna naam se search karta hai."""
    vid = extract_video_id(query)
    if vid:
        return await track_from_id(vid)
    return await search_track(query)


async def search_related_track(seed_title: str, exclude_ids=None):
    """Autoplay ke liye 'related' track dhoondta hai — seed track ke title se
    hi search karke, pehli aisi result jo already play na ho chuki ho (exclude_ids
    mein na ho) use karta hai. YouTube ka koi official 'related videos' API
    yahan use nahi ho raha (youtube_search library isse support nahi karti),
    isliye yeh best-effort approximation hai."""
    exclude_ids = exclude_ids or set()
    loop = asyncio.get_event_loop()

    def _search():
        results = YoutubeSearch(seed_title, max_results=6).to_dict()
        return results

    results = await loop.run_in_executor(None, _search)
    for r in results or []:
        vid = r.get("id")
        if vid and vid not in exclude_ids:
            thumbnails = r.get("thumbnails") or []
            return {
                "id": vid,
                "title": r.get("title", "Unknown"),
                "duration": r.get("duration", ""),
                "thumbnail": thumbnails[0] if thumbnails else None,
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
    return None


_URL_KEYS = (
    "download_url", "downloadUrl", "download", "stream_url", "streamUrl",
    "audio_url", "audioUrl", "url", "link", "file", "result", "data",
)


def _find_url(obj):
    """JSON response ke andar se pehla http(s) link dhoondta hai."""
    if isinstance(obj, str):
        if obj.startswith(("http://", "https://")):
            return obj
        if obj.startswith("/") and obj.lower().endswith((".mp3", ".m4a", ".webm", ".opus", ".ogg", ".mp4")):
            return obj
        return None
    if isinstance(obj, dict):
        for k in _URL_KEYS:
            if k in obj:
                found = _find_url(obj[k])
                if found:
                    return found
        for v in obj.values():
            found = _find_url(v)
            if found:
                return found
    if isinstance(obj, list):
        for v in obj:
            found = _find_url(v)
            if found:
                return found
    return None


async def _resolve_link(video_id: str) -> str:
    """
    riteshyt API se audio link banata hai:
    https://api.riteshyt.in/download?query=<VIDEO_ID>&dl_type=audio&api_key=<KEY>

    - Agar API seedha audio file/stream deta hai -> final URL (redirect ke baad)
      hi pytgcalls ko de dete hain.
    - Agar API JSON deta hai -> usme se download/stream link nikal lete hain.
    - "processing" jaisa status aaye to 3 baar retry karta hai.
    """
    params = urlencode({"query": video_id, "dl_type": "audio", "api_key": DOWNLOAD_API_KEY})
    api_url = f"{DOWNLOAD_API_URL.rstrip('/')}/download?{params}"

    last_err = "unknown error"
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=40),
                    allow_redirects=True,
                ) as resp:
                    if resp.status >= 400:
                        last_err = f"API ne status {resp.status} diya"
                        await asyncio.sleep(2)
                        continue

                    ctype = (resp.headers.get("Content-Type") or "").lower()

                    # Seedha audio/binary stream -> body padhe bina URL return
                    if ctype.startswith(("audio/", "video/")) or "octet-stream" in ctype:
                        return str(resp.url)

                    body = await resp.text()
                    try:
                        data = json.loads(body)
                    except ValueError:
                        last_err = "API ka response samajh nahi aaya"
                        await asyncio.sleep(2)
                        continue

                    link = _find_url(data)
                    if link:
                        return urljoin(api_url, link)  # relative path ho to bhi chalega

                    last_err = f"API ne link nahi diya: {str(data)[:150]}"
                    await asyncio.sleep(3)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_err = f"API tak pahunch nahi paaye: {e}"
            await asyncio.sleep(2)

    raise Exception(last_err)


def _cleanup_old_files(max_age_sec: int = 6 * 3600):
    now = time.time()
    try:
        for name in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, name)
            if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_sec:
                try:
                    os.remove(path)
                except OSError:
                    pass
    except OSError:
        pass


async def get_stream_url(video_id: str) -> str:
    """
    API se link lekar audio ko LOCAL file mein download karta hai aur us file
    ka path return karta hai. (pytgcalls ko http link dene par 'No such file
    or directory' error aa raha tha, local file se woh problem nahi aati.)
    Pehle se downloaded file ho to wahi reuse hoti hai.
    """
    safe_id = "".join(ch for ch in str(video_id) if ch.isalnum() or ch in "-_")
    final_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, f"{safe_id}.mp3"))

    if os.path.isfile(final_path) and os.path.getsize(final_path) > 20_000:
        return final_path

    _cleanup_old_files()
    link = await _resolve_link(video_id)
    tmp_path = final_path + ".part"

    last_err = "download fail"
    for attempt in range(6):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link, timeout=aiohttp.ClientTimeout(total=180)) as resp:
                    if resp.status >= 400:
                        last_err = f"file download status {resp.status}"
                        await asyncio.sleep(3)  # file shayad abhi ban rahi hai
                        continue
                    with open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            f.write(chunk)
            with open(tmp_path, "rb") as f:
                head = f.read(16).lstrip()
            if os.path.getsize(tmp_path) < 20_000 or head[:1] in (b"<", b"{"):
                last_err = "downloaded file audio nahi hai (error page/JSON mila)"
                await asyncio.sleep(3)
                continue
            os.replace(tmp_path, final_path)
            return final_path
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            last_err = f"download error: {e}"
            await asyncio.sleep(2)

    try:
        os.remove(tmp_path)
    except OSError:
        pass
    raise Exception(last_err)


# ---------------------------------------------------------------------------
# VIDEO (/vplay /cvplay) — riteshyt API:
#   {DOWNLOAD_API_URL}/downloads/{DOWNLOAD_API_KEY}/youtube.com/{video_id}.mp4?quality=360
# Audio ki tarah video bhi pehle LOCAL file mein download hoti hai, phir
# pytgcalls ko local path milta hai — isse stream beech mein atakti nahi
# (live http link par ffmpeg network jitter se hichkichata hai).
# ---------------------------------------------------------------------------
VIDEO_QUALITY_PX = os.environ.get("VIDEO_API_QUALITY", "360")


def build_video_url(video_id: str) -> str:
    base = DOWNLOAD_API_URL.rstrip("/")
    return f"{base}/downloads/{DOWNLOAD_API_KEY}/youtube.com/{video_id}.mp4?quality={VIDEO_QUALITY_PX}"


async def get_video_path(video_id: str) -> str:
    """Video ko API se local .mp4 mein download karke uska path deta hai.
    Pehle se downloaded ho to wahi reuse hota hai."""
    safe_id = "".join(ch for ch in str(video_id) if ch.isalnum() or ch in "-_")
    final_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, f"{safe_id}_{VIDEO_QUALITY_PX}.mp4"))

    if os.path.isfile(final_path) and os.path.getsize(final_path) > 100_000:
        try:
            os.utime(final_path, None)  # cleanup isse beech mein delete na kare
        except OSError:
            pass
        return final_path

    _cleanup_old_files()
    url = build_video_url(safe_id)
    tmp_path = final_path + ".part"

    last_err = "video download fail"
    for attempt in range(10):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    if resp.status >= 400:
                        # file shayad abhi API par ban rahi hai — thoda ruk ke retry
                        last_err = f"video API status {resp.status}"
                        await asyncio.sleep(4)
                        continue
                    with open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(128 * 1024):
                            f.write(chunk)
            with open(tmp_path, "rb") as f:
                head = f.read(16).lstrip()
            if os.path.getsize(tmp_path) < 100_000 or head[:1] in (b"<", b"{"):
                last_err = "downloaded file video nahi hai (error page/JSON mila)"
                await asyncio.sleep(4)
                continue
            os.replace(tmp_path, final_path)
            return final_path
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            last_err = f"video download error: {e}"
            await asyncio.sleep(3)

    try:
        os.remove(tmp_path)
    except OSError:
        pass
    raise Exception(last_err)
