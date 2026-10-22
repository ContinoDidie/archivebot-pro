# --- HILO DEL BOT DE TELEGRAM ---
def run_telegram_bot():
    # Esperar un momento prudente para que el puerto web abra primero
    time.sleep(5)
    logger.info("Iniciando bucle de Telegram...")
    
    import telebot
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not TOKEN:
        logger.error("¡Falta el TELEGRAM_BOT_TOKEN en las variables de entorno!")
        return
    
    while True:
        try:
            bot = telebot.TeleBot(TOKEN)
            
            # Limpiar cualquier conexión previa colgada
            try:
                bot.remove_webhook()
            except Exception:
                pass
            
            @bot.message_handler(commands=['start', 'help'])
            def send_welcome(message):
                bot.reply_to(message, "¡Hola! Envíame fotos, videos, documentos o audios y aparecerán sincronizados en tu biblioteca web.")

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
                        file_name = f"foto_{message.photo[-1].file_unique_id}.jpg"
                        file_size_mb = round(message.photo[-1].file_size / (1024 * 1024), 2) if hasattr(message.photo[-1], 'file_size') else 1.5
                        file_mime = "image/jpeg"
                    
                    elif message.content_type == 'document':
                        category = "documents"
                        file_name = message.document.file_name or "documento.pdf"
                        file_size_mb = round(message.document.file_size / (1024 * 1024), 2)
                        file_mime = message.document.mime_type or "application/octet-stream"

                    elif message.content_type == 'video':
                        category = "videos"
                        file_name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
                        file_size_mb = round(message.video.file_size / (1024 * 1024), 2)
                        file_mime = message.video.mime_type or "video/mp4"

                    elif message.content_type in ['audio', 'voice']:
                        category = "audios"
                        audio_obj = message.audio if message.content_type == 'audio' else message.voice
                        file_name = getattr(audio_obj, 'file_name', f"audio_{audio_obj.file_unique_id}.ogg")
                        file_size_mb = round(audio_obj.file_size / (1024 * 1024), 2)
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
                    
                    if not any(f['name'] == file_name for f in user_files_database[user_id][category]):
                        user_files_database[user_id][category].append(new_entry)

                    bot.reply_to(message, f"✅ Archivo guardado en [{category}]: {file_name} ({file_size_mb} MB)")
                    logger.info(f"Archivo guardado exitosamente para el usuario {user_id} en {category}: {file_name}")

                except Exception as e:
                    logger.error(f"Error procesando archivo de Telegram: {e}")
                    bot.reply_to(message, "Hubo un error al procesar tu archivo.")

            logger.info("Bot de Telegram conectado y escuchando mensajes...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
            
        except Exception as e:
            logger.error(f"Conflicto o desconexión en el bot ({e}). Reintentando en 10 segundos...")
            time.sleep(10)
