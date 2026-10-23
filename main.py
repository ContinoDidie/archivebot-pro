import os
import io
import hmac
import hashlib
import json
import sqlite3
import logging
import threading
import time
import zipfile

from datetime import datetime, timezone
from urllib.parse import parse_qsl
from functools import wraps

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import telebot


# =========================================================
# ARCHIVEBOT PRO - CONFIGURACIÓN
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("archivebot")

BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

PORT = int(os.environ.get("PORT", "10000"))

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    "archivebot.db"
)

MAX_FILES_PER_ZIP = 50
MAX_INIT_DATA_AGE = 86400

app = Flask(__name__, static_folder='.', static_url_path='')

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    },
    allow_headers=[
        "Content-Type",
        "X-Telegram-Init-Data"
    ],
    methods=["GET", "POST", "OPTIONS"]
)

api_bot = None
bot_lock = threading.Lock()


# =========================================================
# BASE DE DATOS SQLITE
# =========================================================

def get_db():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_unique_id TEXT,
                name TEXT NOT NULL,
                size INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT '',
                category TEXT DEFAULT 'documentos',
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_user
            ON files(user_id)
        """)
        connection.commit()
        logger.info("Base de datos inicializada correctamente.")
    finally:
        connection.close()


def save_file(
    user_id,
    file_id,
    file_unique_id,
    name,
    size,
    mime_type,
    category
):
    connection = get_db()
    try:
        existing = None
        if file_unique_id:
            existing = connection.execute(
                """
                SELECT id
                FROM files
                WHERE user_id = ?
                AND file_unique_id = ?
                """,
                (user_id, file_unique_id)
            ).fetchone()

        size_mb = round(size / (1024 * 1024), 2) if size else 0.1

        if existing:
            connection.execute(
                """
                UPDATE files
                SET file_id = ?,
                    name = ?,
                    size = ?,
                    mime_type = ?,
                    category = ?
                WHERE id = ?
                """,
                (
                    file_id,
                    name,
                    size_mb,
                    mime_type or "",
                    category,
                    existing["id"]
                )
            )
        else:
            connection.execute(
                """
                INSERT INTO files (
                    user_id,
                    file_id,
                    file_unique_id,
                    name,
                    size,
                    mime_type,
                    category,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    file_id,
                    file_unique_id,
                    name,
                    size_mb,
                    mime_type or "",
                    category,
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                )
            )
        connection.commit()
    finally:
        connection.close()


# =========================================================
# RUTAS WEB Y API
# =========================================================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health_check():
    return "OK", 200

@app.route('/api/files', methods=['GET'])
def get_files():
    connection = get_db()
    try:
        rows = connection.execute("SELECT * FROM files ORDER BY id DESC").fetchall()
        
        global_library = {
            "photos": [],
            "videos": [],
            "documents": [],
            "audios": []
        }
        
        for row in rows:
            file_data = {
                "id": str(row["id"]),
                "name": row["name"],
                "size": row["size"],
                "mime": row["mime_type"],
                "date": row["created_at"],
                "category": row["category"]
            }
            
            cat = row["category"]
            if cat in global_library:
                if not any(f['name'] == file_data['name'] for f in global_library[cat]):
                    global_library[cat].append(file_data)
                    
        return jsonify(global_library)
    except Exception as e:
        logger.error(f"Error en /api/files: {e}")
        return jsonify({"photos": [], "videos": [], "documents": [], "audios": []})
    finally:
        connection.close()


# =========================================================
# HILO DEL BOT DE TELEGRAM
# =========================================================

