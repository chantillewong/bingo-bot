import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8727437729:AAHPumcPZMKOm4kPoRPriV_l-7z9En3ULFU"
ADMIN_ID = 1087116288  # replace with your Telegram user ID

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
CREATE TABLE IF NOT EXISTS submissions (
    user_id INTEGER,
    username TEXT,
    box_id INTEGER,
    status TEXT
)
""")

conn.commit()

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
    22: "Wefie with an animal from the Antartica.",
    23: "Wefie with a Komodo Dragon.",
    24: "A photo with MC1F.",
    25: "Group photo with Inuka Statue."
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    # ⭐ FREE SPACE AUTO COMPLETE
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
        "Choose a box to submit:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
        (user.id,)
    )
    completed = [row[0] for row in cursor.fetchall()]

    text = ""
    for i in range(1, 26):
        if i in completed:
            text += "✅ "
        else:
            text += "⬜ "

        if i % 5 == 0:
            text += "\n"

    await update.message.reply_text(text)
    
async def select_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    box_id = int(query.data.split("_")[1])
    context.user_data["box"] = box_id

    await query.message.reply_text(
    f"You selected Box {box_id}:\n{PROMPTS[box_id]}\n\nSend your photo 📸"
)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    box_id = context.user_data.get("box")

    if not box_id:
        await update.message.reply_text("Please select a box first using /start")
        return

    # 🚫 NEW CHECK (ADD THIS)
    cursor.execute(
        "SELECT * FROM submissions WHERE user_id=? AND box_id=? AND status='approved'",
        (user.id, box_id)
    )

    if cursor.fetchone():
        await update.message.reply_text("You already completed this box!")
        return

    # ✅ EXISTING CODE
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

    await update.message.reply_text("Submitted! Waiting for approval.")
    
async def send_board(context, user_id):
    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
        (user_id,)
    )
    completed = [row[0] for row in cursor.fetchall()]

    text = ""
    for i in range(1, 26):
        if i in completed:
            text += "✅ "
        else:
            text += "⬜ "

        if i % 5 == 0:
            text += "\n"

    await context.bot.send_message(chat_id=user_id, text=text)
    
if action == "approve":
    cursor.execute(
        "UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?",
        (user_id, box_id)
    )
    conn.commit()

    # notify user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Approved!\nBox {box_id}: {PROMPTS[box_id]}"
    )

    # 🔥 NEW: send updated board
    await send_board(context, user_id)

        cursor.execute(
            "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
            (user_id,)
        )
        completed = [row[0] for row in cursor.fetchall()]

        if has_bingo(completed):
            cursor.execute("SELECT * FROM winner")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO winner VALUES (?, ?)", (user_id, query.from_user.username))
                conn.commit()

                await query.message.reply_text(f"🏆 @{query.from_user.username} GOT BINGO FIRST!")

    await query.message.reply_text("Done.")

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

    for combo in wins:
        if all(x in boxes for x in combo):
            return True
    return False
    
async def board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
        (user.id,)
    )
    completed = [row[0] for row in cursor.fetchall()]

    text = ""
    for i in range(1, 26):
        if i in completed:
            text += "✅ "
        else:
            text += "⬜ "

        if i % 5 == 0:
            text += "\n"

    await update.message.reply_text(text)
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("board", board))
app.add_handler(CallbackQueryHandler(select_box, pattern="box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="approve_|reject_"))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(CommandHandler("board", board))
app.run_polling()
