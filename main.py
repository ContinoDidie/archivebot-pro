import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Configurar logs para ver el estado del bot en la consola
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SERVIDOR HTTP FALSO PARA RENDER (Evita el error de puerto) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Archivebot Pro is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# Inicia el servidor web en un hilo paralelo para no bloquear el bot
threading.Thread(target=run_dummy_server, daemon=True).start()
# -----------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start que da la bienvenida al usuario."""
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola, {user.first_name}! 👋\n\n"
        "Bienvenido a **ArchiveBot Pro**. Tu herramienta definitiva para respaldar chats y contenido de Telegram.\n\n"
        "👇 Presiona el botón del menú abajo para abrir el panel de control y comenzar."
    )

def main():
    # Token de tu bot de Telegram (puedes ingresarlo directamente aquí o usar variables de entorno)
    # Reemplaza 'TU_TOKEN_AQUI' con el token que te dio BotFather
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TU_TOKEN_AQUI")

    if TOKEN == "TU_TOKEN_AQUI":
        logger.warning("⚠️ ADVERTENCIA: No has configurado el Token del bot. Recuerda agregarlo.")

    # Construir la aplicación del bot
    application = ApplicationBuilder().token(TOKEN).build()

    # Registrar el comando /start
    application.add_handler(CommandHandler("start", start))

    # Iniciar el bot en modo Polling
    logger.info("🤖 ArchiveBot Pro iniciado correctamente y escuchando...")
    application.run_polling()

if __name__ == '__main__':
    main()
