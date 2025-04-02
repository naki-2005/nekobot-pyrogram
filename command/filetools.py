import os
import shutil
import random
import string
import py7zr
import time
from pyrogram import Client, filters

user_comp = {} 
compression_size = 10  

def compressfile(file_path, part_size):
    parts = []
    part_size *= 1024 * 1024  # Convertir el tamaño de parte a bytes
    archive_path = f"{file_path}.7z"

    # Crear el archivo comprimido
    with py7zr.SevenZipFile(archive_path, 'w') as archive:
        archive.write(file_path, os.path.basename(file_path))
        os.remove(file_path)  # Eliminar el archivo original

    # Comprobar el tamaño del archivo comprimido
    archive_size = os.path.getsize(archive_path)
    if archive_size < part_size:
        return [archive_path]  # Retornar el archivo comprimido

    # Dividir el archivo comprimido en partes si excede el tamaño de parte
    with open(archive_path, 'rb') as archive:
        part_num = 1
        while True:
            part_data = archive.read(part_size)
            if not part_data:
                break
            part_file = f"{archive_path}.{part_num:03d}"
            with open(part_file, 'wb') as part:
                part.write(part_data)
            parts.append(part_file)
            part_num += 1

    os.remove(archive_path)  # Eliminar el archivo comprimido original
    return parts




async def handle_compress(client, message, username):
    reply_message = message.reply_to_message

    # Crear la carpeta 'server' si no existe
    if not os.path.exists('server'):
        os.mkdir('server')

    if reply_message and reply_message.caption and reply_message.caption.startswith("Look Here") and reply_message.from_user.is_self:
        await message.reply("No puedes comprimir este contenido debido a restricciones.", protect_content=True)
        return

    try:
        os.system("rm -rf ./server/*")
        progress_msg = await message.reply("Descargando el archivo para comprimirlo...")

        def get_file_name(message):
            if message.reply_to_message.document:
                return os.path.basename(message.reply_to_message.document.file_name)[:50]
            elif message.reply_to_message.photo:
                return ''.join(random.choices(string.ascii_letters + string.digits, k=20)) + ".jpg"
            elif message.reply_to_message.audio:
                return ''.join(random.choices(string.ascii_letters + string.digits, k=20)) + ".mp3"
            elif message.reply_to_message.video:
                return ''.join(random.choices(string.ascii_letters + string.digits, k=20)) + ".mp4"
            elif message.reply_to_message.sticker:
                return ''.join(random.choices(string.ascii_letters + string.digits, k=20)) + ".webp"
            else:
                return ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        
        file_name = get_file_name(message)
        file_path = await client.download_media(
            message.reply_to_message,
            file_name=file_name
        )
        await client.edit_message_text(chat_id=message.chat.id, message_id=progress_msg.id, text="Comprimiendo el archivo...")
        
        sizd = user_comp.get(username, 10)
        parts = compressfile(file_path, sizd)
        
        # Añadir la cantidad de partes al mensaje
        num_parts = len(parts)
        await client.edit_message_text(
            chat_id=message.chat.id,
            message_id=progress_msg.id,
            text=f"Se ha comprimido el archivo en {num_parts} partes, ahora se enviarán las partes"
        )

        for part in parts:
            try:
                await client.send_document(message.chat.id, part)
                os.remove(part)
            except Exception as e:
                print(f"Error al enviar la parte {part}: {e}")
                await message.reply(f"Error al enviar la parte {part}: {e}")
                os.remove(part)
        
        # Eliminar el mensaje de progreso
        await client.delete_messages(chat_id=message.chat.id, message_ids=[progress_msg.id])

        # Enviar el mensaje final de "Esas son todas las partes"
        await message.reply("Esas son todas las partes")
        

        # Eliminar la carpeta 'server' y recrearla
        shutil.rmtree('server')
        os.mkdir('server')
    
    except Exception as e:
        await message.reply(f'Error: {str(e)}')
    
        
async def rename(client, message):
    reply_message = message.reply_to_message

    # Verificar si el caption empieza con "Look Here" y el remitente es el bot
    if reply_message and reply_message.caption and reply_message.caption.startswith("Look Here") and reply_message.from_user.is_self:
        await message.reply("No puedes renombrar este contenido debido a restricciones.", protect_content=True)
        return

    if reply_message and reply_message.media:
        try:
            await message.reply("Descargando el archivo para renombrarlo...")
            new_name = message.text.split(' ', 1)[1]
            file_path = await client.download_media(reply_message)
            new_file_path = os.path.join(os.path.dirname(file_path), new_name)
            os.rename(file_path, new_file_path)
            await message.reply("Subiendo el archivo con nuevo nombre...")
            await client.send_document(message.chat.id, new_file_path)
            os.remove(new_file_path)
        except Exception as e:
            await message.reply(f'Error: {str(e)}')
    else:
        await message.reply('Ejecute el comando respondiendo a un archivo')

async def set_size(client, message):
    try:
        valor = int(message.text.split(" ")[1])  # Intentar convertir el valor a entero
        if valor < 1:  # Validar que el tamaño sea mayor a 0 MB
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAIF02fm3-XonvGhnnaVYCwO-y71UhThAAJuOgAC4KOCB77pR2Nyg3apHgQ"
            )
            time.sleep(5)
            await message.reply("¿Qué haces pendejo? ¿Como piensas comprimir en negativo?.")
            return
        username = message.from_user.username
        user_comp[username] = valor  # Registrar el tamaño para el usuario
        await message.reply(f"Tamaño de archivos {valor}MB registrado para el usuario @{username}.")
    except IndexError:
        await message.reply("Por favor, proporciona el tamaño del archivo después del comando.")
    except ValueError:
        await message.reply("El tamaño proporcionado no es un número válido. Intenta nuevamente.")
    except Exception as e:  # Capturar cualquier otro error inesperado
        await message.reply(f"Ha ocurrido un error inesperado: {str(e)}")
        logging.error(f"Error inesperado en set_size: {str(e)}")
