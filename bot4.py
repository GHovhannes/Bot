import os
import time
import traceback
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)
from telegram.error import Conflict

BOT_TOKEN = "7576613965:AAFx5d6fvfqXPofEyD-r1g1HN43AgyxHt4s"

# VIDEO_LIBRARY maps a command (string) to a list of video file paths.
VIDEO_LIBRARY = {
    "Ugway_quotes": ["ugway1.mp4", "ugway2.mp4", "ugway3.mp4"],
    # You can add more keys as needed.
}

# Global dictionaries to track each user's mode and admin temporary data.
user_modes = {}   # Maps user_id -> "user", "pending_admin", or "admin"
admin_temp = {}   # Stores temporary data for admin actions (like the downloaded video file path)

# Conversation states for admin flow
SELECT_MODE, ADMIN_PASSWORD, ADMIN_MENU, ADMIN_ADD_WAIT_VIDEO, ADMIN_ADD_WAIT_NAME, ADMIN_REMOVE = range(6)


# -------------------- Conversation Entry --------------------
async def start(update: Update, context):
    user_id = update.message.from_user.id
    user_modes.pop(user_id, None)  # Clear any previous mode
    # Show mode selection buttons
    keyboard = [
        [
            InlineKeyboardButton("User", callback_data="mode_user"),
            InlineKeyboardButton("Admin", callback_data="mode_admin"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select mode:", reply_markup=reply_markup)
    return SELECT_MODE


# -------------------- Mode Selection --------------------
async def select_mode(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "mode_user":
        user_modes[user_id] = "user"
        # Build an inline keyboard listing available video commands:
        if VIDEO_LIBRARY:
            buttons = []
            for command in VIDEO_LIBRARY.keys():
                # Prefix callback data with "user_select_" to distinguish it
                buttons.append([InlineKeyboardButton(command, callback_data=f"user_select_{command}")])
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text("User mode selected.\nPlease choose a video category:", reply_markup=reply_markup)
        else:
            await query.edit_message_text("User mode selected, but no videos are available.")
        return ConversationHandler.END
    elif query.data == "mode_admin":
        user_modes[user_id] = "pending_admin"
        await query.edit_message_text("Please enter the admin password:")
        return ADMIN_PASSWORD


# -------------------- Admin Password --------------------
async def admin_password(update: Update, context):
    user_id = update.message.from_user.id
    password = update.message.text.strip()
    if password == "hostertoster":
        user_modes[user_id] = "admin"
        # Show admin menu buttons
        keyboard = [
            [
                InlineKeyboardButton("Add", callback_data="admin_add"),
                InlineKeyboardButton("Remove", callback_data="admin_remove"),
            ],
            [InlineKeyboardButton("End_session", callback_data="admin_end")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Admin mode activated. Choose an option:", reply_markup=reply_markup)
        return ADMIN_MENU
    else:
        await update.message.reply_text("Incorrect password. Please try again:")
        return ADMIN_PASSWORD


# -------------------- Admin Menu --------------------
async def admin_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "admin_add":
        await query.edit_message_text("Please send me the video file to add.")
        return ADMIN_ADD_WAIT_VIDEO
    elif query.data == "admin_remove":
        await query.edit_message_text("Please send me the command name you want to remove.")
        return ADMIN_REMOVE
    elif query.data == "admin_end":
        user_modes.pop(user_id, None)  # End admin session
        await query.edit_message_text("Admin session ended. Please select mode again.")
        keyboard = [
            [
                InlineKeyboardButton("User", callback_data="mode_user"),
                InlineKeyboardButton("Admin", callback_data="mode_admin"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select mode:", reply_markup=reply_markup)
        return SELECT_MODE


# -------------------- Admin: Add Video - Receive File --------------------
async def admin_add_video(update: Update, context):
    user_id = update.message.from_user.id
    file_obj = None
    if update.message.video:
        file_obj = update.message.video
    elif update.message.document:
        file_obj = update.message.document
    if file_obj is None:
        await update.message.reply_text("Please send a valid video file.")
        return ADMIN_ADD_WAIT_VIDEO
    # Download the file
    file_id = file_obj.file_id
    telegram_file = await context.bot.get_file(file_id)
    os.makedirs("videos", exist_ok=True)
    filename = f"video_{user_id}_{int(time.time())}.mp4"
    file_path = os.path.join("videos", filename)
    await telegram_file.download_to_drive(file_path)
    # Save the file path temporarily for this admin user.
    admin_temp[user_id] = {"video": file_path}
    await update.message.reply_text("Video received. Now send me the command name for this video:")
    return ADMIN_ADD_WAIT_NAME


# -------------------- Admin: Add Video - Receive Command Name --------------------
async def admin_add_name(update: Update, context):
    user_id = update.message.from_user.id
    command_name = update.message.text.strip()
    if user_id not in admin_temp or "video" not in admin_temp[user_id]:
        await update.message.reply_text("No video file received. Please start the Add process again.")
        return ADMIN_MENU
    file_path = admin_temp[user_id]["video"]
    # If command name exists, append the video; otherwise, create a new entry.
    if command_name in VIDEO_LIBRARY:
        VIDEO_LIBRARY[command_name].append(file_path)
    else:
        VIDEO_LIBRARY[command_name] = [file_path]
    await update.message.reply_text(f"Video added under command '{command_name}'.")
    admin_temp.pop(user_id, None)
    keyboard = [
        [
            InlineKeyboardButton("Add", callback_data="admin_add"),
            InlineKeyboardButton("Remove", callback_data="admin_remove"),
        ],
        [InlineKeyboardButton("End_session", callback_data="admin_end")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin menu:", reply_markup=reply_markup)
    return ADMIN_MENU


# -------------------- Admin: Remove Video Command --------------------
async def admin_remove(update: Update, context):
    user_id = update.message.from_user.id
    command_name = update.message.text.strip()
    if command_name in VIDEO_LIBRARY:
        VIDEO_LIBRARY.pop(command_name)
        await update.message.reply_text(f"Command '{command_name}' and its videos have been removed.")
    else:
        await update.message.reply_text(f"Command '{command_name}' not found.")
    keyboard = [
        [
            InlineKeyboardButton("Add", callback_data="admin_add"),
            InlineKeyboardButton("Remove", callback_data="admin_remove"),
        ],
        [InlineKeyboardButton("End_session", callback_data="admin_end")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin menu:", reply_markup=reply_markup)
    return ADMIN_MENU


# -------------------- User: Handle Video Category Selection --------------------
async def user_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    # Extract the chosen command from the callback data.
    # Expected format: "user_select_<command>"
    chosen = query.data.replace("user_select_", "", 1)
    print(f"User selected command: {chosen}")
    if chosen in VIDEO_LIBRARY:
        video_paths = VIDEO_LIBRARY[chosen]
        for video_path in video_paths:
            if not os.path.exists(video_path):
                await query.message.reply_text(f"Video file not found: {video_path}")
                continue
            try:
                await query.message.reply_text(f"Sending video: {video_path}")
                with open(video_path, 'rb') as video_file:
                    await query.message.reply_video(video=video_file)
            except Exception as e:
                await query.message.reply_text(f"An error occurred: {str(e)}")
        # After sending videos, offer the choice to send another video or end the session.
        keyboard = [
            [
                InlineKeyboardButton("Send another video", callback_data="user_again"),
                InlineKeyboardButton("End session", callback_data="user_end"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Choose an option:", reply_markup=reply_markup)
    else:
        await query.message.reply_text("Unknown command.")


# -------------------- User Choice Callback Handler --------------------
async def user_choice(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "user_again":
        # Resend the list of available video categories.
        if VIDEO_LIBRARY:
            buttons = []
            for command in VIDEO_LIBRARY.keys():
                buttons.append([InlineKeyboardButton(command, callback_data=f"user_select_{command}")])
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text("Choose a video category:", reply_markup=reply_markup)
        else:
            await query.edit_message_text("No video categories available.")
    elif query.data == "user_end":
        if user_id in user_modes:
            user_modes.pop(user_id, None)
        await query.edit_message_text("Session ended. Please send /start to select a mode.")


# -------------------- User End Session (Command) --------------------
async def user_end_session(update: Update, context):
    user_id = update.message.from_user.id
    if user_id in user_modes:
        user_modes.pop(user_id, None)
    await update.message.reply_text("Session ended. Please send /start to select a mode.")
    

# -------------------- Global Error Handler --------------------
async def error_handler(update: object, context):
    print("Exception while handling an update:")
    traceback_str = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    print(traceback_str)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("There is some error. Returning to mode selection.")
        except Exception as e:
            print(f"Failed to send error message: {e}")
        try:
            await update.effective_message.reply_text("Please send /start to select a mode.")
        except Exception as e:
            print(f"Failed to restart conversation: {e}")


# -------------------- Main --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_MODE: [CallbackQueryHandler(select_mode)],
            ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_password)],
            ADMIN_MENU: [CallbackQueryHandler(admin_menu)],
            ADMIN_ADD_WAIT_VIDEO: [MessageHandler(filters.VIDEO | filters.Document.ALL, admin_add_video)],
            ADMIN_ADD_WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_name)],
            ADMIN_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_remove)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    # Remove the plain text send_video handler since user commands are now via inline buttons.
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_video))
    app.add_handler(CommandHandler("end_session", user_end_session))
    app.add_handler(CallbackQueryHandler(user_choice, pattern="^(user_again|user_end)$"))
    # Handler for user selection of video category.
    app.add_handler(CallbackQueryHandler(user_select, pattern="^user_select_.*$"))
    app.add_error_handler(error_handler)

    print("Bot is starting...")
    try:
        app.run_polling()
    except Conflict as e:
        print("Another instance of the bot is already running. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
