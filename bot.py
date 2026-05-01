import sqlite3
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8727437729:AAHx_bGLbpc0QyJWY-oBZE2qjbu6Xag2IAk"
ADMIN_IDS = [1087116288]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE SETUP ---
conn = sqlite3.connect("bingo.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS submissions (user_id INTEGER, username TEXT, box_id INTEGER, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS winner (user_id INTEGER, username TEXT, rank INTEGER)")
conn.commit()

# --- TASK DATA ---
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

# --- HELPER FUNCTIONS ---

async def get_user_board(user_id):
    cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
    completed = [row[0] for row in cursor.fetchall()]
    if 13 not in completed:
        completed.append(13)

    keyboard = []
    row = []
    visual_grid = ""
    for i in range(1, 26):
        if i == 13:
            visual_grid += "🟩 "
            row.append(InlineKeyboardButton("FREE", callback_data="blocked"))
        elif i in completed:
            visual_grid += "✅ "
            row.append(InlineKeyboardButton("✔️", callback_data="blocked"))
        else:
            visual_grid += "⬜ "
            row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
            visual_grid += "\n"
            
    return visual_grid, InlineKeyboardMarkup(keyboard)

def check_for_bingo(boxes):
    winning_combos = [
        [1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20], [21,22,23,24,25], 
        [1,6,11,16,21], [2,7,12,17,22], [3,8,13,18,23], [4,9,14,19,24], [5,10,15,20,25], 
        [1,7,13,19,25], [5,9,13,17,21]
    ]
    return any(all(box in boxes for box in combo) for box in winning_combos)

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grid, kb = await get_user_board(update.effective_user.id)
    await update.message.reply_text(
        f"🎮 **BINGO CHALLENGE**\nSelect a box number to see your task:\n\n{grid}",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def box_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    box_id = int(query.data.split("_")[1])
    context.user_data["active_box"] = box_id
    await query.message.reply_text(f"📸 **Box {box_id}**: {PROMPTS[box_id]}\n\nPlease send your photo now!")

async def photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    box_id = context.user_data.get("active_box")

    if not box_id:
        await update.message.reply_text("❌ Please select a box first from the board!")
        return

    try:
        cursor.execute("INSERT INTO submissions (user_id, username, box_id, status) VALUES (?, ?, ?, 'pending')", 
                       (user.id, user.username, box_id))
        conn.commit()

        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"adm_ok_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_no_{user.id}_{box_id}")
        ]])

        photo_file_id = update.message.photo[-1].file_id
        sent_success = False

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=f"📥 **New Submission**\nUser: @{user.username}\nBox: {box_id}",
                    reply_markup=admin_kb
                )
                sent_success = True
            except Exception as e:
                logging.error(f"Admin {admin_id} notification failed: {e}")

        if sent_success:
            await update.message.reply_text(f"📨 Box {box_id} submitted! Waiting for approval.")
        else:
            await update.message.reply_text("⚠️ Submission saved, but admins couldn't be reached. Ensure admins have /start-ed the bot.")
        
        context.user_data.pop("active_box", None)

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ You already have a pending submission for this box.")
    except Exception as e:
        logging.error(f"Upload error: {e}")
        await update.message.reply_text("❌ Error processing photo.")

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    action, user_id, box_id = data[1], int(data[2]), int(data[3])

    if action == "ok":
        cursor.execute("UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        await query.edit_message_caption("✅ Approved")
        
        # Notify User
        grid, kb = await get_user_board(user_id)
        await context.bot.send_message(user_id, f"✅ Box {box_id} Approved!\n\n{grid}", reply_markup=kb, parse_mode="Markdown")

        # Bingo logic
        cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
        done = [r[0] for r in cursor.fetchall()]
        if 13 not in done: done.append(13)
        if check_for_bingo(done):
            await context.bot.send_message(user_id, "🏆 BINGO! Contact admin for your prize.")
    else:
        cursor.execute("DELETE FROM submissions WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        await query.edit_message_caption("❌ Rejected")
        await context.bot.send_message(user_id, f"❌ Box {box_id} rejected. Try again!")

# --- BOOT ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_upload))
    app.add_handler(CallbackQueryHandler(box_click, pattern="^box_"))
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^adm_"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^blocked$"))
    print("🚀 Running...")
    app.run_polling()    15: "Wefie with an African Painted Dog.",
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

# --- HELPERS ---

