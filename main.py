import os
import logging
from threading import Thread
from flask import Flask

# Configuración básica de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. SERVIDOR FLASK PARA RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Archivebot-pro está activo y funcionando en Render.", 200

def run_flask():
    # Obtiene el puerto asignado dinámicamente por Render (por defecto 5000)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Inicia el servidor Flask en segundo plano antes de arrancar el bot
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()
logger.info("Servidor HTTP interno de Flask iniciado para Render.")


# --- 2. CÓDIGO DEL BOT DE TELEGRAM ---
# Importa aquí las librerías que utilices para tu bot
import telebot # O 'from telegram.ext import ApplicationBuilder', etc.

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TU_TOKEN_AQUI")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! Archivebot-pro está en línea y escuchando.")

# Si tienes otros handlers o funciones de tu bot, agrégalos aquí...


# --- 3. BUCLE PRINCIPAL DE EJECUCIÓN ---
if __name__ == "__main__":
    logger.info("Iniciando el polling de Telegram para Archivebot-pro...")
    try:
        # Bucle continuo para recibir mensajes de Telegram
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Error en el bucle principal del bot: {e}")
