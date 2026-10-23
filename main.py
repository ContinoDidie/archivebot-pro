import os
import io
import re
import json
import time
import sqlite3
import logging
import threading
import zipfile
import urllib.request
import urllib.parse

from datetime import datetime, timezone
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

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "10000"))

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    "archivebot.db"
)

MAX_FILES_PER_ZIP = 50
TELEGRAM_TIMEOUT = 60

app = Flask(__name__, static_folder=".", static_url_path="")

CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    allow_headers=["Content-Type", "X-Telegram-Init-Data"],
    methods=["GET", "POST", "OPTIONS"]
)


# =========================================================
# BASE DE DATOS
# =========================================================

def get_db():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
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
                size REAL DEFAULT 0,
                mime_type TEXT DEFAULT '',
                category TEXT DEFAULT 'documents',
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_user
            ON files(user_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_unique
            ON files(user_id, file_unique_id)
        """)

        connection.commit()
        logger.info("Base de datos inicializada correctamente.")

    finally:
        connection.close()


# =========================================================
# GUARDAR ARCHIVOS
# =========================================================

def save_file(
    user_id,
    file_id,
    file_unique_id,
    name,
    size,
    mime_type,
    category
):
    if not file_id:
        logger.error("No se puede guardar un archivo sin file_id.")
        return False

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
                LIMIT 1
                """,
                (user_id, file_unique_id)
            ).fetchone()

        size_mb = round(size / (1024 * 1024), 2) if size else 0

        created_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

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

            logger.info("Archivo actualizado: %s", name)

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
                    file_unique_id or None,
                    name,
                    size_mb,
                    mime_type or "",
                    category,
                    created_at
                )
            )

            logger.info("Archivo registrado: %s [%s]", name, category)

        connection.commit()
        return True

    except Exception:
        logger.exception("Error al guardar el archivo en SQLite.")
        return False

    finally:
        connection.close()


# =========================================================
# COMUNICACIÓN CON TELEGRAM
# =========================================================

def telegram_api(method, params=None):
    if not BOT_TOKEN:
        raise RuntimeError(
            "Falta configurar TELEGRAM_BOT_TOKEN en Render."
        )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    encoded_params = urllib.parse.urlencode(params or {}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=encoded_params if encoded_params else None,
        method="POST" if encoded_params else "GET"
    )

    with urllib.request.urlopen(
        req,
        timeout=TELEGRAM_TIMEOUT
    ) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(
            result.get("description", "Error desconocido de Telegram.")
        )

    return result["result"]


def download_telegram_file(file_id):
    """
    Devuelve los bytes del archivo descargado desde Telegram.
    """

    file_info = telegram_api("getFile", {"file_id": file_id})
    file_path = file_info.get("file_path")

    if not file_path:
        raise RuntimeError("Telegram no devolvió la ruta del archivo.")

    encoded_path = urllib.parse.quote(file_path, safe="/")

    download_url = (
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{encoded_path}"
    )

    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "ArchiveBot-Pro/1.0"}
    )

    with urllib.request.urlopen(
        req,
        timeout=TELEGRAM_TIMEOUT
    ) as response:
        return response.read()


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
        "service": "ArchiveBot Pro"
    }), 200


# =========================================================
# LISTAR ARCHIVOS
# =========================================================

@app.route("/api/files", methods=["GET"])
def get_files():
    connection = get_db()

    try:
        rows = connection.execute(
            "SELECT * FROM files ORDER BY id DESC"
        ).fetchall()

        library = {
            "photos": [],
            "videos": [],
            "documents": [],
            "audios": []
        }

        seen = {
            "photos": set(),
            "videos": set(),
            "documents": set(),
            "audios": set()
        }

        for row in rows:
            category = row["category"]

            if category not in library:
                category = "documents"

            file_name = row["name"]

            # Evita mostrar repetidamente un mismo nombre
            # dentro de la misma categoría.
            if file_name in seen[category]:
                continue

            seen[category].add(file_name)

            library[category].append({
                "id": str(row["id"]),
                "name": file_name,
                "size": row["size"] or 0,
                "mime": row["mime_type"] or "",
                "date": row["created_at"],
                "category": category
            })

        return jsonify(library), 200

    except Exception:
        logger.exception("Error en /api/files")

        return jsonify({
            "error": "No se pudo cargar la biblioteca."
        }), 500

    finally:
        connection.close()


# =========================================================
# ABRIR O DESCARGAR UN ARCHIVO
# =========================================================

