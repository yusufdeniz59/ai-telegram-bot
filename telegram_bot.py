from datetime import datetime

# Telegram bot entegrasyonu
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from configparser import ConfigParser
import sys
import openai
from rag_engine import retrieve_memory
from web_data_engine import get_weather, get_exchange_rates, get_tr_news, get_world_news, get_daily_briefing, should_use_web, get_web_summary

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
config = ConfigParser()
config.read('config/settings.ini')

# Get bot token from environment variable or config
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    BOT_TOKEN = config.get('Telegram', 'bot_token', fallback=None)

# Get OpenAI API key from environment variable or config
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    OPENAI_API_KEY = config.get('OpenAI', 'api_key', fallback=None)

if not BOT_TOKEN:
    logger.error("No bot token found in environment variable TELEGRAM_BOT_TOKEN or config/settings.ini")
    sys.exit(1)

if not OPENAI_API_KEY:
    logger.warning("No OpenAI API key found in environment variable OPENAI_API_KEY or config/settings.ini")

# Use the new OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_openai_response(prompt: str) -> str:
    try:
        # Tarih ve temel prompt
        today = datetime.now().strftime("%d.%m.%Y %A %H:%M")
        with open("prompts/system_prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()

        # Hafızadan ilgili bilgi getir
        memory_context = retrieve_memory(prompt)

        # Promptu birleştir
        system_prompt = f"TODAY: {today}\n{base_prompt}\n\nRELATED MEMORY:\n{memory_context}"

        # GPT çağrısı (new OpenAI API)
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        import traceback
        logger.error("OpenAI API error: %s", e)
        logger.error(traceback.format_exc())
        return f"Sorry, I couldn't process your request right now. ({e})"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Hello! I am your AI assistant. How can I help you today?')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text('🤖 DigiMe AI Asistan - Komutlar:\n\n'
                                  '📋 Temel Komutlar:\n'
                                  '/start - Botu başlat\n'
                                  '/help - Bu yardım mesajını göster\n\n'
                                  '🔍 Web Arama:\n'
                                  '/search <terim> - Güncel bilgi ara\n'
                                  'Örnek: /search iran israil savaşı\n\n'
                                  '📊 Güncel Bilgiler:\n'
                                  '/weather - Hava durumu\n'
                                  '/exchange - Döviz kurları\n'
                                  '/trnews - Türkiye haberleri\n'
                                  '/worldnews - Dünya haberleri\n\n'
                                  '💬 Normal Sohbet:\n'
                                  'Güncel olaylar hakkında soru sorabilirsin\n'
                                  'Örnek: "iran israil savaşı son durum nedir?"')

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = get_weather()
    await update.message.reply_text(result)

async def exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = get_exchange_rates()
    await update.message.reply_text(result)

async def tr_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = get_tr_news()
    await update.message.reply_text(result)

async def world_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = get_world_news()
    await update.message.reply_text(result)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search the web for current information"""
    try:
        # Get the search query from the command arguments
        query = ' '.join(context.args)
        
        if not query:
            await update.message.reply_text("🔍 Kullanım: /search <arama terimi>\nÖrnek: /search iran israil savaşı")
            return
        
        await update.message.reply_text(f"🔍 '{query}' için güncel bilgi aranıyor...")
        summary = get_web_summary(query)
        await update.message.reply_text(summary)
        
    except Exception as e:
        logger.error(f"Error in search command: {e}")
        await update.message.reply_text("Arama sırasında bir hata oluştu.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    try:
        user_message = update.message.text

        # Eğer mesaj güncel bilgiyle ilgiliyse (web arama)
        if should_use_web(user_message):
            await update.message.reply_text("🔍 Güncel bilgi aranıyor...")
            summary = get_web_summary(user_message)
            await update.message.reply_text(summary)
            return

        # Eğer mesaj güncel bilgiyle ilgiliyse (basit anahtar kelime filtresi)
        if any(word in user_message.lower() for word in ["hava", "piyasa", "gündem", "haber", "dolar", "euro", "altın", "dünya", "kur", "bülten", "günlük"]):
            briefing = get_daily_briefing()
            await update.message.reply_text(briefing)
            return

        # Geri kalan normal GPT hafıza tabanlı yanıtlar burada
        ai_reply = get_openai_response(user_message)
        await update.message.reply_text(ai_reply)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("Sorry, I encountered an error processing your message.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, I encountered an error while processing your request."
        )

async def delete_webhook():
    """Delete any existing webhook."""
    try:
        async with Application.builder().token(BOT_TOKEN).build() as app:
            await app.bot.delete_webhook()
            logger.info("Successfully deleted webhook")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")

def main():
    """Start the bot."""
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CommandHandler("weather", weather_command))
        application.add_handler(CommandHandler("exchange", exchange_command))
        application.add_handler(CommandHandler("trnews", tr_news_command))
        application.add_handler(CommandHandler("worldnews", world_news_command))
        application.add_handler(CommandHandler("search", search_command))
        
        # Add error handler
        application.add_error_handler(error_handler)

        # Start the Bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()