def run_telegram_bot():
    time.sleep(3)
    logger.info("Iniciando configuración del bot de Telegram...")
    
    if not BOT_TOKEN:
        logger.error("¡Falta el TELEGRAM_BOT_TOKEN en las variables de entorno!")
        return
    
    bot = telebot.TeleBot(BOT_TOKEN)
    
    try:
        bot.remove_webhook()
        logger.info("Webhook anterior eliminado.")
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
            user_id = message.chat.id
            file_id = ""
            file_unique_id = ""
            file_name = "archivo_sin_nombre"
            size_bytes = 102400
            category = "documents"
            file_mime = "Desconocido"

            if message.content_type == 'photo':
                category = "photos"
                if message.photo:
                    p = message.photo[-1]
                    file_id = p.file_id
                    file_unique_id = getattr(p, 'file_unique_id', '')
                    file_name = f"foto_{file_unique_id[:8]}.jpg"
                    size_bytes = getattr(p, 'file_size', 102400) or 102400
                file_mime = "image/jpeg"
            
            elif message.content_type == 'document' and message.document:
                category = "documents"
                doc = message.document
                file_id = doc.file_id
                file_unique_id = getattr(doc, 'file_unique_id', '')
                file_name = getattr(doc, 'file_name', None) or "documento.pdf"
                size_bytes = getattr(doc, 'file_size', 102400) or 102400
                file_mime = getattr(doc, 'mime_type', 'application/octet-stream')

            elif message.content_type == 'video' and message.video:
                category = "videos"
                vid = message.video
                file_id = vid.file_id
                file_unique_id = getattr(vid, 'file_unique_id', '')
                file_name = getattr(vid, 'name', None) or f"video_{file_unique_id[:8]}.mp4"
                size_bytes = getattr(vid, 'file_size', 102400) or 102400
                file_mime = getattr(vid, 'mime_type', 'video/mp4')

            elif message.content_type in ['audio', 'voice']:
                category = "audios"
                audio_obj = message.audio if message.content_type == 'audio' else message.voice
                if audio_obj:
                    file_id = audio_obj.file_id
                    file_unique_id = getattr(audio_obj, 'file_unique_id', '')
                    file_name = getattr(audio_obj, 'file_name', None) or f"audio_{file_unique_id[:8]}.ogg"
                    size_bytes = getattr(audio_obj, 'file_size', 102400) or 102400
                    file_mime = getattr(audio_obj, 'mime_type', 'audio/ogg')

            save_file(user_id, file_id, file_unique_id, file_name, size_bytes, file_mime, category)
            bot.reply_to(message, f"✅ Archivo guardado en [{category}]: {file_name}")
            logger.info(f"Archivo guardado para el usuario {user_id} en {category}: {file_name}")

        except Exception as e:
            logger.error(f"Error procesando archivo de Telegram: {e}")

    while True:
        try:
            logger.info("Bot de Telegram conectado y escuchando mensajes...")
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            logger.error(f"Desconexión en el bot ({e}). Reintentando en 10 segundos...")
            time.sleep(10)


# =========================================================
# INICIO DE LA APLICACIÓN
# =========================================================
@app.route('/api/download/<int:file_id>', methods=['GET'])
def download_file(file_id):
    connection = get_db()
    try:
        row = connection.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            return "Archivo no encontrado", 404
        
        tg_file_id = row["file_id"]
        file_name = row["name"]
        
        # Consultar la ruta real del archivo en los servidores de Telegram
        token = BOT_TOKEN
        import urllib.request
        import json
        
        url_info = f"https://api.telegram.org/bot{token}/getFile?file_id={tg_file_id}"
        req = urllib.request.urlopen(url_info)
        res_data = json.loads(req.read().decode('utf-8'))
        
        if not res_data.get("ok"):
            return "No se pudo recuperar el archivo de Telegram", 400
            
        file_path = res_data["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        
        # Redirigir directamente al enlace seguro de descarga de Telegram
        return jsonify({"download_url": download_url})
        
    except Exception as e:
        logger.error(f"Error en descarga: {e}")
        return "Error interno al procesar la descarga", 500
    finally:
        connection.close()

if __name__ == '__main__':
    init_db()
    
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    app.run(host="0.0.0.0", port=PORT)
