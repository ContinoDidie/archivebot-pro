import os
import logging
from threading import Thread
import time

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (OBLIGATORIO PARA RENDER) ---
from flask import Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Archivebot-pro is running!", 200

# --- 2. FUNCIÓN PARA CORRER EL BOT EN SEGUNDO PLANO ---
def run_telegram_bot():
    # Damos unos segundos para que el servidor web responda primero en Render
    time.sleep(3)
    logger.info("Iniciando bucle de Telegram...")
    try:
        import telebot
        TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not TOKEN:
            logger.error("¡Falta el TELEGRAM_BOT_TOKEN en las variables de entorno!")
            return
        
        bot = telebot.TeleBot(TOKEN)
        
        @bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            bot.reply_to(message, "¡Archivebot-pro operativo en Render!")
            
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Error en el hilo del bot de Telegram: {e}")

# Lanzamos el bot en un hilo separado para que NO bloquee el puerto web
bot_thread = Thread(target=run_telegram_bot, daemon=True)
bot_thread.start()

# --- 3. ARRANQUE PRINCIPAL PARA GUNICORN ---
if __name__ == "__main__":
    # Esto se ejecuta si ejecutas python main.py localmente
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
