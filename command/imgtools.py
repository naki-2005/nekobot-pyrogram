import os
import requests
from pyrogram import Client
from PIL import Image

IMG_CHEST_API_KEY = os.getenv("IMGAPI")

def safe_remove(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

async def create_imgchest_post(client, message):
    file = message.reply_to_message.document or message.reply_to_message.photo or message.reply_to_message.video
    photo_file = await client.download_media(file)
    if not photo_file:
        await client.send_message(
            chat_id=message.from_user.id,
            text="No se pudo descargar el archivo. Asegúrate de que sea un archivo válido."
        )
        return

    file_size = os.path.getsize(photo_file)
    file_extension = photo_file.rsplit(".", 1)[-1].lower()
    allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp", "mp4"]

    if file_extension not in allowed_extensions:
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"El tipo de archivo {file_extension} no es compatible con Imgchest."
        )
        safe_remove(photo_file)
        return

    if file_extension in ["mp4"] and file_size > 30 * 1024 * 1024:  # 30 MB
        await client.send_message(
            chat_id=message.from_user.id,
            text="El archivo excede el límite de 30 MB permitido por Imgchest."
        )
        safe_remove(photo_file)
        return

    if file_extension in ["jpg", "jpeg", "png"] and file_extension != "png":
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
            safe_remove(photo_file)
            return

    # Subir a Imgchest
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

    if response.status_code == 201:
        imgchest_data = response.json()
        post_link = f"https://imgchest.com/p/{imgchest_data['data']['id']}"
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"Tu post ha sido creado exitosamente:\n\n📁 Enlace del Álbum: {post_link}"
        )
    else:
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"No se pudo crear el post. Detalles del error:\nEstado: {response.status_code}\nRespuesta: {response.text}"
        )

    safe_remove(photo_file)
    if "png_file" in locals():
        safe_remove(png_file)
