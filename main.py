import os
import time
import logging
import threading
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
import telebot
from flask_cors import CORS

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".", static_url_path="")

# Permitir que la Mini App alojada en GitHub Pages
# se comunique con el backend alojado en Render.
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://continodidie.github.io"
            ]
        }
    },
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600
)

# Base de datos temporal en memoria.
# IMPORTANTE: los datos se pierden si el proceso se reinicia.
user_files_database = {}

# =========================================================
# RUTAS WEB
# =========================================================

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health_check():
    return jsonify({
        "status": "ok",
        "service": "ArchiveBot Pro",
        "time": datetime.utcnow().isoformat() + "Z"
    }), 200


# =========================================================
# API DE ARCHIVOS
# =========================================================

@app.route("/api/files", methods=["GET", "OPTIONS"])
def get_files():

    # Flask-CORS gestiona las cabeceras CORS.
    if request.method == "OPTIONS":
        return "", 204

    global_library = {
        "photos": [],
        "videos": [],
        "documents": [],
        "audios": []
    }

    # Mantener el comportamiento de biblioteca global
    # de la versión original.
    for uid, categories in user_files_database.items():

        if not isinstance(categories, dict):
            continue

        for category in global_library:

            entries = categories.get(category, [])

            if not isinstance(entries, list):
                continue

            for file_entry in entries:

                if not isinstance(file_entry, dict):
                    continue

                # Evitar duplicados por nombre.
                duplicate = any(
                    existing.get("name") == file_entry.get("name")
                    for existing in global_library[category]
                )

                if not duplicate:
                    global_library[category].append(file_entry)

    logger.info(
        "API /api/files consultada | "
        "Fotos: %s | Videos: %s | Documentos: %s | Audios: %s",
        len(global_library["photos"]),
        len(global_library["videos"]),
        len(global_library["documents"]),
        len(global_library["audios"])
    )

    return jsonify(global_library), 200


# =========================================================
# BOT DE TELEGRAM
# =========================================================

def run_telegram_bot():

    time.sleep(3)

    logger.info("Iniciando configuración del bot de Telegram...")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

    if not token:
        logger.error(
            "Falta TELEGRAM_BOT_TOKEN en las variables de entorno de Render."
        )
        return

    bot = telebot.TeleBot(token)

    try:
        bot.remove_webhook()
        logger.info("Webhook anterior eliminado.")
    except Exception as error:
        logger.warning("No se pudo eliminar el webhook: %s", error)

    # -----------------------------------------------------
    # COMANDO START
    # -----------------------------------------------------

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):

        try:
            bot.reply_to(
                message,
                "¡Hola! 👋\n\n"
                "Envíame fotos, vídeos, documentos o audios "
                "para añadirlos a la biblioteca de ArchiveBot Pro.\n\n"
                "Abre la Mini App desde Telegram para consultar "
                "la biblioteca disponible."
            )

        except Exception as error:
            logger.error("Error en send_welcome: %s", error)

    # -----------------------------------------------------
    # RECEPCIÓN DE ARCHIVOS
    # -----------------------------------------------------

    @bot.message_handler(
        content_types=[
            "photo",
            "document",
            "video",
            "audio",
            "voice"
        ]
    )
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
            file_size_mb = 0.1
            category = "documents"
            file_mime = "application/octet-stream"

            # FOTO
            if message.content_type == "photo":

                category = "photos"

                if message.photo:
                    photo = message.photo[-1]

                    file_name = (
                        f"foto_{photo.file_unique_id}.jpg"
                    )

                    size_bytes = (
                        getattr(photo, "file_size", None) or 102400
                    )

                    file_size_mb = round(
                        size_bytes / (1024 * 1024), 2
                    )

                file_mime = "image/jpeg"

            # DOCUMENTO
            elif (
                message.content_type == "document"
                and message.document
            ):

                document = message.document
                category = "documents"

                file_name = (
                    getattr(document, "file_name", None)
                    or f"documento_{document.file_unique_id}"
                )

                size_bytes = (
                    getattr(document, "file_size", None) or 102400
                )

                file_size_mb = round(
                    size_bytes / (1024 * 1024), 2
                )

                file_mime = (
                    getattr(document, "mime_type", None)
                    or "application/octet-stream"
                )

            # VÍDEO
            elif (
                message.content_type == "video"
                and message.video
            ):

                video = message.video
                category = "videos"

                file_name = (
                    getattr(video, "file_name", None)
                    or f"video_{video.file_unique_id}.mp4"
                )

                size_bytes = (
                    getattr(video, "file_size", None) or 102400
                )

                file_size_mb = round(
                    size_bytes / (1024 * 1024), 2
                )

                file_mime = (
                    getattr(video, "mime_type", None)
                    or "video/mp4"
                )

            # AUDIO O MENSAJE DE VOZ
            elif message.content_type in ["audio", "voice"]:

                audio_obj = (
                    message.audio
                    if message.content_type == "audio"
                    else message.voice
                )

                category = "audios"

                if audio_obj:

                    file_name = (
                        getattr(audio_obj, "file_name", None)
                        or f"audio_{audio_obj.file_unique_id}.ogg"
                    )

                    size_bytes = (
                        getattr(audio_obj, "file_size", None) or 102400
                    )

                    file_size_mb = round(
                        size_bytes / (1024 * 1024), 2
                    )

                    file_mime = (
                        getattr(audio_obj, "mime_type", None)
                        or "audio/ogg"
                    )

            now_str = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            entries = user_files_database[user_id][category]

            # Evitar duplicar el mismo archivo en la misma categoría.
            existing = any(
                entry.get("name") == file_name
                for entry in entries
            )

            if existing:

                bot.reply_to(
                    message,
                    f"ℹ️ Este archivo ya está registrado: {file_name}"
                )

                return

            new_entry = {
                "id": str(len(entries) + 1),
                "name": file_name,
                "size": file_size_mb,
                "mime": file_mime,
                "date": now_str,
                "category": category
            }

            entries.append(new_entry)

            bot.reply_to(
                message,
                f"✅ Archivo registrado en {category}:\n"
                f"{file_name}\n"
                f"📦 Tamaño aproximado: {file_size_mb} MB"
            )

            logger.info(
                "Archivo registrado para usuario %s | %s | %s",
                user_id,
                category,
                file_name
            )

        except Exception as error:

            logger.exception(
                "Error procesando archivo de Telegram"
            )

            try:
                bot.reply_to(
                    message,
                    "❌ Hubo un error al procesar el archivo. "
                    "Inténtalo de nuevo."
                )
            except Exception:
                pass

    # -----------------------------------------------------
    # ESCUCHA CONTINUA DEL BOT
    # -----------------------------------------------------

    while True:

        try:
            logger.info(
                "Bot de Telegram conectado y escuchando mensajes..."
            )

            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=20,
                skip_pending=True
            )

        except Exception as error:

            logger.exception(
                "Desconexión o conflicto del bot: %s",
                error
            )

            time.sleep(10)


# =========================================================
# INICIO DEL SERVIDOR
# =========================================================

if __name__ == "__main__":

    bot_thread = threading.Thread(
        target=run_telegram_bot,
        daemon=True
    )

    bot_thread.start()

    port = int(os.environ.get("PORT", 5000))

    logger.info("Iniciando servidor Flask en el puerto %s", port)

    app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )
