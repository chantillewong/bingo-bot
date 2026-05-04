print("🚀 BOT STARTING...")

import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = "8727437729:AAEGV_NJd8aTNDYoxzwK80Dcl-brWeldreU"
OWNER_ID = 1087116288  # 🔑 ONLY YOU can add admins

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("bingo.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    user_id INTEGER,
    username TEXT,
    box_id INTEGER,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS winner (
    user_id INTEGER,
    username TEXT,
    rank INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY
)
""")

conn.commit()

# =========================
# PROMPTS
# =========================
PROMPTS = {
    1: "Selfie with an elderly age 60 and above.",
    2: "Take a video of your group shouting your unit slogan.",
    3: "A photo with C1F.",
    4: "Wefie with your ship crew.",
    5: "Wefie with another unit's crew and family.",
    6: "Selfie with a child aged 3 and below.",
    7: "Group photo with Ah Meng's statue.",
    8: "Wefie with family in an animal show.",
    9: "Take a photo with DY1F.",
    10: "Take a video of family member feeding an animal.",
    11: "Wefie with a Peacock.",
    12: "Wefie with a Primate.",
    13: "Free space!",
    14: "Wefie with a lion.",
    15: "Wefie with an African Painted Dog.",
    16: "Take a video of your group shouting 1F slogan.",
    17: "Wefie with an animal from the Savannah.",
    18: "Wefie with an Otter.",
    19: "Picture of your family member holding an animal.",
    20: "Wefie with a Giraffe.",
    21: "Wefie with an animal from the rainforest.",
    22: "Wefie with an animal from the Antarctica.",
    23: "Wefie with a Komodo Dragon.",
    24: "A photo with MC1F.",
    25: "Group photo with Inuka Statue."
}

# =========================
# ADMIN SYSTEM
# =========================
def get_admin_ids():
    cursor.execute("SELECT user_id FROM admins")
    return [row[0] for row in cursor.fetchall()]

async def setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can add admins")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setadmin <user_id>")
        return

    new_admin = int(context.args[0])

    cursor.execute("INSERT OR IGNORE INTO admins VALUES (?)", (new_admin,))
    conn.commit()

    await update.message.reply_text(f"✅ Added admin {new_admin}")

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute(
        "INSERT OR IGNORE INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, 13, "approved")
    )
    conn.commit()

    await send_board(context, user.id)

# =========================
# BOARD
# =========================
async def send_board(context, user_id):
    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
        (user_id,)
    )
    completed = [r[0] for r in cursor.fetchall()]

    if 13 not in completed:
        completed.append(13)

    board = ""
    keyboard = []
    row = []

    for i in range(1, 26):
        if i in completed:
            board += "✅ "
            btn = InlineKeyboardButton("✔️", callback_data="blocked")
        elif i == 13:
            board += "🟩 "
            btn = InlineKeyboardButton("FREE", callback_data="blocked")
        else:
            board += "⬜ "
            btn = InlineKeyboardButton(str(i), callback_data=f"box_{i}")

        row.append(btn)

        if i % 5 == 0:
            keyboard.append(row)
            row = []
            board += "\n"

    await context.bot.send_message(
        chat_id=user_id,
        text="📊 Your Board:\n\n" + board,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# SELECT BOX
# =========================
async def select_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    box_id = int(query.data.split("_")[1])
    context.user_data["box"] = box_id

    await query.message.reply_text(
        f"📸 Box {box_id}\n{PROMPTS[box_id]}\n\nSend photo or video!"
    )

# =========================
# HANDLE MEDIA
# =========================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    box_id = context.user_data.get("box")

    if not box_id:
        await update.message.reply_text("Select a box first with /start")
        return

    name = f"@{user.username}" if user.username else f"User {user.id}"

    # prevent duplicate pending
    cursor.execute(
        "SELECT * FROM submissions WHERE user_id=? AND box_id=? AND status='pending'",
        (user.id, box_id)
    )
    if cursor.fetchone():
        await update.message.reply_text("⏳ Already pending approval!")
        return

    # detect media
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        if update.message.video.file_size and update.message.video.file_size > 20_000_000:
            await update.message.reply_text("🚫 Video too large (max 20MB)")
            return
        file_id = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("Send photo or video only")
        return

    cursor.execute(
        "INSERT INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, box_id, "pending")
    )
    conn.commit()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}_{box_id}")
        ]
    ])

    for admin_id in get_admin_ids():
        try:
            if media_type == "photo":
                await context.bot.send_photo(
                    admin_id,
                    file_id,
                    caption=f"{name}\nBox {box_id}\n{PROMPTS[box_id]}",
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_video(
                    admin_id,
                    file_id,
                    caption=f"{name}\nBox {box_id}\n{PROMPTS[box_id]}",
                    reply_markup=keyboard
                )
        except Exception as e:
            print("Admin send error:", e)

    await update.message.reply_text("⏳ Submitted!")

# =========================
# BINGO CHECK
# =========================
def has_bingo(boxes):
    wins = [
        [1,2,3,4,5],[6,7,8,9,10],[11,12,13,14,15],
        [16,17,18,19,20],[21,22,23,24,25],
        [1,6,11,16,21],[2,7,12,17,22],
        [3,8,13,18,23],[4,9,14,19,24],
        [5,10,15,20,25],
        [1,7,13,19,25],[5,9,13,17,21]
    ]
    return any(all(x in boxes for x in combo) for combo in wins)

# =========================
# APPROVAL + WINNERS
# =========================
async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id, box_id = query.data.split("_")
    user_id, box_id = int(user_id), int(box_id)

    if action == "approve":
        cursor.execute(
            "UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?",
            (user_id, box_id)
        )
        conn.commit()

        await query.edit_message_caption(f"✅ Approved Box {box_id}")

        await context.bot.send_message(user_id, f"✅ Approved Box {box_id}")
        await send_board(context, user_id)

        # check bingo
        cursor.execute(
            "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
            (user_id,)
        )
        boxes = [r[0] for r in cursor.fetchall()]

        if 13 not in boxes:
            boxes.append(13)

        if has_bingo(boxes):

            cursor.execute("SELECT COUNT(*) FROM winner")
            count = cursor.fetchone()[0]

            cursor.execute("SELECT 1 FROM winner WHERE user_id=?", (user_id,))
            if cursor.fetchone():
                return

            if count < 15:
                rank = count + 1

                cursor.execute(
                    "INSERT INTO winner VALUES (?, ?, ?)",
                    (user_id, None, rank)
                )
                conn.commit()

                prize = "$10 voucher 💰" if rank <= 5 else "$5 voucher 🎁"

                await context.bot.send_message(
                    user_id,
                    f"🏆 BINGO!\nYou are #{rank}\nPrize: {prize}"
                )

    else:
        cursor.execute(
            "DELETE FROM submissions WHERE user_id=? AND box_id=?",
            (user_id, box_id)
        )
        conn.commit()

        await query.edit_message_caption(f"❌ Rejected Box {box_id}")
        await context.bot.send_message(user_id, f"❌ Rejected Box {box_id}")

# =========================
# BLOCKED
# =========================
async def blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Already done ✅", show_alert=True)

# =========================
# LEADERBOARD
# =========================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT rank FROM winner ORDER BY rank ASC")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No winners yet!")
        return

    text = "🏆 Leaderboard\n\n"
    for i, (rank,) in enumerate(rows, start=1):
        prize = "$10 💰" if rank <= 5 else "$5 🎁"
        text += f"{i}. Winner #{rank} - {prize}\n"

    await update.message.reply_text(text)

# =========================
# APP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setadmin", setadmin))
app.add_handler(CommandHandler("leaderboard", leaderboard))

app.add_handler(CallbackQueryHandler(select_box, pattern="^box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve|reject)_"))
app.add_handler(CallbackQueryHandler(blocked, pattern="^blocked$"))

app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

print("🤖 Bot running...")
app.run_polling()
