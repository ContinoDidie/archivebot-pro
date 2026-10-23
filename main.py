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
                category TEXT DEFAULT 'documento',
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

    finally:
        connection.close()


def get_user_files(user_id):
    connection = get_db()

    try:
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

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_file_record(file_id, user_id):
    connection = get_db()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM files
            WHERE id = ?
            AND user_id = ?
            """,
            (file_id, user_id)
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


# =========================================================
# VALIDACIÓN DE TELEGRAM MINI APP
# =========================================================

def validate_telegram_init_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None

    try:
        parsed_data = dict(
            parse_qsl(
                init_data,
                keep_blank_values=True
            )
        )

        received_hash = parsed_data.pop("hash", None)

        if not received_hash:
            return None

        auth_date = int(
            parsed_data.get("auth_date", "0")
        )

        current_time = int(time.time())

        if auth_date <= 0:
            return None

        if current_time - auth_date > MAX_INIT_DATA_AGE:
            return None

        if auth_date - current_time > 60:
            return None

       
