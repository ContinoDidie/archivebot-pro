import os
import re
import io
import json
import time
import sqlite3
import logging
import zipfile
import threading

from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    jsonify,
    request,
    send_file,
    send_from_directory
)

# =========================================================
# ARCHIVEBOT PRO
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("archivebot")

app = Flask(__name__, static_folder=".", static_url_path="")

# Render puede borrar estos archivos al reiniciar el servicio.
# ARCHIVE_DIR permite configurar otra ruta si posteriormente
# añadimos almacenamiento persistente.
DATA_DIR = Path(os.environ.get("ARCHIVE_DIR", "/tmp/archivebot_data"))
FILES_DIR = DATA_DIR / "files"
DB_PATH = DATA_DIR / "archivebot.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)

# Plan gratuito: 500 MiB por usuario.
USER_LIMIT = 500 * 1024 * 1024

db_lock = threading.RLock()
bot_lock = threading.Lock()
bot_instance = None


# =========================================================
# BASE DE DATOS
# =========================================================

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_lock:
        conn = get_db()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    telegram_file_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    size INTEGER NOT NULL DEFAULT 0,
                    mime TEXT,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    disk_name TEXT NOT NULL,
                    UNIQUE(user_id, telegram_file_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_user
                ON files(user_id)
            """)
            conn.commit()
        finally:
            conn.close()


init_db()


# =========================================================
# UTILIDADES
# =========================================================

def safe_filename(name):
    name = os.path.basename(str(name or "archivo_sin_nombre"))
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(" .")
    return (name or "archivo_sin_nombre")[:180]


def category_for(content_type):
    mapping = {
        "photo": "photos",
        "video": "videos",
        "document": "documents",
        "audio": "audios",
        "voice": "audios",
        "video_note": "videos",
        "animation": "videos"
    }
    return mapping.get(content_type, "documents")


def get_user_usage(user_id):
    with db_lock:
        conn = get_db()
        try:
            row = conn.execute("""
                SELECT COALESCE(SUM(size), 0) AS total
                FROM files
                WHERE user_id = ?
            """, (str(user_id),)).fetchone()
            return int(row["total"])
        finally:
            conn.close()


def format_file(row):
    size_bytes = int(row["size"] or 0)
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "size": round(size_bytes / (1024 * 1024), 3),
        "size_bytes": size_bytes,
        "mime": row["mime"] or "application/octet-stream",
        "date": row["date"],
        "category": row["category"]
    }


# =========================================================
# PÁGINA WEB
# =========================================================

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ArchiveBot Pro"
    })


# =========================================================
# API DE ARCHIVOS
# =========================================================

@app.route("/api/files", methods=["GET"])
def get_files():
    user_id = request.args.get("user_id", "").strip()

    if not user_id or user_id == "default_user":
        return jsonify({
            "error": "Abre la aplicación desde Telegram."
        }), 400

    with db_lock:
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT *
                FROM files
                WHERE user_id = ?
                ORDER BY id DESC
            """, (user_id,)).fetchall()
        finally:
            conn.close()

    result = {
        "photos": [],
        "videos": [],
        "documents": [],
        "audios": []
    }

    for row in rows:
        item = format_file(row)
        category = item["category"]

        if category in result:
            result[category].append(item)

    return jsonify(result)


@app.route("/api/usage", methods=["GET"])
def get_usage():
    user_id = request.args.get("user_id", "").strip()

    if not user_id or user_id == "default_user":
        return jsonify({"error": "Usuario no identificado"}), 400

    used = get_user_usage(user_id)

    return jsonify({
        "used_bytes": used,
        "limit_bytes": USER_LIMIT,
        "used_mb": round(used / (1024 * 1024), 2),
        "limit_mb": 500,
        "remaining_mb": round(
            max(0, USER_LIMIT - used) / (1024 * 1024), 2
        )
    })


def get_owned_file(user_id, file_id):
    with db_lock:
        conn = get_db()
        try:
            return conn.execute("""
                SELECT *
                FROM files
                WHERE id = ? AND user_id = ?
            """, (file_id, str(user_id))).fetchone()
        finally:
            conn.close()


