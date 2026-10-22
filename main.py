import os
import logging
from threading import Thread
import time
from flask import Flask, jsonify, request, send_from_directory

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuramos Flask para servir archivos desde la misma carpeta del proyecto
app = Flask(__name__, static_folder='.', static_url_path='')

# Almacenamiento en memoria para los archivos reales de Telegram
user_files_database = {}

# 1. Ruta principal que sirve tu interfaz visual (index.html)
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# 2. Ruta API que consulta la MiniApp para obtener los archivos reales por categoría
@app.route('/api/files', methods=['GET'])
def get_files():
    user_id = request.args.get('user_id', 'default_user')
    
    if user_id not in user_files_database:
        user_files_database[user_id] = {
            "photos": [],
            "videos": [],
            "documents": [],
            "audios": []
        }
    return jsonify(user_files_database[user_id])


# --- HILO DEL BOT DE TELEGRAM ---
def run_telegram_bot():
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
            bot.reply_to(message, "¡Hola! Envíame fotos, videos, documentos o audios y aparecerán en tu panel web.")

        @bot.message_handler(content_types=['photo', 'document', 'video', 'audio', 'voice'])
        def handle_user_files(message):
            try:
                user_id = str(message.chat.id)
                
                if user_id not in user_files_database:
                    user_files_database[user_id] = {
                        "photos": [],
                        "videos": [],
                        "documents": [],
                        "audios": []
                    }

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
                    "id": str(len(user_files_database[user_id][category]) + 1),
                    "name": file_name,
                    "size": file_size_mb
                }
                
                user_files_database[user_id][category].append(new_entry)
                bot.reply_to(message, f"✅ Archivo guardado en [{category}]: {file_name} ({file_size_mb} MB)")

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
