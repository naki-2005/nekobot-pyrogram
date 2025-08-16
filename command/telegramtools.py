async def get_file_id(client, message):
    if message.reply_to_message:
        if message.reply_to_message.sticker:
            file_type = "Sticker"
            file_id = message.reply_to_message.sticker.file_id
        elif message.reply_to_message.photo:
            file_type = "Foto"
            file_id = message.reply_to_message.photo[-1].file_id
        elif message.reply_to_message.document:
            file_type = "Documento"
            file_id = message.reply_to_message.document.file_id
        elif message.reply_to_message.audio:
            file_type = "Audio"
            file_id = message.reply_to_message.audio.file_id
        elif message.reply_to_message.video:
            file_type = "Video"
            file_id = message.reply_to_message.video.file_id
        elif message.reply_to_message.voice:
            file_type = "Nota de Voz"
            file_id = message.reply_to_message.voice.file_id
        elif message.reply_to_message.animation:
            file_type = "GIF"
            file_id = message.reply_to_message.animation.file_id
        else:
            await client.send_message(
                chat_id=message.chat.id,
                text="El mensaje al que respondiste no contiene contenido válido."
            )
            return

        await client.send_message(
            chat_id=message.chat.id,
            text=f"ID del {file_type}:\n\n`{file_id}`"
        )
    else:
        await client.send_message(
            chat_id=message.chat.id,
            text="Por favor, responde a un mensaje para usar esta función."
        )

async def send_file_by_id(client, message):
    try:
        args = message.text.split(' ', 2)
        if len(args) < 3:
            await client.send_message(
                chat_id=message.chat.id,
                text="Por favor, usa el formato: /sendfile tipo_de_archivo file_id"
            )
            return
        
        file_type = args[1].lower()
        file_id = args[2]

        if file_type == "sticker":
            await client.send_sticker(chat_id=message.chat.id, sticker=file_id)
        elif file_type == "foto":
            await client.send_photo(chat_id=message.chat.id, photo=file_id)
        elif file_type == "documento":
            await client.send_document(chat_id=message.chat.id, document=file_id)
        elif file_type == "audio":
            await client.send_audio(chat_id=message.chat.id, audio=file_id)
        elif file_type == "video":
            await client.send_video(chat_id=message.chat.id, video=file_id)
        elif file_type == "nota_de_voz":
            await client.send_voice(chat_id=message.chat.id, voice=file_id)
        elif file_type == "gif":
            await client.send_animation(chat_id=message.chat.id, animation=file_id)
        else:
            await client.send_message(
                chat_id=message.chat.id,
                text="Tipo de archivo no reconocido. Los tipos válidos son: sticker, foto, documento, audio, video, nota_de_voz, gif."
            )
    except Exception as e:
        await client.send_message(
            chat_id=message.chat.id,
            text=f"Error al enviar el archivo: {e}"
        )