@app.route("/api/file/<int:file_id>", methods=["GET"])
def get_single_file(file_id):
    connection = get_db()

    try:
        row = connection.execute(
            "SELECT * FROM files WHERE id = ?",
            (file_id,)
        ).fetchone()

        if not row:
            return jsonify({
                "error": "Archivo no encontrado en la biblioteca."
            }), 404

        tg_file_id = row["file_id"]
        file_name = row["name"]
        mime_type = row["mime_type"] or "application/octet-stream"

    finally:
        connection.close()

    try:
        file_bytes = download_telegram_file(tg_file_id)

        is_download = request.args.get("download") == "1"

        return send_file(
            io.BytesIO(file_bytes),
            mimetype=mime_type,
            as_attachment=is_download,
            download_name=file_name,
            max_age=0
        )

    except Exception:
        logger.exception(
            "Error al recuperar el archivo ID %s desde Telegram.",
            file_id
        )

        return jsonify({
            "error": (
                "No se pudo recuperar el archivo desde Telegram. "
                "Comprueba el token y que el archivo siga disponible."
            )
        }), 502


# =========================================================
# CREAR ZIP
# =========================================================

@app.route("/api/zip", methods=["POST"])
def create_zip():
    connection = None

    try:
        data = request.get_json(silent=True) or {}
        file_ids = data.get("ids", [])

        if not isinstance(file_ids, list) or not file_ids:
            return jsonify({
                "error": "Selecciona al menos un archivo."
            }), 400

        if len(file_ids) > MAX_FILES_PER_ZIP:
            return jsonify({
                "error": (
                    f"El límite es de {MAX_FILES_PER_ZIP} archivos "
                    "por ZIP."
                )
            }), 400

        # Normaliza IDs recibidos desde el frontend.
        normalized_ids = []

        for value in file_ids:
            try:
                normalized_id = int(value)

                if normalized_id > 0 and normalized_id not in normalized_ids:
                    normalized_ids.append(normalized_id)

            except (ValueError, TypeError):
                continue

        if not normalized_ids:
            return jsonify({
                "error": "Los identificadores de los archivos no son válidos."
            }), 400

        if len(normalized_ids) > MAX_FILES_PER_ZIP:
            return jsonify({
                "error": (
                    f"El límite es de {MAX_FILES_PER_ZIP} archivos "
                    "por ZIP."
                )
            }), 400

        connection = get_db()

        placeholders = ",".join("?" for _ in normalized_ids)

        rows = connection.execute(
            f"""
            SELECT *
            FROM files
            WHERE id IN ({placeholders})
            ORDER BY id DESC
            """,
            normalized_ids
        ).fetchall()

        connection.close()
        connection = None

        if not rows:
            return jsonify({
                "error": "No se encontraron los archivos seleccionados."
            }), 404

        memory_zip = io.BytesIO()
        failed_files = []
        added_files = 0
        used_names = set()

        with zipfile.ZipFile(
            memory_zip,
            mode="w",
            compression=zipfile.ZIP_DEFLATED
        ) as zip_file:

            for row in rows:
                original_name = row["name"] or f"archivo_{row['id']}"

                # Evita rutas peligrosas dentro del ZIP y nombres vacíos.
                safe_name = os.path.basename(
                    original_name.replace("\\", "/")
                ).strip()

                if not safe_name:
                    safe_name = f"archivo_{row['id']}"

                # Evita duplicados de nombre dentro del ZIP.
                base, extension = os.path.splitext(safe_name)
                candidate = safe_name
                counter = 1

                while candidate.lower() in used_names:
                    candidate = f"{base}_{counter}{extension}"
                    counter += 1

                used_names.add(candidate.lower())

                try:
                    file_bytes = download_telegram_file(row["file_id"])

                    if not file_bytes:
                        raise RuntimeError("Telegram devolvió un archivo vacío.")

                    zip_file.writestr(candidate, file_bytes)
                    added_files += 1

                    logger.info(
                        "Archivo añadido al ZIP: %s",
                        candidate
                    )

                except Exception as error:
                    logger.exception(
                        "Error al añadir %s al ZIP.",
                        original_name
                    )

                    failed_files.append({
                        "name": original_name,
                        "error": str(error)[:200]
                    })

        if added_files == 0:
            return jsonify({
                "error": (
                    "No se pudo descargar ninguno de los archivos. "
                    "No se generó un ZIP vacío. Comprueba los registros "
                    "del servicio en Render."
                ),
                "failed_files": failed_files
            }), 502

        memory_zip.seek(0)

        response = send_file(
            memory_zip,
            mimetype="application/zip",
            as_attachment=True,
            download_name="ArchiveBot_Pro.zip",
            max_age=0
        )

        response.headers["X-ArchiveBot-Files-Added"] = str(added_files)
        response.headers["X-ArchiveBot-Files-Failed"] = str(len(failed_files))

        return response

    except Exception:
        logger.exception("Error creando el ZIP.")

        return jsonify({
            "error": "Error interno al generar el archivo ZIP."
        }), 500

    finally:
        if connection is not None:
            connection.close()


# =========================================================
# PROCESAMIENTO DE ARCHIVOS DE TELEGRAM
# =========================================================

