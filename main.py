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

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import telebot


# =========================================================
# CONFIGURACIÓN
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("archivebot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    "archivebot.db"
)

PORT = int(os.environ.get("PORT", "10000"))

MAX_FILES_PER_ZIP = 50
MAX_INIT_DATA_AGE = 86400

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://continodidie.github.io",
                "http://localhost:8000",
                "http://127.0.0.1:8000"
            ]
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
# BASE DE DATOS
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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_unique_id TEXT,
            name TEXT NOT NULL,
            size INTEGER DEFAULT 0,
            mime_type TEXT DEFAULT '',
            category TEXT DEFAULT 'documento',
            created_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_files_user
        ON files(user_id)
    """)

    connection.commit()
    connection.close()

    logger.info("Base de datos inicializada.")


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

    existing = connection.execute(
        """
        SELECT id
        FROM files
        WHERE user_id = ?
        AND file_unique_id = ?
        """,
        (user_id, file_unique_id)
    ).fetchone()

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
                size or 0,
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
                size or 0,
                mime_type or "",
                category,
                datetime.now(timezone.utc).isoformat()
            )
        )

    connection.commit()
    connection.close()


def get_user_files(user_id):
    connection = get_db()

    rows = connection.execute(
        """
        SELECT
            id,
            name,
            size,
            mime_type,
            category,
            created_at
        FROM files
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def get_file_record(file_id, user_id):
    connection = get_db()

    row = connection.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        AND user_id = ?
        """,
        (file_id, user_id)
    ).fetchone()

    connection.close()

    return dict(row) if row else None


# =========================================================
# VALIDACIÓN SEGURA DE TELEGRAM MINI APP
# =========================================================

def validate_telegram_init_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None

    try:
        parsed_data = dict(parse_qsl(
            init_data,
            keep_blank_values=True
        ))

        received_hash = parsed_data.pop("hash", None)

        if not received_hash:
            return None

        auth_date = int(parsed_data.get("auth_date", "0"))

        current_time = int(time.time())

        if auth_date <= 0:
            return None

        if current_time - auth_date > MAX_INIT_DATA_AGE:
            return None

        if auth_date - current_time > 60:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(parsed_data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode("utf-8"),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        user_json = parsed_data.get("user")

        if not user_json:
            return None

        user_data = json.loads(user_json)
        user_id = user_data.get("id")

        if not user_id:
            return None

        return int(user_id)

    except Exception as error:
        logger.warning(
            "No se pudo validar Telegram initData: %s",
            error
        )
        return None


def require_telegram_user(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        init_data = request.headers.get(
            "X-Telegram-Init-Data",
            ""
        )

        user_id = validate_telegram_init_data(init_data)

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Sesión de Telegram inválida o caducada."
            }), 401

        request.telegram_user_id = user_id

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# BOT DE TELEGRAM
# =========================================================

def get_bot():
    global api_bot

    with bot_lock:
        if api_bot is None:
            if not BOT_TOKEN:
                raise RuntimeError(
                    "Falta la variable TELEGRAM_BOT_TOKEN."
                )

            api_bot = telebot.TeleBot(
                BOT_TOKEN,
                threaded=True
            )

        return api_bot


def get_message_file(message):
    file_id = None
    file_unique_id = None
    name = None
    size = 0
    mime_type = ""
    category = "documento"

    if message.document:
        item = message.document

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = item.file_name or f"documento_{item.file_unique_id}"
        size = item.file_size or 0
        mime_type = item.mime_type or ""
        category = "documento"

    elif message.photo:
        item = message.photo[-1]

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = f"foto_{item.file_unique_id}.jpg"
        size = item.file_size or 0
        mime_type = "image/jpeg"
        category = "imagen"

    elif message.video:
        item = message.video

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = item.file_name or f"video_{item.file_unique_id}.mp4"
        size = item.file_size or 0
        mime_type = item.mime_type or "video/mp4"
        category = "video"

    elif message.animation:
        item = message.animation

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = item.file_name or f"animacion_{item.file_unique_id}.mp4"
        size = item.file_size or 0
        mime_type = item.mime_type or "video/mp4"
        category = "video"

    elif message.audio:
        item = message.audio

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = item.file_name or f"audio_{item.file_unique_id}"
        size = item.file_size or 0
        mime_type = item.mime_type or "audio/mpeg"
        category = "audio"

    elif message.voice:
        item = message.voice

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = f"nota_voz_{item.file_unique_id}.ogg"
        size = item.file_size or 0
        mime_type = item.mime_type or "audio/ogg"
        category = "audio"

    elif message.video_note:
        item = message.video_note

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = f"nota_video_{item.file_unique_id}.mp4"
        size = item.file_size or 0
        mime_type = "video/mp4"
        category = "video"

    elif message.sticker:
        item = message.sticker

        file_id = item.file_id
        file_unique_id = item.file_unique_id
        name = f"sticker_{item.file_unique_id}.webp"
        size = item.file_size or 0
        mime_type = "image/webp"
        category = "imagen"

    if not file_id:
        return None

    return {
        "file_id": file_id,
        "file_unique_id": file_unique_id,
        "name": name,
        "size": size,
        "mime_type": mime_type,
        "category": category
    }


def register_bot_handlers(bot):
    @bot.message_handler(
        content_types=[
            "document",
            "photo",
            "video",
            "animation",
            "audio",
            "voice",
            "video_note",
            "sticker"
        ]
    )
    def handle_file(message):
        try:
            if message.chat.type != "private":
                return

            file_data = get_message_file(message)

            if not file_data:
                bot.reply_to(
                    message,
                    "No pude identificar ese archivo. Intenta enviarlo de nuevo."
                )
                return

            save_file(
                user_id=message.from_user.id,
                file_id=file_data["file_id"],
                file_unique_id=file_data["file_unique_id"],
                name=file_data["name"],
                size=file_data["size"],
                mime_type=file_data["mime_type"],
                category=file_data["category"]
            )

           
