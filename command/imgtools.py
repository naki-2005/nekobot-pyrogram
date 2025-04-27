import os
import requests
import re
from pyrogram import Client
from PIL import Image

IMG_CHEST_API_KEY = os.getenv("IMGAPI")

async def create_imgchest_post(client, message):
    file = message.reply_to_message.document or message.reply_to_message.photo or message.reply_to_message.video
    photo_file = await client.download_media(file)
    if not photo_file:
        await client.send_message(
            chat_id=message.from_user.id,
            text="No se pudo descargar el archivo. Asegúrate de que sea un archivo válido."
        )
        return

    # Verificar el tipo de archivo y su tamaño
    file_size = os.path.getsize(photo_file)
    file_extension = photo_file.rsplit(".", 1)[-1].lower()
    
    if file_extension == "gif" or file_extension in ["mp4", "mkv", "webm"]:
        if file_size > 30 * 1024 * 1024:  # 30 MB
            await client.send_message(
                chat_id=message.from_user.id,
                text="El archivo excede el límite de 30 MB permitido por Imgchest."
            )
            os.remove(photo_file)
            return
    elif file_extension in ["jpg", "jpeg", "png"]:
        png_file = photo_file.rsplit(".", 1)[0] + ".png"
        try:
            with Image.open(photo_file) as img:
                img.convert("RGBA").save(png_file, "PNG")
            photo_file = png_file
        except Exception as e:
            await client.send_message(
                chat_id=message.from_user.id,
                text=f"No se pudo convertir la imagen a PNG. Error: {str(e)}"
            )
            os.remove(photo_file)
            return
    else:
        await client.send_message(
            chat_id=message.from_user.id,
            text="El tipo de archivo no es compatible."
        )
        os.remove(photo_file)
        return

    # Subir el archivo a Imgchest
    with open(photo_file, "rb") as file:
        response = requests.post(
            "https://api.imgchest.com/v1/post",
            headers={"Authorization": f"Bearer {IMG_CHEST_API_KEY}"},
            files={"images[]": file},
            data={
                "title": "Mi Post en Imgchest",
                "privacy": "hidden",
                "nsfw": "true"
            }
        )

    # Manejo de respuestas
    if response.status_code == 201:
        imgchest_data = response.json()
        post_link = f"https://imgchest.com/p/{imgchest_data['data']['id']}"
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"Tu post ha sido creado exitosamente:\n\n📁 Enlace del Álbum: {post_link}"
        )
    elif response.status_code == 200:
        try:
            match = re.search(r'https:\\/\\/cdn\.imgchest\.com\\/files\\/[\w]+\.(jpg|jpeg|png|gif|mp4|webm)', response.text)
            if match:
                image_link = match.group(0).replace("\\/", "/")
                await client.send_message(
                    chat_id=message.from_user.id,
                    text=f"Link: {image_link}"
                )
            else:
                await client.send_message(
                    chat_id=message.from_user.id,
                    text="No se encontró un enlace en la respuesta del servidor."
                )
        except Exception as e:
            await client.send_message(
                chat_id=message.from_user.id,
                text=f"Ocurrió un error al procesar la respuesta:\n{str(e)}"
            )
    else:
        error_details = response.text
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"No se pudo crear el post. Detalles del error:\nEstado: {response.status_code}\nRespuesta: {error_details}"
        )

    # Limpieza
    os.remove(photo_file)
    if "png_file" in locals():
        os.remove(png_file)
