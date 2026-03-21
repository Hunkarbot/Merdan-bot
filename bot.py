import os
from telegram.ext import ApplicationBuilder, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("Bot aktif kral ✅")

def main():
    app=
ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
print("Bot çalışıyor...")
app.run_polling()

if __name__ == "__main__":
   main() 