@app.route("/api/download/<int:file_id>", methods=["GET"])
def download_file(file_id):
    user_id = request.args.get("user_id", "").strip()

    if not user_id or user_id == "default_user":
        return jsonify({"error": "Usuario no identificado"}), 400

    row = get_owned_file(user_id, file_id)

    if not row:
        return jsonify({"error": "Archivo no encontrado"}), 404

    path = FILES_DIR / row["disk_name"]

    if not path.is_file():
        return jsonify({
            "error": "El archivo físico ya no está disponible. "
                     "El almacenamiento de Render puede ser temporal."
        }), 404

    return send_file(
        path,
        as_attachment=True,
        download_name=row["name"],
        mimetype=row["mime"] or "application/octet-stream"
    )


@app.route("/api/zip", methods=["POST"])
def download_zip():
    data = request.get_json(silent=True) or {}

    user_id = str(data.get("user_id", "")).strip()
    requested_ids = data.get("ids", [])

    if not user_id or user_id == "default_user":
        return jsonify({"error": "Usuario no identificado"}), 400

    if not isinstance(requested_ids, list) or not requested_ids:
        return jsonify({"error": "Selecciona al menos un archivo"}), 400

    if len(requested_ids) > 200:
        return jsonify({"error": "Máximo 200 archivos por ZIP"}), 400

    try:
        ids = list(dict.fromkeys(int(value) for value in requested_ids))
    except (ValueError, TypeError):
        return jsonify({"error": "Lista de archivos no válida"}), 400

    rows = []

    for file_id in ids:
        row = get_owned_file(user_id, file_id)

        if row is None:
            return jsonify({
                "error": "Uno de los archivos no pertenece a tu biblioteca."
            }), 403

        path = FILES_DIR / row["disk_name"]

        if not path.is_file():
            return jsonify({
                "error": f"El archivo {row['name']} ya no está disponible."
            }), 404

        rows.append((row, path))

    memory_file = io.BytesIO()

    try:
        with zipfile.ZipFile(
            memory_file,
            mode="w",
            compression=zipfile.ZIP_DEFLATED
        ) as archive:
            used_names = set()

            for row, path in rows:
                original_name = safe_filename(row["name"])
                archive_name = original_name
                counter = 1

                while archive_name in used_names:
                    stem = Path(original_name).stem
                    suffix = Path(original_name).suffix
                    archive_name = f"{stem}_{counter}{suffix}"
                    counter += 1

                used_names.add(archive_name)
                archive.write(path, arcname=archive_name)

        memory_file.seek(0)

        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name="ArchiveBot_Pro.zip"
        )

    except Exception:
        logger.exception("Error creando ZIP")
        return jsonify({"error": "No se pudo crear el ZIP"}), 500


# =========================================================
# RECEPCIÓN DE ARCHIVOS DE TELEGRAM
# =========================================================

