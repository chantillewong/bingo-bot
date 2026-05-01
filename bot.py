import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8727437729:AAHx_bGLbpc0QyJWY-oBZE2qjbu6Xag2IAk"
ADMIN_IDS = [1087116288]

# --- DATABASE SETUP ---
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

# --- HELPER FUNCTIONS ---

def has_bingo(boxes):
    wins = [
        [1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20], [21,22,23,24,25], # Rows
        [1,6,11,16,21], [2,7,12,17,22], [3,8,13,18,23], [4,9,14,19,24], [5,10,15,20,25], # Cols
        [1,7,13,19,25], [5,9,13,17,21] # Diagonals
    ]
    for combo in wins:
        if all(x in boxes for x in combo):
            return True
    return False

async def get_updated_board_markup(user_id):
    cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
    completed = [row[0] for row in cursor.fetchall()]
    if 13 not in completed: completed.append(13)

    keyboard = []
    row = []
    board_visual = ""

    for i in range(1, 26):
        if i == 13:
            board_visual += "🟩 "
            row.append(InlineKeyboardButton("FREE", callback_data="blocked"))
        elif i in completed:
            board_visual += "✅ "
            row.append(InlineKeyboardButton("✔️", callback_data="blocked"))
        else:
            board_visual += "⬜ "
            row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
            board_visual += "\n"
            
    return board_visual, InlineKeyboardMarkup(keyboard)

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board_text, markup = await get_updated_board_markup(update.effective_user.id)
    try:
        await update.message.reply_photo(
            photo=open("bingo.jpg", "rb"),
            caption="🎉 **Photo Bingo!**\nSelect a box number to submit your photo.\n\n" + board_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except FileNotFoundError:
        await update.message.reply_text("🎉 **Photo Bingo!**\nSelect a box to submit.\n\n" + board_text, reply_markup=markup)

async def select_box(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    box_id = int(query.data.split("_")[1])
    
    if box_id == 13:
        await query.answer("🟩 This is your free space!", show_alert=True)
        return

    context.user_data["box"] = box_id
    await query.message.reply_text(f"📸 **Box {box_id}**: {PROMPTS[box_id]}\n\nPlease send your photo now!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    box_id = context.user_data.get("box")

    if not box_id:
        await update.message.reply_text("❌ Please select a box number from /start before sending a photo.")
        return

    # Check if already done
    cursor.execute("SELECT status FROM submissions WHERE user_id=? AND box_id=?", (user.id, box_id))
    existing = cursor.fetchone()
    if existing:
        msg = "⏳ Still pending approval." if existing[0] == "pending" else "✅ Already completed!"
        await update.message.reply_text(msg)
        return

    # Store submission
    cursor.execute("INSERT INTO submissions VALUES (?, ?, ?, ?)", (user.id, user.username, box_id, "pending"))
    conn.commit()

    photo_id = update.message.photo[-1].file_id
    
    # Admin Buttons
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejectmenu_{user.id}_{box_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo_id,
            caption=f"📥 **New Submission**\nUser: @{user.username} ({user.id})\nBox {box_id}: {PROMPTS[box_id]}",
            reply_markup=admin_kb,
            parse_mode="Markdown"
        )

    await update.message.reply_text(f"📨 Box {box_id} submitted! Waiting for admin approval.")
    context.user_data.pop("box", None)

# --- ADMIN ACTIONS ---

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS: return
    
    _, user_id, box_id = query.data.split("_")
    user_id, box_id = int(user_id), int(box_id)

    cursor.execute("UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?", (user_id, box_id))
    conn.commit()

    # Update Admin Message
    await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **APPROVED**", reply_markup=None, parse_mode="Markdown")

    # Notify User
    await context.bot.send_message(chat_id=user_id, text=f"✅ Your submission for **Box {box_id}** was approved!", parse_mode="Markdown")
    
    # Send updated board to user
    board_text, markup = await get_updated_board_markup(user_id)
    await context.bot.send_message(chat_id=user_id, text=f"📊 **Updated Board:**\n\n{board_text}", reply_markup=markup, parse_mode="Markdown")

    # Check Bingo
    cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
    completed = [row[0] for row in cursor.fetchall()]
    if 13 not in completed: completed.append(13)

    if has_bingo(completed):
        cursor.execute("SELECT 1 FROM winner WHERE user_id=?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM winner")
            rank = cursor.fetchone()[0] + 1
            if rank <= 15:
                cursor.execute("SELECT username FROM submissions WHERE user_id=? LIMIT 1", (user_id,))
                uname = cursor.fetchone()[0]
                cursor.execute("INSERT INTO winner VALUES (?, ?, ?)", (user_id, uname, rank))
                conn.commit()
                
                prize = "$10 voucher 💰" if rank <= 5 else "$5 voucher 🎁"
                win_msg = f"🏆 **BINGO!**\nYou are winner #{rank}!\nPrize: {prize}\n📍 Collect at entrance."
                await context.bot.send_message(chat_id=user_id, text=win_msg, parse_mode="Markdown")
                
                for aid in ADMIN_IDS:
                    await context.bot.send_message(chat_id=aid, text=f"🏆 **NEW WINNER!**\nUser: @{uname}\nRank: #{rank}")

async def reject_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, user_id, box_id = query.data.split("_")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Wrong prompt", callback_data=f"rej_wrong_{user_id}_{box_id}")],
        [InlineKeyboardButton("📷 Blurry", callback_data=f"rej_blurry_{user_id}_{box_id}")],
        [InlineKeyboardButton("❗ Other", callback_data=f"rej_other_{user_id}_{box_id}")]
    ])
    await query.message.reply_text("Select rejection reason:", reply_markup=keyboard)

async def handle_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, reason_key, user_id, box_id = query.data.split("_")
    user_id, box_id = int(user_id), int(box_id)

    reasons = {"wrong": "Wrong prompt", "blurry": "Photo is blurry", "other": "Not accepted"}
    reason = reasons.get(reason_key, "Submission rejected")

    cursor.execute("DELETE FROM submissions WHERE user_id=? AND box_id=?", (user_id, box_id))
    conn.commit()

    # Update Admin & Notify User
    await query.edit_message_text(f"❌ Rejected: {reason}")
    await context.bot.send_message(chat_id=user_id, text=f"❌ Your submission for **Box {box_id}** was rejected.\nReason: {reason}\nPlease try again!", parse_mode="Markdown")

# --- APP START ---

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(select_box, pattern="^box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="^approve_"))
app.add_handler(CallbackQueryHandler(reject_menu, pattern="^rejectmenu_"))
app.add_handler(CallbackQueryHandler(handle_rejection, pattern="^rej_"))
app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^blocked$"))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("🚀 BOT STARTED")
app.run_polling()    # 🚫 Prevent selecting if pending exists
    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='pending'",
        (query.from_user.id,)
    )
    if cursor.fetchone():
        await query.message.reply_text("⏳ You already have a pending submission.")
        return

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

    # 🔍 Check if already pending
    cursor.execute(
        "SELECT box_id FROM submissions WHERE user_id=? AND status='pending'",
        (user.id,)
    )
    pending = cursor.fetchone()

    if pending:
        await update.message.reply_text("⏳ Waiting for approval.")
        return

    if not box_id:
        await update.message.reply_text("Please select a box first using /start")
        return

    # 🔍 Check if already completed
    cursor.execute(
        "SELECT status FROM submissions WHERE user_id=? AND box_id=?",
        (user.id, box_id)
    )
    result = cursor.fetchone()

    if result:
        if result[0] == "approved":
            await update.message.reply_text("✅ Already completed!")
            return

    # 💾 Save submission
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

    for admin_id in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo,
            caption=f"{user.username} → Box {box_id}",
            reply_markup=keyboard
        )

    await update.message.reply_text("📨 Submitted! Waiting for approval.")
    context.user_data.pop("box", None)

