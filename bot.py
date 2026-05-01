import sqlite3
import logging
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
    wins = [
        [1,2,3,4,5], [6,7,8,9,10], [11,12,13,14,15], [16,17,18,19,20], [21,22,23,24,25], 
        [1,6,11,16,21], [2,7,12,17,22], [3,8,13,18,23], [4,9,14,19,24], [5,10,15,20,25], 
        [1,7,13,19,25], [5,9,13,17,21]
    ]
    return any(all(box in boxes for box in combo) for box in wins)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grid, kb = await get_user_board(update.effective_user.id)

    caption_text = "🎉 Photo Bingo!\nSelect a box below to submit your photo 📸"

    if os.path.exists("bingo.jpg"):
        await update.message.reply_photo(
            photo=open("bingo.jpg", "rb"),
            caption=caption_text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🎮 *BINGO!*\nPick a box:\n\n{grid}",
            reply_markup=kb,
            parse_mode="Markdown"
        )

async def box_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    box_id = int(query.data.split("_")[1])
    context.user_data["active_box"] = box_id
    await query.message.reply_text(f"📸 **Box {box_id}**: {PROMPTS[box_id]}\nSend your photo!")

async def photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    box_id = context.user_data.get("active_box")

    if not box_id:
        await update.message.reply_text("❌ Pick a box first!")
        return

    try:
        cursor.execute("INSERT INTO submissions (user_id, username, box_id, status) VALUES (?, ?, ?, 'pending')", (user.id, user.username, box_id))
        conn.commit()

        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"adm_ok_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_no_{user.id}_{box_id}")
        ]])

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(admin_id, update.message.photo[-1].file_id, caption=f"📥 New: @{user.username}\nBox: {box_id}", reply_markup=admin_kb)
            except Exception:
                pass

        await update.message.reply_text(f"📨 Box {box_id} sent! Waiting for approval.")
        context.user_data.pop("active_box", None)
    except sqlite3.IntegrityError:
        await update.message.reply_text("⚠️ Already submitted!")

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, action, user_id, box_id = query.data.split("_")
    user_id, box_id = int(user_id), int(box_id)

    if action == "ok":
        cursor.execute("UPDATE submissions SET status='approved' WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        await query.edit_message_caption("✅ Approved")
        
        # Send updated board to user
        grid, kb = await get_user_board(user_id)
        await context.bot.send_message(user_id, f"✅ Box {box_id} Approved!\n\n{grid}", reply_markup=kb, parse_mode="Markdown")

        # Bingo check
        cursor.execute("SELECT box_id FROM submissions WHERE user_id=? AND status='approved'", (user_id,))
        done = [r[0] for r in cursor.fetchall()]
        if 13 not in done: done.append(13)
        if check_for_bingo(done):
            await context.bot.send_message(user_id, "🏆 BINGO! Contact admin.")
    else:
        cursor.execute("DELETE FROM submissions WHERE user_id=? AND box_id=?", (user_id, box_id))
        conn.commit()
        await query.edit_message_caption("❌ Rejected")
        await context.bot.send_message(user_id, f"❌ Box {box_id} rejected.")

# --- APP ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_upload))
    app.add_handler(CallbackQueryHandler(box_click, pattern="^box_"))
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^adm_"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^blocked$"))
    print("🚀 Bot Started")
    app.run_polling()
