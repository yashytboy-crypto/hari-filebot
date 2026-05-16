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
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT, last_used TEXT)''')
    conn.commit()
    conn.close()

init_db()

def is_owner(user_id):
    return user_id == OWNER_ID

# =============== START ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    now = datetime.now().isoformat()

    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users (user_id, username, first_name, joined_at, last_used)
                 VALUES (?, ?, ?, COALESCE((SELECT joined_at FROM users WHERE user_id=?), ?), ?)""",
              (user.id, user.username, user.first_name, user.id, now, now))
    conn.commit()
    conn.close()

    welcome_text = "👋 Hey there! I'm Hari\n\n🌟 Welcome to My Files Bot\n\nChoose an album below:"
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT album_name FROM albums")
    albums = [row[0] for row in c.fetchall()]
    conn.close()

    keyboard = []
    for i, album in enumerate(albums):
        context.bot_data[f"a{i}"] = album
        keyboard.append([InlineKeyboardButton(f"📁 {album}", callback_data=f"a{i}")])

    if not albums:
        keyboard.append([InlineKeyboardButton("No albums yet", callback_data="dummy")])

    try:
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# =============== PREMIUM ADMIN PANEL ===============
def admin_dashboard():
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="broadcast")],
        [InlineKeyboardButton("➕ Create New Album", callback_data="create_album")],
        [InlineKeyboardButton("📋 Manage Albums", callback_data="manage_albums")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.message.from_user.id):
        await update.message.reply_text("❌ Access Denied!")
        return
    await update.message.reply_text("👑 **PREMIUM ADMIN PANEL**", reply_markup=admin_dashboard())

# =============== BUTTON HANDLER ===============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("a"):
        album_name = context.bot_data.get(data)
        if not album_name:
            await context.bot.send_message(query.message.chat_id, "Album not found.")
            return

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

    # Admin Features
    elif is_owner(query.from_user.id):
        if data == "stats":
            await show_stats(query)
        elif data == "broadcast":
            await query.edit_message_text("📢 Send your message to broadcast to all users:")
            context.user_data['action'] = 'waiting_broadcast'
        elif data == "create_album":
            await query.edit_message_text("✍️ Send new album name:")
            context.user_data['action'] = 'waiting_album_name'
        elif data == "manage_albums":
            await show_manage_albums(query)

# =============== ADMIN FEATURES ===============
async def show_stats(query):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(DISTINCT album_name) FROM albums"); albums = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM albums"); files = c.fetchone()[0] or 0
    c.execute("SELECT MAX(uploaded_at) FROM albums"); last_upload = c.fetchone()[0] or "Never"
    conn.close()

    text = (
        "📊 **BEST STATISTICS**\n\n"
        f"👥 Total Users     : {users}\n"
        f"📂 Total Albums    : {albums}\n"
        f"📄 Total Files     : {files}\n"
        f"🕒 Last Upload     : {last_upload}"
    )
    await query.edit_message_text(text, reply_markup=admin_dashboard())

async def show_manage_albums(query):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT album_name, COUNT(*) FROM albums GROUP BY album_name")
    albums = c.fetchall()
    conn.close()

    text = "📋 **Manage Albums**\n\n"
    keyboard = []
    for album, count in albums:
        keyboard.append([
            InlineKeyboardButton(f"📤 {album} ({count})", callback_data=f"show_{album}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"del_{album}")
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_admin")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# =============== MESSAGE HANDLER ===============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.message.from_user.id):
        return

    action = context.user_data.get('action')

    if action == 'waiting_album_name':
        album_name = update.message.text.strip()
        context.user_data['current_album'] = album_name
        context.user_data['action'] = 'uploading_files'
        await update.message.reply_text(f"✅ Album **{album_name}** started!\nSend files now.\nType /done when finished.")
        return

    if action == 'uploading_files':
        album_name = context.user_data['current_album']
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

        await update.message.reply_text(f"✅ Added to **{album_name}**")

    if update.message.text and update.message.text.lower() in ["/done", "done"]:
        if context.user_data.get('action') == 'uploading_files':
            album = context.user_data['current_album']
            context.user_data.clear()
            await update.message.reply_text(f"🎉 Album **{album}** is now live!")

    if action == 'waiting_broadcast':
        message_text = update.message.text or update.message.caption or "Broadcast message"
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.close()

        sent = 0
        for (user_id,) in users:
            try:
                await context.bot.send_message(user_id, f"📢 **Broadcast Message**\n\n{message_text}")
                sent += 1
            except:
                continue

        context.user_data.clear()
        await update.message.reply_text(f"✅ Message sent to **{sent}** users!")

# =============== MAIN ===============
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("done", handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("🚀 Premium Bot Started!")
    app.run_polling()

if __name__ == '__main__':
    main()
