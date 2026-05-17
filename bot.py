import os
import re
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import yt_dlp

# ========================
# SOZLAMALAR
# ========================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # @8992614547:AAEjBt6bxo2kl4ydXOmXWxds2i8k4IfizY0

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================
# URL ANIQLASH
# ========================
def is_valid_url(text: str) -> bool:
    pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|vm\.tiktok\.com|music\.youtube\.com)[\S]+"
    return bool(re.search(pattern, text))

def get_platform(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube 🎬"
    elif "instagram.com" in url:
        return "Instagram 📸"
    elif "tiktok.com" in url:
        return "TikTok 🎵"
    return "Noma'lum"

# ========================
# VIDEO MA'LUMOTLARINI OLISH
# ========================
def get_video_info(url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Noma'lum sarlavha"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Noma'lum"),
            "thumbnail": info.get("thumbnail", ""),
        }

# ========================
# YUKLAB OLISH FUNKSIYALARI
# ========================
def download_audio(url: str, filename: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path + ".%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path + ".mp3"

def download_video(url: str, filename: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path + ".%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path + ".mp4"

# ========================
# HANDLERS
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎵 *Musiqa va Video Yuklovchi Bot*\n\n"
        "Qo'llab-quvvatlanadigan platformalar:\n"
        "• YouTube 🎬\n"
        "• Instagram 📸\n"
        "• TikTok 🎵\n\n"
        "Faqat video havolasini yuboring va men:\n"
        "✅ MP3 audio yuklab beraman\n"
        "✅ MP4 video yuklab beraman\n\n"
        "Boshlash uchun havola yuboring! 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Yordam*\n\n"
        "1. YouTube, Instagram yoki TikTok havolasini yuboring\n"
        "2. Bot sizga 2 ta variant taklif qiladi:\n"
        "   🎵 Faqat musiqa (MP3)\n"
        "   🎬 To'liq video (MP4)\n"
        "3. Kerakli variantni tanlang\n"
        "4. Yuklanishini kuting!\n\n"
        "⚠️ *Eslatma:* Katta fayllar biroz vaqt olishi mumkin."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ Bu to'g'ri havola emas!\n\n"
            "YouTube, Instagram yoki TikTok havolasini yuboring."
        )
        return

    platform = get_platform(url)
    processing_msg = await update.message.reply_text(
        f"🔍 *{platform}* dan ma'lumot olinmoqda...",
        parse_mode="Markdown"
    )

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_video_info, url)

        duration_min = info['duration'] // 60
        duration_sec = info['duration'] % 60

        caption = (
            f"🎵 *{info['title']}*\n"
            f"👤 {info['uploader']}\n"
            f"⏱ {duration_min}:{duration_sec:02d}\n"
            f"📡 {platform}\n\n"
            "Qaysi formatda yuklamoqchisiz?"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎵 MP3 Audio", callback_data=f"audio|{url}"),
                InlineKeyboardButton("🎬 MP4 Video", callback_data=f"video|{url}"),
            ]
        ])

        await processing_msg.delete()
        await update.message.reply_text(
            caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"URL xatosi: {e}")
        await processing_msg.edit_text(
            "❌ Havola ochilmadi. Iltimos tekshirib qayta yuboring.\n\n"
            f"Sabab: `{str(e)[:100]}`",
            parse_mode="Markdown"
        )

async def handle_download_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|", 1)
    mode = data[0]   # "audio" yoki "video"
    url = data[1]

    user_id = query.from_user.id
    filename = f"{user_id}_{hash(url) % 100000}"

    status_msg = await query.edit_message_text(
        "⏳ Yuklanmoqda... Biroz kuting 🎵" if mode == "audio" else "⏳ Video yuklanmoqda... Biroz kuting 🎬"
    )

    try:
        loop = asyncio.get_event_loop()

        if mode == "audio":
            file_path = await loop.run_in_executor(None, download_audio, url, filename)
            await status_msg.edit_text("📤 Yuborilmoqda...")
            with open(file_path, "rb") as f:
                await query.message.reply_audio(
                    audio=f,
                    caption="🎵 Musiqa yuklab olindi!\n_@YourBotUsername_",
                    parse_mode="Markdown"
                )
        else:
            file_path = await loop.run_in_executor(None, download_video, url, filename)
            await status_msg.edit_text("📤 Video yuborilmoqda...")
            with open(file_path, "rb") as f:
                await query.message.reply_video(
                    video=f,
                    caption="🎬 Video yuklab olindi!\n_@YourBotUsername_",
                    parse_mode="Markdown"
                )

        # Faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Yuklash xatosi: {e}")
        await status_msg.edit_text(
            "❌ Yuklashda xato yuz berdi!\n\n"
            "Sabablari:\n"
            "• Video yopiq/o'chirilgan\n"
            "• Fayl juda katta (50MB+)\n"
            "• Tarmoq muammosi\n\n"
            f"`{str(e)[:150]}`",
            parse_mode="Markdown"
        )

# ========================
# ASOSIY FUNKSIYA
# ========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_download_choice))

    logger.info("Bot ishga tushdi! ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
