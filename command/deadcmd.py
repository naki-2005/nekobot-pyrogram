async def handle_up(client, message):
    if message.reply_to_message:
        await message.reply("Descargando...")
        file_path = await client.download_media(message.reply_to_message.document.file_id)
        await message.reply("Subiendo a la nube...")
        link = upload_token(file_path, os.getenv("NUBETOKEN"), os.getenv("NUBELINK"))
        await message.reply("Enlace:\n" + str(link).replace("/webservice", ""))
        os.remove(file_path)
