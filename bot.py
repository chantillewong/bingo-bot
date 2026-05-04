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

TOKEN = "8727437729:AAH3Rdv4_weINeeZ7VW2AYxq6RumOT4Q9zc"
ADMIN_ID = 1087116288

# =========================
# DATABASE
# =========================
conn = sqlite3.connect("bingo.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    user_id INTEGER,
    username TEXT,
    box_id INTEGER,
    status TEXT,
    UNIQUE(user_id, box_id)
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
# UTILITY HANDLERS
# =========================
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"Your ID: {user_id}")

    # test sending to yourself via bot API
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Bot can message you"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending to YOU: {e}")

    # test admin send
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="✅ Bot can message admin"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending to ADMIN: {e}")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(update.message.from_user.id))
#Broadcast 

async def broadcast(context, message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for (user_id,) in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except:
            pass  # ignore users who blocked bot
            
# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user.id, user.username)
    )
    conn.commit()

    # ⭐ Auto-complete FREE space
    cursor.execute(
        "INSERT OR IGNORE INTO submissions (user_id, username, box_id, status) VALUES (?, ?, ?, ?)",
        (user.id, user.username, 13, "approved")
    )
    conn.commit()

    # GET COMPLETED BOXES
    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
        (user.id,)
    )
    completed = [row[0] for row in cursor.fetchall()]

    if 13 not in completed:
        completed.append(13)

    # BUILD BOARD TEXT
    board_text = ""
    for i in range(1, 26):
        board_text += "✅ " if i in completed else "⬜ "
        if i % 5 == 0:
            board_text += "\n"

    # BUILD BUTTON GRID
    keyboard = []
    row = []
    for i in range(1, 26):
        if i == 13:
            row.append(InlineKeyboardButton("FREE", callback_data="blocked"))
        elif i in completed:
            row.append(InlineKeyboardButton("✔️", callback_data="blocked"))
        else:
            row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))

        if len(row) == 5:
            keyboard.append(row)
            row = []

    reply_markup = InlineKeyboardMarkup(keyboard)

    # MESSAGE 1 → IMAGE + BUTTONS
    try:
        with open("bingo.jpg", "rb") as img:
            await update.message.reply_photo(
                photo=img,
                caption="🎮 BINGO!\nPick a box:",
                reply_markup=reply_markup
            )
    except FileNotFoundError:
        await update.message.reply_text("🎮 BINGO!\nPick a box:", reply_markup=reply_markup)

    # MESSAGE 2 → BOARD TEXT
    await update.message.reply_text(f"📊 Your Board:\n\n{board_text}")

# =========================
# SELECT BOX
# =========================
async def select_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    box_id = int(query.data.split("_")[1])
    context.user_data["box"] = box_id

    await query.message.reply_text(
        f"📸 Box {box_id}\n{PROMPTS[box_id]}\n\nSend your photo or video!\n⚠️ Video must be under 20MB, (~5-10s)."
        
    )

# =========================
# HANDLE PHOTO
# =========================
import time  # 👈 make sure this is at the top of your file

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute("SELECT COUNT(*) FROM winner")
    winner_count = cursor.fetchone()[0]
    
    if winner_count >= 15:
        await update.message.reply_text(
            "🏁 Game over! All 15 prizes have been claimed.\n"
            "Thanks for participating! 🎉"
        )
        return

    # 🚫 RATE LIMIT (add this block)
    if "last_submit" in context.user_data:
        if time.time() - context.user_data["last_submit"] < 3:
            await update.message.reply_text("⏳ Please wait a few seconds before sending again!")
            return

    context.user_data["last_submit"] = time.time()
    
    box_id = context.user_data.get("box")
    if not box_id:
        await update.message.reply_text("Please select a box first using /start")
        return
    # ✅ END RATE LIMIT

    box_id = context.user_data.get("box")
    
    cursor.execute(
       "SELECT status FROM submissions WHERE user_id=? AND box_id=?",
       (user.id, box_id)
    )

    row = cursor.fetchone()
    if row:
        if row[0] == "pending":
            await update.message.reply_text(
                "⏳ You already submitted this box. Please wait for approval!"
            )
            return
        else:
            await update.message.reply_text("✅ Already completed!")
            return

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        if update.message.video.file_size and update.message.video.file_size > 20_000_000:
            await update.message.reply_text( 
                "🚫 Video too large! (Max 20MB)\n\n"
                "💡 Tip:\n"
                "• Keep videos under ~5–10 seconds\n"
                "• Use Telegram camera instead of gallery\n"
                "• Lower video quality in camera settings"
            )
            return
        file_id = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("Please send a photo or video.")
        return

    cursor.execute(
        "INSERT OR IGNORE INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, box_id, "pending")
    )
    conn.commit()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}_{box_id}")
        ]
    ])

    try:
        caption = f"{user.username} submitted Box {box_id}\n{PROMPTS[box_id]}"
        if media_type == "photo":
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, reply_markup=keyboard)
        elif media_type == "video":
            await context.bot.send_video(chat_id=ADMIN_ID, video=file_id, caption=caption, reply_markup=keyboard)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send to admin: {e}")
        return

    await update.message.reply_text("⏳ Submitted! Waiting for approval...")
    context.user_data.pop("box", None)

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

    board_text = ""
    for i in range(1, 26):
        board_text += "✅ " if i in completed else "⬜ "
        if i % 5 == 0:
            board_text += "\n"

    keyboard = []
    row = []
    for i in range(1, 26):
        if i == 13:
            row.append(InlineKeyboardButton("FREE", callback_data="blocked"))
        elif i in completed:
            row.append(InlineKeyboardButton("✔️", callback_data="blocked"))
        else:
            row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))

        if len(row) == 5:
            keyboard.append(row)
            row = []

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        with open("bingo.jpg", "rb") as img:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=img,
                caption="📊 Updated Board!\nPick another box:",
                reply_markup=reply_markup
            )
    except FileNotFoundError:
        await context.bot.send_message(chat_id=user_id, text="📊 Updated Board!\nPick another box:", reply_markup=reply_markup)

    await context.bot.send_message(chat_id=user_id, text=board_text)

