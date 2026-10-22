import os
import logging
from threading import Thread
import time

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, jsonify, request
app = Flask(__name__)

# Almacenamiento en memoria con soporte para carpetas por usuario
# Estructura: { user_id: { "Nombre_Carpeta": [ {id, name, size, category}, ... ] } }
user_files_database = {}

@app.route('/')
def home():
    return "Archivebot-pro backend is running with folder support!", 200

# Ruta API para que la MiniApp obtenga las carpetas y archivos del usuario
@app.route('/api/files', methods=['GET'])
def get_files():
    # Puedes pasar el user_id por parámetros (ej: /api/files?user_id=123) o devolver una por defecto para pruebas
    user_id = request.args.get('user_id', 'default_user')
    
    # Si el usuario no tiene registros, le creamos una estructura inicial con una carpeta "General"
    if user_id not in user_files_database:
        user_files_database[user_id] = {
            "General": []
        }
        
    return jsonify(user_files_database[user_id])


# --- HILO DEL BOT DE TELEGRAM ---
def run_telegram_bot():
    time.sleep(3)
    logger.info("Iniciando bucle de Telegram con soporte de carpetas...")
    try:
        import telebot
        TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not TOKEN:
            logger.error("¡Falta el TELEGRAM_BOT_TOKEN en las variables de entorno!")
            return
        
        bot = telebot.TeleBot(TOKEN)
        
        @bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            bot.reply_to(message, "¡Hola! Envíame archivos o carpetas completas y los organizaré en tu panel.")

        # Manejador de archivos y documentos reales
        @bot.message_handler(content_types=['photo', 'document', 'video', 'audio', 'voice'])
        def handle_user_files(message):
            try:
                user_id = str(message.chat.id)
                carpeta_actual = "General" # Carpeta por defecto donde caen los archivos sueltos
                
                # Inicializar estructura del usuario si no existe
                if user_id not in user_files_database:
                    user_files_database[user_id] = {carpeta_actual: []}
                
                if carpeta_actual not in user_files_database[user_id]:
                    user_files_database[user_id][carpeta_actual] = []

                file_name = "archivo_sin_nombre"
                file_size_mb = 1.0
                category = "documents"

                if message.content_type == 'photo':
                    category = "photos"
                    file_name = f"foto_{message.photo[-1].file_unique_id}.jpg"
                    file_size_mb = round(message.photo[-1].file_size / (1024 * 1024), 2) if hasattr(message.photo[-1], 'file_size') else 1.5
                
                elif message.content_type == 'document':
                    category = "documents"
                    file_name = message.document.file_name or "documento.pdf"
                    file_size_mb = round(message.document.file_size / (1024 * 1024), 2)

                elif message.content_type == 'video':
                    category = "videos"
                    file_name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
                    file_size_mb = round(message.video.file_size / (1024 * 1024), 2)

                elif message.content_type in ['audio', 'voice']:
                    category = "audios"
                    audio_obj = message.audio if message.content_type == 'audio' else message.voice
                    file_name = getattr(audio_obj, 'file_name', f"audio_{audio_obj.file_unique_id}.ogg")
                    file_size_mb = round(audio_obj.file_size / (1024 * 1024), 2)

                new_entry = {
                    "id": str(len(user_files_database[user_id][carpeta_actual]) + 1),
                    "name": file_name,
                    "size": file_size_mb,
                    "category": category
                }
                
                user_files_database[user_id][carpeta_actual].append(new_entry)
                bot.reply_to(message, f"📁 Guardado en carpeta [{carpeta_actual}]: {file_name} ({file_size_mb} MB)")

            except Exception as e:
                logger.error(f"Error procesando archivo: {e}")
                bot.reply_to(message, "Hubo un error al procesar tu archivo.")

        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Error en el hilo del bot: {e}")

bot_thread = Thread(target=run_telegram_bot, daemon=True)
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
