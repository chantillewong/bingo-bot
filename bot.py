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

TOKEN = "YOUR_TOKEN_HERE"
ADMIN_ID = 1087116288

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
    username TEXT
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
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    # auto add FREE SPACE
    cursor.execute(
        "INSERT OR IGNORE INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, 13, "approved")
    )
    conn.commit()

    keyboard = []
    row = []

    for i in range(1, 26):
        row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []

    await update.message.reply_text(
        "🎮 BINGO! Pick a box:",
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
        f"📸 Box {box_id}\n{PROMPTS[box_id]}\n\nSend your photo!"
    )

# =========================
# HANDLE PHOTO
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    box_id = context.user_data.get("box")

    if not box_id:
        await update.message.reply_text("Please select a box first using /start")
        return

    # check if already done
    cursor.execute(
        "SELECT * FROM submissions WHERE user_id=? AND box_id=? AND status='approved'",
        (user.id, box_id)
    )
    if cursor.fetchone():
        await update.message.reply_text("✅ Already completed!")
        return

    # insert pending
    cursor.execute(
        "INSERT INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, box_id, "pending")
    )
    conn.commit()

    photo = update.message.photo[-1].file_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}_{box_id}")
        ]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo,
        caption=f"{user.username} submitted Box {box_id}\n{PROMPTS[box_id]}",
        reply_markup=keyboard
    )

    await update.message.reply_text("⏳ Submitted! Waiting for approval...")

# =========================
# SEND BOARD
# =========================
async def send_board(context, user_id):
    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
        (user_id,)
    )
    completed = [row[0] for row in cursor.fetchall()]

    if 13 not in completed:
        completed.append(13)

    text = ""
    for i in range(1, 26):
        text += "✅ " if i in completed else "⬜ "
        if i % 5 == 0:
            text += "\n"

    await context.bot.send_message(chat_id=user_id, text=text)

# =========================
# APPROVAL
# =========================
async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id, box_id = query.data.split("_")
    user_id = int(user_id)
    box_id = int(box_id)

    if action == "approve":
        cursor.execute(
            "UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?",
            (user_id, box_id)
        )
        conn.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Approved!\nBox {box_id}: {PROMPTS[box_id]}"
        )

        await send_board(context, user_id)

        # check bingo
        cursor.execute(
            "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
            (user_id,)
        )
        completed = [row[0] for row in cursor.fetchall()]

        if 13 not in completed:
            completed.append(13)

        if has_bingo(completed):
            await context.bot.send_message(
                chat_id=user_id,
                text="🏆 BINGO!"
            )

        await query.message.reply_text("✅ Approved")

    elif action == "reject":
        cursor.execute(
            "DELETE FROM submissions WHERE user_id=? AND box_id=?",
            (user_id, box_id)
        )
        conn.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Rejected.\nBox {box_id}: {PROMPTS[box_id]}\nTry again!"
        )

        await query.message.reply_text("❌ Rejected")

# =========================
# BINGO CHECK
# =========================
def has_bingo(boxes):
    wins = [
        [1,2,3,4,5],
        [6,7,8,9,10],
        [11,12,13,14,15],
        [16,17,18,19,20],
        [21,22,23,24,25],
        [1,6,11,16,21],
        [2,7,12,17,22],
        [3,8,13,18,23],
        [4,9,14,19,24],
        [5,10,15,20,25],
        [1,7,13,19,25],
        [5,9,13,17,21]
    ]

    return any(all(x in boxes for x in combo) for combo in wins)

# =========================
# BOARD COMMAND
# =========================
async def board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_board(context, update.message.from_user.id)

# =========================
# APP SETUP (THIS WAS MISSING)
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("board", board))

app.add_handler(CallbackQueryHandler(select_box, pattern="^box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve|reject)_"))

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("🤖 Bot is running...")
app.run_polling()
