import os
import time
import logging
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
import threading
import telebot

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')

# Base de datos en memoria (volatile)
user_files_database = {}

# --- RUTAS WEB Y API ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health_check():
    return "OK", 200

@app.route('/api/files', methods=['GET'])
def get_files():
    # Biblioteca unificada que junta todos los archivos de cualquier usuario para la MiniApp
    global_library = {
        "photos": [],
        "videos": [],
        "documents": [],
        "audios": []
    }
    
    for uid, categories in user_files_database.items():
        for cat in ["photos", "videos", "documents", "audios"]:
            if cat in categories:
                for file in categories[cat]:
                    if not any(f['name'] == file['name'] for f in global_library[cat]):
                        global_library[cat].append(file)
                        
    return jsonify(global_library)


# --- HILO DEL BOT DE TELEGRAM ---
def run_telegram_bot():
    # Esperar un momento prudente para que el puerto web abra primero
    time.sleep(3)
    logger.info("Iniciando configuración del bot de Telegram...")
    
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not TOKEN:
        logger.error("¡Falta el TELEGRAM_BOT_TOKEN en las variables de entorno!")
        return
    
    bot = telebot.TeleBot(TOKEN)
    
    # Limpiar cualquier conexión previa colgada
    try:
        bot.remove_webhook()
    except Exception:
        pass
    
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        try:
            bot.reply_to(message, "¡Hola! Envíame fotos, videos, documentos o audios y aparecerán sincronizados en tu biblioteca web.")
        except Exception as e:
            logger.error(f"Error en send_welcome: {e}")

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
            file_mime = "Desconocido"

            if message.content_type == 'photo':
                category = "photos"
                if message.photo:
                    p = message.photo[-1]
                    file_name = f"foto_{getattr(p, 'file_unique_id', 'unknown')}.jpg"
                    size_bytes = getattr(p, 'file_size', 102400) or 102400
                    file_size_mb = round(size_bytes / (1024 * 1024), 2)
                file_mime = "image/jpeg"
            
            elif message.content_type == 'document' and message.document:
                category = "documents"
                doc = message.document
                file_name = getattr(doc, 'file_name', None) or "documento.pdf"
                size_bytes = getattr(doc, 'file_size', 102400) or 102400
                file_size_mb = round(size_bytes / (1024 * 1024), 2)
                file_mime = getattr(doc, 'mime_type', 'application/octet-stream')

            elif message.content_type == 'video' and message.video:
                category = "videos"
                vid = message.video
                file_name = getattr(vid, 'file_name', None) or f"video_{getattr(vid, 'file_unique_id', 'unknown')}.mp4"
                size_bytes = getattr(vid, 'file_size', 102400) or 102400
                file_size_mb = round(size_bytes / (1024 * 1024), 2)
                file_mime = getattr(vid, 'mime_type', 'video/mp4')

            elif message.content_type in ['audio', 'voice']:
                category = "audios"
                audio_obj = message.audio if message.content_type == 'audio' else message.voice
                if audio_obj:
                    file_name = getattr(audio_obj, 'file_name', None) or f"audio_{getattr(audio_obj, 'file_unique_id', 'unknown')}.ogg"
                    size_bytes = getattr(audio_obj, 'file_size', 102400) or 102400
                    file_size_mb = round(size_bytes / (1024 * 1024), 2)
                    file_mime = getattr(audio_obj, 'mime_type', 'audio/ogg')

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            new_entry = {
                "id": str(len(user_files_database[user_id][category]) + 1),
                "name": file_name,
                "size": file_size_mb,
                "mime": file_mime,
                "date": now_str,
                "category": category
            }
            
            # Evitar duplicados exactos
            if not any(f['name'] == file_name for f in user_files_database[user_id][category]):
                user_files_database[user_id][category].append(new_entry)

            bot.reply_to(message, f"✅ Archivo guardado en [{category}]: {file_name} ({file_size_mb} MB)")
            logger.info(f"Archivo guardado exitosamente para el usuario {user_id} en {category}: {file_name}")

        except Exception as e:
            logger.error(f"Error procesando archivo de Telegram: {e}")
            try:
                bot.reply_to(message, "Hubo un error al procesar tu archivo.")
            except:
                pass

    # Bucle de escucha continuo con reconexión automática ante conflictos o cortes de red
    while True:
        try:
            logger.info("Bot de Telegram conectado y escuchando mensajes...")
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            logger.error(f"Desconexión o conflicto en el bot ({e}). Reintentando en 10 segundos...")
            time.sleep(10)


# --- INICIO DE LA APLICACIÓN ---
if __name__ == '__main__':
    # Lanzar el bot de Telegram en un hilo en segundo plano
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Iniciar el servidor Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
