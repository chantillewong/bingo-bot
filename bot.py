import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import os
TOKEN = os.getenv("TOKEN")
ADMIN_ID = [1087116288]

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
    25: "Group photo with Inuka Statue.",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []

    for i in range(1, 26):
        row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []

    await update.message.reply_photo(
        photo=open("bingo.jpg", "rb"),
        caption="🎉 Photo Bingo!\nSelect a box below to submit your photo 📸",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    box_id = int(query.data.split("_")[1])

    # 🟩 FREE SPACE BLOCK
    if box_id == 13:
        await query.answer("🟩 Free space! No photo needed", show_alert=True)
        return

    context.user_data["box"] = box_id

    await query.message.reply_text(
        f"📸 Box {box_id}\n{PROMPTS[box_id]}\n\nSend your photo!"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    box_id = context.user_data.get("box")

    if not box_id:
        await update.message.reply_text("Please select a box first using /start")
        return

    # 🔍 Check if already submitted
    cursor.execute(
        "SELECT status FROM submissions WHERE user_id=? AND box_id=?",
        (user.id, box_id)
    )
    result = cursor.fetchone()

    if result:
        if result[0] == "pending":
            await update.message.reply_text("⏳ You already submitted this. Waiting for approval.")
        else:
            await update.message.reply_text("✅ You already completed this box!")
        return

    # ✅ Save as pending
    cursor.execute(
        "INSERT INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, box_id, "pending")
    )
    conn.commit()

    photo = update.message.photo[-1].file_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejectmenu_{user.id}_{box_id}")
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

    # ⭐ free space
    if 13 not in completed:
        completed.append(13)

    board_text = ""
    keyboard = []
    row = []

    for i in range(1, 26):

        # 🟩 FREE SPACE
        if i == 13:
            board_text += "🟩 "
            row.append(InlineKeyboardButton("FREE", callback_data="blocked"))

        # ✅ COMPLETED
        elif i in completed:
            board_text += "✅ "
            row.append(InlineKeyboardButton("✔️", callback_data="blocked"))

        # ⬜ NOT DONE
        else:
            board_text += "⬜ "
            row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))

        if len(row) == 5:
            keyboard.append(row)
            row = []
            board_text += "\n"

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📊 Your Updated Board:\n\n{board_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
# =========================
# APPROVAL + REJECTION FLOW
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

        # ✅ notify user
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Approved!\nBox {box_id}: {PROMPTS[box_id]}"
        )
        
        # ✅ send updated board
        await send_board(context, user_id)

                # 🏆 check bingo
        cursor.execute(
            "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
            (user_id,)
        )
        completed = [row[0] for row in cursor.fetchall()]
        if 13 not in completed:
            completed.append(13)

        if has_bingo(completed):
            cursor.execute("SELECT COUNT(*) FROM winner")
            count = cursor.fetchone()[0]

            if count < 15:
                rank = count + 1

                cursor.execute(
                    "INSERT INTO winner VALUES (?, ?, ?)",
                    (user_id, query.from_user.username, rank)
                )
                conn.commit()

                # 🎁 prize
                if rank <= 5:
                    prize = "$10 voucher 💰"
                else:
                    prize = "$5 voucher 🎁"

                # 📢 notify admins
username = query.from_user.username or "User"

for admin_id in ADMIN_IDS:
    await context.bot.send_message(
        chat_id=admin_id,
        text=(
            f"🏆 NEW WINNER\n"
            f"User: @{username}\n"
            f"User ID: {user_id}\n"
            f"Rank: #{rank}\n"
            f"Prize: {prize}"
        )
    )

                # notify user
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🏆 BINGO!\nYou are winner #{rank}!\nYou won a {prize}"
                )

                
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🎉 BINGO! All prizes have been claimed."
                )
                
async def blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print("BLOCKED CLICK DETECTED")
    await query.answer("Already completed ✅", show_alert=True)

# =========================
# STEP 1: SHOW REJECT MENU
# =========================

async def reject_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, user_id, box_id = query.data.split("_")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Wrong prompt", callback_data=f"reject_wrong_{user_id}_{box_id}")],
        [InlineKeyboardButton("📷 Blurry photo", callback_data=f"reject_blurry_{user_id}_{box_id}")],
        [InlineKeyboardButton("🤔 Not clear", callback_data=f"reject_unclear_{user_id}_{box_id}")],
        [InlineKeyboardButton("❗ Other", callback_data=f"reject_other_{user_id}_{box_id}")]
    ])

    await query.message.reply_text("Select rejection reason:", reply_markup=keyboard)


# =========================
# STEP 2: HANDLE REJECTION
# =========================

async def handle_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    reason = parts[1]
    user_id = int(parts[2])
    box_id = int(parts[3])

    reason_text = {
        "wrong": "❌ Wrong prompt",
        "blurry": "📷 Photo is too blurry",
        "unclear": "🤔 Submission is unclear",
        "other": "❗ Not accepted"
    }

    # ❌ notify user
    await context.bot.send_message(
        chat_id=user_id,
        text=f"{reason_text[reason]}\nBox {box_id}: {PROMPTS[box_id]}\nPlease try again!"
    )

    # ❌ remove pending submission so they can retry
    cursor.execute(
        "DELETE FROM submissions WHERE user_id=? AND box_id=? AND status='pending'",
        (user_id, box_id)
    )
    conn.commit()

    await query.message.reply_text("Rejected with reason.")

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

    # ⭐ free space
    if 13 not in completed:
        completed.append(13)

    board_text = ""

    for i in range(1, 26):
        if i in completed:
            board_text += "✅ "
        else:
            board_text += "⬜ "

        if i % 5 == 0:
            board_text += "\n"

    await update.message.reply_text(f"Your Bingo Board:\n\n{board_text}")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT username, rank FROM winner ORDER BY rank ASC"
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No winners yet!")
        return

    text = "🏆 Leaderboard\n\n"

    for username, rank in rows:
        if rank <= 5:
            prize = "$10 voucher 💰"
        else:
            prize = "$5 voucher 🎁"

        name = f"@{username}" if username else "User"
        text += f"{rank}. {name} - {prize}\n"

    await update.message.reply_text(text)
    
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("board", board))
app.add_handler(CallbackQueryHandler(blocked, pattern="^blocked$"))
app.add_handler(CallbackQueryHandler(select_box, pattern="box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="^approve_"))
app.add_handler(CallbackQueryHandler(reject_menu, pattern="^rejectmenu_"))
app.add_handler(CallbackQueryHandler(handle_reject_reason, pattern="^reject_"))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.run_polling()