def process_telegram_file(message, bot):
    try:
        if not message.from_user:
            logger.warning("Mensaje sin usuario; se ignora.")
            return

        user_id = message.from_user.id
        content_type = message.content_type

        file_id = ""
        file_unique_id = ""
        file_name = "archivo_sin_nombre"
        size_bytes = 0
        file_mime = "application/octet-stream"
        category = "documents"

        if content_type == "photo" and message.photo:
            category = "photos"

            photo = message.photo[-1]
            file_id = photo.file_id
            file_unique_id = getattr(photo, "file_unique_id", "")

            suffix = (file_unique_id or str(time.time_ns()))[:8]
            file_name = f"foto_{suffix}.jpg"

            size_bytes = getattr(photo, "file_size", 0) or 0
            file_mime = "image/jpeg"

        elif content_type == "document" and message.document:
            category = "documents"

            doc = message.document
            file_id = doc.file_id
            file_unique_id = getattr(doc, "file_unique_id", "")
            file_name = getattr(doc, "file_name", None) or "documento"
            size_bytes = getattr(doc, "file_size", 0) or 0
            file_mime = getattr(
                doc,
                "mime_type",
                "application/octet-stream"
            ) or "application/octet-stream"

        elif content_type == "video" and message.video:
            category = "videos"

            video = message.video
            file_id = video.file_id
            file_unique_id = getattr(video, "file_unique_id", "")

            suffix = (file_unique_id or str(time.time_ns()))[:8]
            file_name = getattr(video, "file_name", None) or f"video_{suffix}.mp4"

            size_bytes = getattr(video, "file_size", 0) or 0
            file_mime = getattr(video, "mime_type", "video/mp4") or "video/mp4"

        elif content_type in ("audio", "voice"):
            category = "audios"

            audio_obj = (
                message.audio
                if content_type == "audio"
                else message.voice
            )

            if not audio_obj:
                raise RuntimeError("No se encontró el objeto de audio.")

            file_id = audio_obj.file_id
            file_unique_id = getattr(audio_obj, "file_unique_id", "")

            suffix = (file_unique_id or str(time.time_ns()))[:8]

            if content_type == "voice":
                file_name = f"audio_{suffix}.ogg"
                file_mime = "audio/ogg"
            else:
                file_name = getattr(
                    audio_obj,
                    "file_name",
                    None
                ) or f"audio_{suffix}.mp3"

                file_mime = getattr(
                    audio_obj,
                    "mime_type",
                    "audio/mpeg"
                ) or "audio/mpeg"

            size_bytes = getattr(audio_obj, "file_size", 0) or 0

        else:
            return

        if not file_id:
            raise RuntimeError("Telegram no proporcionó file_id.")

        saved = save_file(
            user_id,
            file_id,
            file_unique_id,
            file_name,
            size_bytes,
            file_mime,
            category
        )

        if saved:
            bot.reply_to(
                message,
                f"✅ Archivo guardado en {category}:\n{file_name}"
            )
        else:
            bot.reply_to(
                message,
                "❌ No se pudo guardar el archivo en la base de datos."
            )

    except Exception:
        logger.exception("Error procesando archivo recibido de Telegram.")

        try:
            bot.reply_to(
                message,
                "❌ Ocurrió un error al guardar el archivo. Inténtalo otra vez."
            )
        except Exception:
            pass


# =========================================================
# BOT DE TELEGRAM
# =========================================================

def run_telegram_bot():
    time.sleep(3)

    if not BOT_TOKEN:
        logger.error(
            "Falta TELEGRAM_BOT_TOKEN en las variables de entorno de Render."
        )
        return

    bot = telebot.TeleBot(BOT_TOKEN)

    try:
        bot.remove_webhook()
        logger.info("Webhook anterior eliminado.")
    except Exception:
        logger.exception("No se pudo eliminar el webhook anterior.")

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):
        try:
            bot.reply_to(
                message,
                (
                    "¡Bienvenido a ArchiveBot Pro! 📁\n\n"
                    "Envíame fotos, videos, documentos o audios "
                    "para registrarlos en tu biblioteca.\n\n"
                    "Después abre la Mini App para verlos."
                )
            )
        except Exception:
            logger.exception("Error enviando el mensaje de bienvenida.")

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
        process_telegram_file(message, bot)

    while True:
        try:
            logger.info("Bot de Telegram conectado y escuchando mensajes...")

            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=20,
                skip_pending=True
            )

        except Exception:
            logger.exception(
                "Desconexión del bot. Reintentando en 10 segundos."
            )
            time.sleep(10)


# =========================================================
# INICIO DE LA APLICACIÓN
# =========================================================

init_db()


if __name__ == "__main__":
    bot_thread = threading.Thread(
        target=run_telegram_bot,
        daemon=True
    )

    bot_thread.start()

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
