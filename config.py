import os

API_ID = int(os.getenv("API_ID", "36595018"))
API_HASH = os.getenv("API_HASH", "0601ef8910a39d5311cb4a6c82879d4c")
BOT_TOKEN = os.getenv("BOT_TOKEN", "9080531950:AAG8FPpzCJ1LgUQIT7Gtk6Q-LoB5J9pjh70")
STRING_SESSION = os.getenv("STRING_SESSION", "AQIuZUoAF0m-GYUwhMFr7zsNl4Y61oQ4hVEU3qBLH845RYnR6kR_IMIdVn6ggdfEksEiKJiqNTSrdSE8Yh1sg2eQpbJ5omx_utkDMhvp_N9s1D_eQuugdc0kHob6IdNlzYz4G3U9XCTAn5B2fopkO5WkhM3n7YEiw2EM0-CIXAac0rRtGPrdSXmv4_vK-78YdM2QMy9-G-mBoQZYvTPpPvRsIKg1RyQBCtBEnIbeFHcUJ9JlBfkfL5c4oL4nTfReYG412kWwpGd8m4Me8qBa9OnldvuTSnoaBY_47jwnofojaG4qsxEjbGxvegjAxZQAkbQ6uvStZI0SHrlARaUQ2t8zYHimIAAAAAINBRvjAA")
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "-1004327297451"))
OWNER_ID = int(os.getenv("OWNER_ID", "7433900109"))
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://likeeadii80_db_user:BvxekuzSBMuULZmv@cluster0.08xzqdo.mongodb.net/?appName=Cluster0")
PORT = int(os.getenv("PORT", "10000"))

# Start message ke buttons ke links (support group / update channel / owner)
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/wizard_likes")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/AdityaXzexxyAPI")
OWNER_URL = os.getenv("OWNER_URL", "https://t.me/NEXOR_BLAZE")

# "Source Code" button (start message) ke liye git repo link — isko sample.env
# / Render env vars mein SOURCE_URL set karke kabhi bhi badla ja sakta hai.
SOURCE_URL = os.getenv("SOURCE_URL", "https://github.com/rameswarm666-source/Aditya-Music.git")

# /start message ke saath jaane wali default image — agar owner ne /addvd
# (ya group ke liye /addvd2) se koi custom media set nahi kiya, to yeh URL
# fallback ke roop mein use hoti hai. Khali chhodne par sirf text jaayega.
START_IMAGE_URL = os.getenv("START_IMAGE_URL", "")

# Render apne aap yeh env variable deta hai (e.g. https://your-app.onrender.com)
# Isse bot khud ko periodically ping karke sleep hone se bachata hai.
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "600"))  # seconds (10 min default)

# Assistant (userbot) ka username — /play chalne par bot check karta hai ki
# yeh account group mein hai ya nahi, aur agar nahi hai to isi username se
# (ya invite link se) join karwane ki koshish karta hai.
ASSISTANT_USERNAME = os.getenv("ASSISTANT_USERNAME", "Mitsuriass")

# /vplay /cvplay ke video ki quality: low (640x360, sabse smooth / kam CPU),
# medium (854x480) ya high (1280x720). Render free tier par "low" hi rakho.
VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "low")