# =========================
# APPROVAL
# =========================
async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.answer("Not authorised ❌", show_alert=True)
        return

    action, user_id, box_id = query.data.split("_")
    user_id, box_id = int(user_id), int(box_id)

    if action == "approve":
        cursor.execute(
            "UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?",
            (user_id, box_id)
        )
        conn.commit()

        await query.edit_message_caption("✅ Approved")
        await query.edit_message_reply_markup(None)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Approved!\nBox {box_id}"
        )

        await send_board(context, user_id)

# =========================
# REJECT
# =========================
async def handle_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, user_id, box_id = query.data.split("_")
    user_id, box_id = int(user_id), int(box_id)

    cursor.execute(
        "DELETE FROM submissions WHERE user_id=? AND box_id=? AND status='pending'",
        (user_id, box_id)
    )
    conn.commit()

    await context.bot.send_message(
        chat_id=user_id,
        text=f"❌ Rejected. Please try again for Box {box_id}"
    )

    await query.edit_message_caption("❌ Rejected")
    await query.edit_message_reply_markup(None)

# =========================
# BOARD
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

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📊 Your Board:\n\n{text}"
    )

# =========================
# BLOCKED BUTTON
# =========================
async def blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Already done", show_alert=True)

# =========================
# MAIN
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(select_box, pattern="^box_"))
app.add_handler(CallbackQueryHandler(handle_approval, pattern="^approve_"))
app.add_handler(CallbackQueryHandler(handle_reject, pattern="^reject_"))
app.add_handler(CallbackQueryHandler(blocked, pattern="^blocked$"))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.run_polling()        await query.answer("🟩 Free space! No photo needed", show_alert=True)
        return

    context.user_data["box"] = box_id

    await query.message.reply_text(
        f"📸 Box {box_id}\n{PROMPTS[box_id]}\n\nSend your photo!"
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    print(f"🧪 Test command from user_id={user.id}")

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text="✅ Test message works!"
        )
        print("✅ Test message sent")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    box_id = context.user_data.get("box")

    if not box_id:
        await update.message.reply_text("Please select a box first using /start")
        return

    cursor.execute(
        "SELECT status FROM submissions WHERE user_id=? AND box_id=?",
        (user.id, box_id)
    )
    result = cursor.fetchone()
    if result:
        if result[0] == "pending":
            await update.message.reply_text("⏳ Waiting for approval.")
        else:
            await update.message.reply_text("✅ Already completed!")
        return

    cursor.execute(
        "INSERT INTO submissions VALUES (?, ?, ?, ?)",
        (user.id, user.username, box_id, "pending")
    )
    print(f"📸 STORED → user_id={user.id}, username={user.username}, box={box_id}")
    conn.commit()

    photo = update.message.photo[-1].file_id

    # ✅ THIS PART MUST BE INSIDE FUNCTION
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejectmenu_{user.id}_{box_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo,
            caption=f"{user.username} submitted Box {box_id}\n{PROMPTS[box_id]}",
            reply_markup=keyboard
        )

    await update.message.reply_text("📨 Submitted! Once approved, you'll receive a message and your board will update.")
    context.user_data.pop("box", None)
    
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
    print("🔥 handle_approval triggered")
    query = update.callback_query
    await query.answer()

    # 🔐 Admin check
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("Not authorised ❌", show_alert=True)
        return

    action, user_id, box_id = query.data.split("_")
    user_id = int(user_id)
    box_id = int(box_id)

    # 🔍 Check current status
    cursor.execute(
        "SELECT status FROM submissions WHERE user_id=? AND box_id=?",
        (user_id, box_id)
    )
    result = cursor.fetchone()

    if not result:
        await query.answer("Submission not found ❌", show_alert=True)
        return

    if result[0] != "pending":
        await query.answer("Already processed ✅", show_alert=True)
        return

    # ======================
    # ✅ APPROVE FLOW
    # ======================
    if action == "approve":
        print("✅ APPROVE BLOCK ENTERED")
        cursor.execute(
            "UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?",
            (user_id, box_id)
        )
        conn.commit()
        
        print(f"📤 TRYING TO SEND → user_id={user_id}, box={box_id}")

        admin_name = query.from_user.username or query.from_user.first_name

        # 🟢 Update admin message
        await query.edit_message_caption(
            caption=f"✅ Approved by @{admin_name}"
        )
        await query.edit_message_reply_markup(reply_markup=None)
        print(f"📤 Sending to user_id={user_id}")
        # ======================
        # 👤 SEND TO USER
        # ======================
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Approved!\nBox {box_id}: {PROMPTS[box_id]}"
            )
            print(f"✅ Sent approval to {user_id}")
        except Exception as e:
            print(f"❌ Failed to send approval to {user_id}: {e}")

        # ======================
        # 📊 UPDATE BOARD
        # ======================
        try:
            await send_board(context, user_id)
        except Exception as e:
            print(f"❌ Failed to send board: {e}")

        # ======================
        # 🏆 CHECK BINGO
        # ======================
        cursor.execute(
            "SELECT box_id FROM submissions WHERE user_id=? AND status='approved'",
            (user_id,)
        )
        completed = [row[0] for row in cursor.fetchall()]

        if 13 not in completed:
            completed.append(13)

        if has_bingo(completed):

            # 🚫 prevent duplicate winners
            cursor.execute(
                "SELECT 1 FROM winner WHERE user_id=?",
                (user_id,)
            )
            if cursor.fetchone():
                return

            cursor.execute("SELECT COUNT(*) FROM winner")
            count = cursor.fetchone()[0]

            if count < 15:
                rank = count + 1

                cursor.execute(
                    "SELECT username FROM submissions WHERE user_id=? LIMIT 1",
                    (user_id,)
                )
                result = cursor.fetchone()
                username = result[0] if result else None
                display_name = f"@{username}" if username else f"User {user_id}"

                cursor.execute(
                    "INSERT INTO winner VALUES (?, ?, ?)",
                    (user_id, username, rank)
                )
                conn.commit()

                prize = "$10 voucher 💰" if rank <= 5 else "$5 voucher 🎁"

                # 👤 notify user
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🏆 BINGO!\n"
                            f"You are winner #{rank}!\n"
                            f"You won a {prize}\n\n"
                            f"📍 Please collect your voucher at the entrance!"
                        )
                    )
                except Exception as e:
                    print(f"❌ Failed to notify winner: {e}")

                # 📢 notify admins
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"🏆 NEW WINNER\n"
                                f"User: {display_name}\n"
                                f"User ID: {user_id}\n"
                                f"Rank: #{rank}\n"
                                f"Prize: {prize}"
                            )
                        )
                    except Exception as e:
                        print(f"❌ Failed to notify admin {admin_id}: {e}")

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

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Not authorised ❌")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Pending Approvals", callback_data="admin_pending")],
        [InlineKeyboardButton("🔄 Reset Game", callback_data="admin_reset")],
        [InlineKeyboardButton("🏆 View Leaderboard", callback_data="admin_leaderboard")],
        [InlineKeyboardButton("💣 RESET EVERYTHING", callback_data="admin_reset_all")]

])

    await update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=keyboard
    )
    
