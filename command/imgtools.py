import os
import shutil
import random
import string
import py7zr
import requests
import re
import sqlite3
from pyrogram import Client, filters
from PIL import Image

def get_imgchest_api_key():
    """Obtiene la API key de ImgChest desde la tabla de parámetros"""
    try:
        ruta_db = os.path.join(os.getcwd(), 'bot_cmd.db')
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parametros (
                nombre TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')
        
        cursor.execute('SELECT valor FROM parametros WHERE nombre = ?', ('imgapi',))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            return resultado[0]
        return None
        
    except Exception as e:
        print(f"Error al obtener API key de imgchest: {e}")
        return None

async def create_imgchest_post(client, message):
    IMG_CHEST_API_KEY = get_imgchest_api_key()
    
    if not IMG_CHEST_API_KEY:
        await client.send_message(
            chat_id=message.from_user.id,
            text="❌ No se ha configurado la API key de ImgChest. Usa el comando `/config imgapi <tu_api_key>` para configurarla."
        )
        return

    if not message.reply_to_message or not (message.reply_to_message.document or message.reply_to_message.photo):
        await client.send_message(
            chat_id=message.from_user.id,
            text="❌ Debes responder a una imagen o archivo para subirlo a ImgChest."
        )
        return

    file = message.reply_to_message.document or message.reply_to_message.photo
    photo_file = await client.download_media(file)
    
    if not photo_file:
        await client.send_message(
            chat_id=message.from_user.id,
            text="No se pudo descargar el archivo. Asegúrate de que sea un archivo válido."
        )
        return
        
    png_file = photo_file.rsplit(".", 1)[0] + ".png"
    try:
        with Image.open(photo_file) as img:
            img.convert("RGBA").save(png_file, "PNG")
    except Exception as e:
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"No se pudo convertir la imagen a PNG. Error: {str(e)}"
        )
        os.remove(photo_file)
        return

    try:
        with open(png_file, "rb") as file:
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
                text=f"✅ Tu post ha sido creado exitosamente:\n\n📁 Enlace del Álbum: {post_link}"
            )
        elif response.status_code == 200:
            try:
                match = re.search(r'https:\\/\\/cdn\.imgchest\.com\\/files\\/[\w]+\.(jpg|jpeg|png|gif)', response.text)
                if match:
                    image_link = match.group(0).replace("\\/", "/")
                    await client.send_message(
                        chat_id=message.from_user.id,
                        text=f"{image_link}"
                    )
                else:
                    await client.send_message(
                        chat_id=message.from_user.id,
                        text="⚠️ No se encontró un enlace de imagen en la respuesta del servidor."
                    )
            except Exception as e:
                await client.send_message(
                    chat_id=message.from_user.id,
                    text=f"❌ Ocurrió un error al procesar la respuesta:\n{str(e)}"
                )
        else:
            error_details = response.text
            await client.send_message(
                chat_id=message.from_user.id,
                text=f"❌ No se pudo crear el post. Detalles del error:\nEstado: {response.status_code}\nRespuesta: {error_details}"
            )

    except Exception as e:
        await client.send_message(
            chat_id=message.from_user.id,
            text=f"❌ Error al conectar con ImgChest: {str(e)}"
        )

    finally:
        if os.path.exists(photo_file):
            os.remove(photo_file)
        if os.path.exists(png_file):
            os.remove(png_file)