# =========================
# APPROVAL
# =========================
async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT COUNT(*) FROM winner")
    winner_count = cursor.fetchone()[0]
    
    if winner_count >= 15:
        await query.answer("Game already ended 🏁", show_alert=True)
        return

    data = query.data.split("_")
    action, user_id, box_id = data[0], int(data[1]), int(data[2])

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

        # BINGO CHECK
        cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
        completed = [row[0] for row in cursor.fetchall()]
        if 13 not in completed:
            completed.append(13)

        if has_bingo(completed):
            cursor.execute("SELECT 1 FROM winner WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM winner")
                count = cursor.fetchone()[0]
                
                if count < 15:
                    rank = count + 1
                    cursor.execute("SELECT username FROM submissions WHERE user_id=? LIMIT 1", (user_id,))
                    result = cursor.fetchone()
                    username = result[0] if result else None
                    display_name = f"@{username}" if username else f"User {user_id}"

                    cursor.execute("INSERT INTO winner VALUES (?, ?, ?)", (user_id, username, rank))
                    conn.commit()

                    prize = "$10 NTUC e-voucher 💰" if rank <= 5 else "$5 NTUC e-voucher 🎁"

                    remaining = 15 - rank 
                    winner_name = f"@{username}" if username else f"User {user_id}"

                    await broadcast(
                        context, 
                         f"🏆 BINGO WINNER!\n\n"
                        f"{winner_name} just got Bingo! 🎉\n"
                        f"🏅 Winner #{rank}\n\n"
                        f"🎁 Only {remaining} prizes left — hurry! Keep going!"
                    )
   

                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🏆 BINGO!\nYou are winner #{rank}!\n\n🎁 Prize: {prize}\n📍 Please text FMD WCS S1 @AmosBok for your e-voucher!"
                    )
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"🏆 NEW WINNER\nUser: {display_name}\nUser ID: {user_id}\nRank: #{rank}\nPrize: {prize}"
                    )
                else:
                    await context.bot.send_message(chat_id=user_id, text="🎉 BINGO! But all prizes have been claimed.")

        await query.message.reply_text("✅ Approved")

    elif action == "reject":
        cursor.execute("DELETE FROM submissions WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        await context.bot.send_message(chat_id=user_id, text=f"❌ Rejected.\nBox {box_id}: {PROMPTS[box_id]}\nTry again!")
        await query.message.reply_text("❌ Rejected")
        
async def blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Already completed ✅", show_alert=True)
    
def has_bingo(boxes):
    wins = [
        [1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20], [21,22,23,24,25], # Rows
        [1,6,11,16,21], [2,7,12,17,22], [3,8,13,18,23], [4,9,14,19,24], [5,10,15,20,25], # Cols
        [1,7,13,19,25], [5,9,13,17,21] # Diagonals
    ]
    return any(all(x in boxes for x in combo) for combo in wins)

async def board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_board(context, update.message.from_user.id)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT username, rank FROM winner ORDER BY rank ASC")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("No winners yet!")
        return

    text = "🏆 Leaderboard\n\n"
    for username, rank in rows:
        prize = "$10 NTUC e-voucher 💰" if rank <= 5 else "$5 NTUC e-voucher 🎁"
        name = f"@{username}" if username else "User"
        text += f"{rank}. {name} - {prize}\n"

    await update.message.reply_text(text)
    
# =========================
# APP SETUP
# =========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("myid", myid))
app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("board", board))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CallbackQueryHandler(select_box, pattern="^box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve|reject)_"))
app.add_handler(CallbackQueryHandler(blocked, pattern="^blocked$"))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

print("🤖 Bot is running...")
app.run_polling()