async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.answer("Not authorised ❌", show_alert=True)
        return

    action = query.data

    # 🔄 Reset leaderboard only
    if action == "admin_reset":
        cursor.execute("DELETE FROM winner")
        conn.commit()

        await query.message.reply_text("♻️ Leaderboard has been reset!")

    # 📋 View pending submissions
    elif action == "admin_pending":
        cursor.execute(
            "SELECT user_id, username, box_id FROM submissions WHERE status='pending'"
        )
        rows = cursor.fetchall()

        if not rows:
            await query.message.reply_text("✅ No pending submissions!")
            return

        text = "📋 Pending Approvals:\n\n"
        for user_id, username, box_id in rows:
            name = f"@{username}" if username else f"User {user_id}"
            text += f"{name} → Box {box_id}\n"

        await query.message.reply_text(text)

    # 🏆 View leaderboard
    elif action == "admin_leaderboard":
        cursor.execute(
            "SELECT username, rank FROM winner ORDER BY rank ASC"
        )
        rows = cursor.fetchall()

        if not rows:
            await query.message.reply_text("No winners yet!")
            return

        text = "🏆 Leaderboard\n\n"

        for username, rank in rows:
            if rank <= 5:
                prize = "$10 voucher 💰"
            else:
                prize = "$5 voucher 🎁"

            name = f"@{username}" if username else "User"
            text += f"{rank}. {name} - {prize}\n"

        await query.message.reply_text(text)

    # 💣 Ask confirmation for FULL reset
    elif action == "admin_reset_all":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚠️ YES, RESET", callback_data="confirm_reset_all"),
                InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")
            ]
        ])

        await query.message.reply_text(
            "⚠️ Are you sure you want to RESET EVERYTHING?\nThis cannot be undone.",
            reply_markup=keyboard
        )

    # 💣 CONFIRM full reset
    elif action == "confirm_reset_all":
        cursor.execute("DELETE FROM submissions")
        cursor.execute("DELETE FROM winner")
        conn.commit()

        await query.message.reply_text("💣 Game fully reset! Everyone starts fresh.")

    # ❌ Cancel reset
    elif action == "admin_cancel":
        await query.message.reply_text("Cancelled 👍")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("board", board))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("test", test))  # 👈 ADD HERE

app.add_handler(CallbackQueryHandler(handle_approval, pattern="^approve_"))
app.add_handler(CallbackQueryHandler(reject_menu, pattern="^rejectmenu_"))
app.add_handler(CallbackQueryHandler(handle_reject_reason, pattern="^reject_"))
app.add_handler(CallbackQueryHandler(handle_admin_actions, pattern="^(admin_|confirm_)"))
app.add_handler(CallbackQueryHandler(select_box, pattern="^box_"))
app.add_handler(CallbackQueryHandler(blocked, pattern="^blocked$"))

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.run_polling()
