import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "8640692981:AAHhuEPRqzfzIlrrR3Bb6yD2BNy1LGFpFao"
OWNER_ID = 1066185750
WELCOME_IMAGE = "https://postimg.cc/XZ0dPFXJ"

logging.basicConfig(level=logging.INFO)

def get_db():
    return sqlite3.connect("albums.db", check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS albums 
                 (album_name TEXT, file_id TEXT, file_name TEXT, file_type TEXT, uploaded_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# =============== START ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "👋 Hey there! I'm Hari\n\n🌟 Welcome to My Files Bot\n\nChoose an album below:"

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT album_name FROM albums")
    albums = [row[0] for row in c.fetchall()]
    conn.close()

    keyboard = [[InlineKeyboardButton(f"📁 {album}", callback_data=f"show_{album}")] for album in albums]
    if not albums:
        keyboard.append([InlineKeyboardButton("No albums yet", callback_data="dummy")])

    try:
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# =============== ADMIN ===============
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Access Denied!")
        return
    await update.message.reply_text("👑 ADMIN PANEL\nSend file with caption = Album Name")

# =============== BUTTON HANDLER ===============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("show_"):
        album_name = data.replace("show_", "")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT file_id, file_name, file_type FROM albums WHERE album_name=?", (album_name,))
        files = c.fetchall()
        conn.close()

        if not files:
            await context.bot.send_message(query.message.chat_id, f"📭 {album_name} is empty.")
            return

        await context.bot.send_message(query.message.chat_id, f"📤 Sending {len(files)} files from {album_name}...")

        for file_id, name, ftype in files:
            try:
                if ftype == "photo":
                    await context.bot.send_photo(query.message.chat_id, file_id, caption=name)
                elif ftype == "video":
                    await context.bot.send_video(query.message.chat_id, file_id, caption=name)
                else:
                    await context.bot.send_document(query.message.chat_id, file_id, caption=name)
            except:
                continue

        await context.bot.send_message(query.message.chat_id, "✅ All files sent!\nThank you ❤️")

# =============== FILE UPLOAD ===============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return

    if not update.message.caption:
        await update.message.reply_text("Send file with caption = Album Name")
        return

    album_name = update.message.caption.strip()
    file = None
    file_name = "file"
    file_type = "document"

    if update.message.document:
        file = update.message.document
        file_name = file.file_name or "document"
        file_type = "document"
    elif update.message.photo:
        file = update.message.photo[-1]
        file_name = "photo.jpg"
        file_type = "photo"
    elif update.message.video:
        file = update.message.video
        file_name = file.file_name or "video"
        file_type = "video"
    else:
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO albums VALUES (?, ?, ?, ?, ?)",
              (album_name, file.file_id, file_name, file_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ File added to **{album_name}**")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("🚀 Bot Started!")
    app.run_polling()

if __name__ == '__main__':
    main()
