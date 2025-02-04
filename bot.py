import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

BOT_TOKEN = "7576613965:AAFx5d6fvfqXPofEyD-r1g1HN43AgyxHt4s"

VIDEO_LIBRARY = {
    "Reject": "video.mp4",  # The video file should be in the same directory as the script
}


async def start(update: Update, context):
    print("Received /start command")  # Log when /start is received
    await update.message.reply_text("Send me a command without '/' (like Reject) to get a meme video.")


async def send_video(update: Update, context):
    # Strip the slash (if present) from the message
    text = update.message.text.strip().lstrip("/")  # Remove leading slash if present
    print(f"Received message: {update.message.text} (command: {text})")  # Log received message

    if text in VIDEO_LIBRARY:
        video_path = VIDEO_LIBRARY[text]

        print(f"Video path: {video_path}")  # Log video path

        if not os.path.exists(video_path):
            await update.message.reply_text(f"Video file not found at the specified path: {video_path}")
            print(f"File not found: {video_path}")  # Log file missing
            return

        try:
            await update.message.reply_text(f"Sending video: {video_path}")
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(video=video_file)
            print(f"Video sent: {video_path}")  # Log successful video sending
        except Exception as e:
            await update.message.reply_text(f"An error occurred: {str(e)}")
            print(f"Error: {str(e)}")  # Log the error
    else:
        await update.message.reply_text("Unknown command.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add both the /start handler and the message handler for all text commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, send_video))  # Handle all text messages (not commands)

    print("Bot is starting...")  # Log when the bot starts
    app.run_polling()


if __name__ == "__main__":
    main()