def start_telegram_bot():
    global bot_instance

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

    if not token:
        logger.error("Falta TELEGRAM_BOT_TOKEN en Render.")
        return

    try:
        import telebot

        bot = telebot.TeleBot(token)
        bot_instance = bot

        @bot.message_handler(commands=["start", "help"])
        def welcome(message):
            if message.chat.type != "private":
                bot.reply_to(
                    message,
                    "Por favor, envíame los archivos por chat privado."
                )
                return

            bot.reply_to(
                message,
                "📦 ArchiveBot Pro está listo.\n\n"
                "Envíame fotos, vídeos, documentos o audios "
                "y aparecerán en tu biblioteca.\n\n"
                "Límite gratuito: 500 MB por usuario."
            )

        @bot.message_handler(content_types=[
            "photo", "document", "video", "audio",
            "voice", "video_note", "animation"
        ])
        def receive_file(message):
            if message.chat.type != "private":
                bot.reply_to(
                    message,
                    "Envía tus archivos en un chat privado conmigo."
                )
                return

            user_id = str(message.from_user.id)
            content_type = message.content_type

            try:
                file_obj = None
                file_name = None
                mime = "application/octet-stream"

                if content_type == "photo":
                    file_obj = message.photo[-1]
                    file_name = f"foto_{message.message_id}.jpg"
                    mime = "image/jpeg"

                elif content_type == "document":
                    file_obj = message.document
                    file_name = file_obj.file_name or "documento"
                    mime = file_obj.mime_type or mime

                elif content_type == "video":
                    file_obj = message.video
                    file_name = file_obj.file_name or f"video_{message.message_id}.mp4"
                    mime = file_obj.mime_type or "video/mp4"

                elif content_type == "audio":
                    file_obj = message.audio
                    file_name = file_obj.file_name or f"audio_{message.message_id}.mp3"
                    mime = file_obj.mime_type or "audio/mpeg"

                elif content_type == "voice":
                    file_obj = message.voice
                    file_name = f"audio_{message.message_id}.ogg"
                    mime = "audio/ogg"

                elif content_type == "video_note":
                    file_obj = message.video_note
                    file_name = f"video_note_{message.message_id}.mp4"
                    mime = "video/mp4"

                elif content_type == "animation":
                    file_obj = message.animation
                    file_name = file_obj.file_name or f"animacion_{message.message_id}.mp4"
                    mime = file_obj.mime_type or "video/mp4"

                if not file_obj:
                    bot.reply_to(message, "No pude identificar el archivo.")
                    return

                telegram_file_id = file_obj.file_id
                expected_size = int(getattr(file_obj, "file_size", 0) or 0)

                # Evitar duplicados en la misma biblioteca.
                with db_lock:
                    conn = get_db()
                    try:
                        existing = conn.execute("""
                            SELECT id FROM files
                            WHERE user_id = ? AND telegram_file_id = ?
                        """, (user_id, telegram_file_id)).fetchone()
                    finally:
                        conn.close()

                if existing:
                    bot.reply_to(message, "ℹ️ Este archivo ya está registrado.")
                    return

                used = get_user_usage(user_id)

                if expected_size and used + expected_size > USER_LIMIT:
                    bot.reply_to(
                        message,
                        "⛔ Has alcanzado el límite gratuito de 500 MB.\n"
                        "El archivo no se ha guardado."
                    )
                    return

                # Descargar el contenido real desde Telegram.
                file_info = bot.get_file(telegram_file_id)
                downloaded = bot.download_file(file_info.file_path)

                actual_size = len(downloaded)

                if used + actual_size > USER_LIMIT:
                    bot.reply_to(
                        message,
                        "⛔ Este archivo supera el espacio que te queda "
                        "en el plan gratuito de 500 MB."
                    )
                    return

                disk_name = f"{user_id}_{time.time_ns()}_{safe_filename(file_name)}"
                disk_path = FILES_DIR / disk_name

                with open(disk_path, "wb") as output:
                    output.write(downloaded)

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                category = category_for(content_type)

                try:
                    with db_lock:
                        conn = get_db()
                        try:
                            conn.execute("""
                                INSERT INTO files (
                                    user_id, telegram_file_id, name,
                                    size, mime, category, date, disk_name
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                user_id,
                                telegram_file_id,
                                safe_filename(file_name),
                                actual_size,
                                mime,
                                category,
                                now_str,
                                disk_name
                            ))
                            conn.commit()
                        finally:
                            conn.close()

                except Exception:
                    # Si el registro falla, no dejar un archivo huérfano.
                    try:
                        disk_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise

                used_mb = round((used + actual_size) / (1024 * 1024), 2)

                bot.reply_to(
                    message,
                    f"✅ Archivo archivado correctamente.\n\n"
                    f"📄 {safe_filename(file_name)}\n"
                    f"💾 {round(actual_size / (1024 * 1024), 2)} MB\n"
                    f"📊 Uso total: {used_mb} / 500 MB\n\n"
                    f"Abre ArchiveBot Pro para verlo en tu biblioteca."
                )

            except Exception:
                logger.exception("Error guardando archivo de Telegram")
                bot.reply_to(
                    message,
                    "❌ No se pudo guardar el archivo. "
                    "Comprueba su tamaño e inténtalo de nuevo."
                )

        logger.info("Iniciando bot de Telegram.")

        # Eliminar webhook anterior antes de utilizar polling.
        bot.remove_webhook()
        bot.infinity_polling(
            timeout=20,
            long_polling_timeout=10,
            skip_pending=True
        )

    except Exception:
        logger.exception("No se pudo iniciar el bot de Telegram.")


# =========================================================
# INICIO
# =========================================================

def launch_bot_once():
    if bot_lock.acquire(blocking=False):
        def runner():
            try:
                start_telegram_bot()
            finally:
                bot_lock.release()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()


@app.before_request
def ensure_bot_started():
    # Evita que el bot se inicie una vez por cada petición.
    launch_bot_once()


if __name__ == "__main__":
    launch_bot_once()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
