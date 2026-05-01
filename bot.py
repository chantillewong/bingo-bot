async def photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    box_id = context.user_data.get("active_box")

    if not box_id:
        await update.message.reply_text("❌ Select a box first using /start")
        return

    try:
        # 1. Save to Database first
        cursor.execute("INSERT INTO submissions (user_id, username, box_id, status) VALUES (?, ?, ?, 'pending')", 
                       (user.id, user.username, box_id))
        conn.commit()

        # 2. Create Admin Buttons
        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"adm_ok_{user.id}_{box_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_no_{user.id}_{box_id}")
        ]])

        # 3. Send to Admins
        photo_file_id = update.message.photo[-1].file_id
        sent_to_at_least_one_admin = False

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=f"📥 **New Submission**\nUser: @{user.username} ({user.id})\nBox: {box_id}\nTask: {PROMPTS[box_id]}",
                    reply_markup=admin_kb,
                    parse_mode="Markdown"
                )
                sent_to_at_least_one_admin = True
            except Exception as admin_err:
                logging.error(f"Could not send to admin {admin_id}: {admin_err}")

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