async def get_user_board(user_id):
    cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
    completed = [row[0] for row in cursor.fetchall()]
    if 13 not in completed:
        completed.append(13)

    keyboard = []
    row = []
    visual_grid = ""
    for i in range(1, 26):
        if i == 13:
            visual_grid += "🟩 "
            row.append(InlineKeyboardButton("FREE", callback_data="blocked"))
        elif i in completed:
            visual_grid += "✅ "
            row.append(InlineKeyboardButton("✔️", callback_data="blocked"))
        else:
            visual_grid += "⬜ "
            row.append(InlineKeyboardButton(str(i), callback_data=f"box_{i}"))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
            visual_grid += "\n"
            
    return visual_grid, InlineKeyboardMarkup(keyboard)

def check_for_bingo(boxes):
    winning_combos = [
        [1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20], [21,22,23,24,25], 
        [1,6,11,16,21], [2,7,12,17,22], [3,8,13,18,23], [4,9,14,19,24], [5,10,15,20,25], 
        [1,7,13,19,25], [5,9,13,17,21]
    ]
    return any(all(box in boxes for box in combo) for combo in winning_combos)

# --- CORE HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grid, kb = await get_user_board(update.effective_user.id)
    await update.message.reply_text(
        f"🎮 **BINGO CHALLENGE**\nSelect a box number to see your task:\n\n{grid}",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def box_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    box_id = int(query.data.split("_")[1])
    context.user_data["active_box"] = box_id
    await query.message.reply_text(f"📸 **Box {box_id}**: {PROMPTS[box_id]}\n\nPlease send your photo now!")

async def photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    box_id = context.user_data.get("active_box")

    if not box_id:
        await update.message.reply_text("❌ Please select a box number first from the board!")
        return

    try:
        # Check if already pending or approved
        cursor.execute("SELECT status FROM submissions WHERE user_id=? AND box_id=?", (user.id, box_id))
        existing = cursor.fetchone()
        if existing:
            await update.message.reply_text(f"⚠️ You already have a {existing[0]} submission for this box.")
            return

        cursor.execute("INSERT INTO submissions (user_id, username, box_id, status) VALUES (?, ?, ?, 'pending')", 
                       (user.id, user.username, box_id))
        conn.commit()

        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"adm_ok_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_no_{user.id}_{box_id}")
        ]])

        photo_file_id = update.message.photo[-1].file_id
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=f"📥 **New Submission**\nUser: @{user.username}\nBox: {box_id}\nTask: {PROMPTS[box_id]}",
                    reply_markup=admin_kb,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id}: {e}")

        await update.message.reply_text(f"📨 Box {box_id} submitted! Waiting for admin approval.")
        context.user_data.pop("active_box", None)

    except Exception as e:
        logging.error(f"Upload Error: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Format: adm_action_userid_boxid
    data = query.data.split("_")
    action = data[1] 
    user_id = int(data[2])
    box_id = int(data[3])

    if action == "ok":
        cursor.execute("UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        
        await query.edit_message_caption(caption=f"✅ **Approved Box {box_id} for @{user_id}**", parse_mode="Markdown")
        
        # Notify User and Send Updated Board
        grid, kb = await get_user_board(user_id)
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"🎉 **Box {box_id} Approved!**\nHere is your updated board:\n\n{grid}", 
            reply_markup=kb, 
            parse_mode="Markdown"
        )

        # Check Bingo
        cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
        done = [r[0] for r in cursor.fetchall()]
        if 13 not in done: done.append(13)

        if check_for_bingo(done):
            cursor.execute("SELECT 1 FROM winner WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM winner")
                rank = cursor.fetchone()[0] + 1
                cursor.execute("INSERT INTO winner VALUES (?, ?, ?)", (user_id, "User", rank))
                conn.commit()
                await context.bot.send_message(user_id, f"🏆 **BINGO!** You are winner #{rank}! See admin for prize.")
    else:
        cursor.execute("DELETE FROM submissions WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        await query.edit_message_caption(caption=f"❌ **Rejected Box {box_id}**", parse_mode="Markdown")
        await context.bot.send_message(user_id, f"❌ Your submission for **Box {box_id}** was rejected. Please try again!", parse_mode="Markdown")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, photo_upload))
    application.add_handler(CallbackQueryHandler(box_click, pattern="^box_"))
    application.add_handler(CallbackQueryHandler(admin_decision, pattern="^adm_"))
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^blocked$"))

    print("🚀 Bingo Bot is now running...")
    application.run_polling()
        # 4. Feedback to User
        if sent_to_at_least_one_admin:
            await update.message.reply_text(f"📨 Box {box_id} submitted! Waiting for admin approval.")
        else:
            await update.message.reply_text("⚠️ Submission saved, but admins couldn't be notified. Please tell an admin to /start the bot.")
        
        context.user_data.pop("active_box", None)

    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ You already have a pending submission for this box.")
    except Exception as e:
        logging.error(f"General Error in photo_upload: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
