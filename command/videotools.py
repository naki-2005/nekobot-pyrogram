import asyncio
import os
import uuid
import re
import subprocess
import random
from command.video_processor import procesar_video
from data.vars import admin_users, vip_users, video_limit, video_settings
from data.stickers import sobre_mb
import time
from pyrogram import Client
from pyrogram.types import Message
from PIL import Image

max_tareas = int(os.getenv('MAX_TASKS', '1'))

tareas_en_ejecucion = {}
cola_de_tareas = []

import copy

async def update_video_settings(client, message, protect_content):
    user_id = message.from_user.id
    global video_settings
    
    if user_id not in video_settings:
        video_settings[user_id] = copy.deepcopy(video_settings.get('default', {}))

    try:
        command_params = message.text.split()[1:]

        if not command_params:
            configuracion_actual = "/calidad " + " ".join(f"{k}={v}" for k, v in video_settings[user_id].items())
            await message.reply_text(f"⚙️ Configuración actual:\n`{configuracion_actual}`", protect_content=protect_content)
            return

        params = {}
        for item in command_params:
            if "=" not in item or len(item.split("=")) != 2:
                raise ValueError(f"Formato inválido para el parámetro: '{item}'. Usa clave=valor.")
            key, value = item.split("=")
            params[key] = value

        for key, value in params.items():
            if key in video_settings[user_id]:
                if key == 'resolution' and not re.match(r'^\d+x\d+$', value):
                    raise ValueError("Resolución inválida. Usa el formato WIDTHxHEIGHT.")
                elif key == 'crf' and not value.isdigit():
                    raise ValueError("El parámetro 'crf' debe ser un número.")
                elif key == 'audio_bitrate' and not re.match(r'^\d+k$', value):
                    raise ValueError("Audio bitrate inválido. Usa un valor en kbps, como '80k'.")
                elif key == 'fps' and not value.isdigit():
                    raise ValueError("El parámetro 'fps' debe ser un número.")
                elif key == 'preset' and value not in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']:
                    raise ValueError("Preset inválido. Usa uno de los valores válidos.")
                elif key == 'codec' and value not in ['libx264', 'libx265', 'libvpx']:
                    raise ValueError("Codec inválido. Usa 'libx264', 'libx265' o 'libvpx'.")

                video_settings[user_id][key] = value

        configuracion_texto = "/calidad " + " ".join(f"{k}={v}" for k, v in video_settings[user_id].items())
        await message.reply_text(f"⚙️ Configuraciones de video actualizadas:\n`{configuracion_texto}`", protect_content=protect_content)

    except ValueError as ve:
        await message.reply_text(f"❌ Error de validación:\n{ve}", protect_content=protect_content)
    except Exception as e:
        await message.reply_text(f"❌ Error al procesar el comando:\n{e}", protect_content=protect_content)

async def cancelar_tarea(int_lvl, client, task_id, chat_id, message, protect_content):
    user_id_requesting = message.from_user.id

    global cola_de_tareas, tareas_en_ejecucion

    if task_id in tareas_en_ejecucion:
        tarea = tareas_en_ejecucion[task_id]
        if tarea["user_id"] == user_id_requesting or int_lvl > 3 :
            tarea["cancel"] = True 
            del tareas_en_ejecucion[task_id]
            await client.send_message(chat_id=chat_id, text=f"❌ Tarea `{task_id}` cancelada.", protect_content=protect_content)

            if cola_de_tareas:
                siguiente_tarea = cola_de_tareas.pop(0)
                await compress_video(siguiente_tarea["client"], siguiente_tarea["message"], protect_content)
        else:
            await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para cancelar esta tarea.", protect_content=protect_content)

    elif task_id in [t["id"] for t in cola_de_tareas]:
        tarea = next((t for t in cola_de_tareas if t["id"] == task_id), None)
        if tarea and (tarea["user_id"] == user_id_requesting or user_id_requesting in admin_users):
            cola_de_tareas = [t for t in cola_de_tareas if t["id"] != task_id]  # Remover tarea de la cola
            await client.send_message(chat_id=chat_id, text=f"❌ Tarea `{task_id}` eliminada de la cola.", protect_content=protect_content)
        else:
            await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para eliminar esta tarea de la cola.", protect_content=protect_content)

    else:
        await client.send_message(chat_id=chat_id, text=f"⚠️ No se encontró la tarea con ID `{task_id}`.", protect_content=protect_content)


async def listar_tareas(client, chat_id, protect_content, message):
    user_id_requesting = int(message.from_user.id) 

    global cola_de_tareas, tareas_en_ejecucion

    lista_tareas = "📝 Lista de tareas:\n\n"

    tareas_en_ejecucion_filtradas = tareas_en_ejecucion if int_lvl > 3 else {
        k: v for k, v in tareas_en_ejecucion.items() if int(v["user_id"]) == user_id_requesting
    }

    cola_enumerada = [(index + 1, tarea) for index, tarea in enumerate(cola_de_tareas)]

    cola_de_tareas_filtradas = cola_enumerada if user_id_requesting in admin_users else [
        (index, tarea) for index, tarea in cola_enumerada if int(tarea["user_id"]) == user_id_requesting
    ]

    if tareas_en_ejecucion_filtradas:
        for task_id, tarea in tareas_en_ejecucion_filtradas.items():
            user_info = await client.get_users(tarea["user_id"])
            username = f"@{user_info.username}" if user_info.username else "Usuario Anónimo"
            lista_tareas += f"Tarea actual: ID {task_id} {username} (`{tarea['user_id']}`)\n\n"

    if cola_de_tareas_filtradas:
        for index, tarea in cola_de_tareas_filtradas:
            user_info = await client.get_users(tarea["user_id"])
            username = f"@{user_info.username}" if user_info.username else "Usuario Anónimo"
            lista_tareas += f"{index}. ID: `{tarea['id']}`\n   Usuario: {username} (`{tarea['user_id']}`)\n\n"
    else:
        if not tareas_en_ejecucion_filtradas:
            lista_tareas += "📝 No hay tareas en ejecución ni en cola.\n"

    await client.send_message(chat_id=chat_id, text=lista_tareas, protect_content=protect_content)


# Compresión de video
async def compress_video(client, message, protect_content):
    user_id = message.from_user.id

    global cola_de_tareas, tareas_en_ejecucion
    task_id = str(uuid.uuid4())
    chat_id = message.chat.id

    if len(tareas_en_ejecucion) >= max_tareas:
        cola_de_tareas.append({
            "id": task_id,
            "user_id": user_id,
            "client": client,
            "message": message
        })
        await client.send_message(
            chat_id=chat_id,
            text=f"🕒 Tarea añadida a la cola con ID `{task_id}`.",
            protect_content=protect_content
        )
        return

    tareas_en_ejecucion[task_id] = {"cancel": False, "user_id": user_id}
    await client.send_message(chat_id=chat_id, text=f"🎥 Preparando la compresión del video...", protect_content=protect_content)

    try:
        if tareas_en_ejecucion[task_id]["cancel"]:
            await client.send_message(chat_id=chat_id, text=f"⚠️ La tarea `{task_id}` ha sido cancelada.", protect_content=protect_content)
            return

        if message.video or (message.document and message.document.mime_type.startswith("video/")):
            video_size = message.video.file_size if message.video else message.document.file_size

            if video_limit and video_size > video_limit and chat_id not in admin_users and chat_id not in vip_users:
                sticker = random.choice(sobre_mb)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[0])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="El archivo es demasiado grande")
                return
            if video_limit and video_size > video_limit and (chat_id in admin_users or chat_id in vip_users):
                sticker = random.choice(sobre_mb)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[0])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="Pero lo haré solo por tí")
            video_path = await client.download_media(message.video or message.document)
        elif (message.reply_to_message and 
              (message.reply_to_message.video or (message.reply_to_message.document and message.reply_to_message.document.mime_type.startswith("video/")))):
            if message.reply_to_message.video:
                video_size = message.reply_to_message.video.file_size
            elif message.reply_to_message.document.mime_type.startswith("video/"):
                video_size = message.reply_to_message.document.file_size

            if video_limit and video_size > video_limit and chat_id not in admin_users and chat_id not in vip_users:
                sticker = random.choice(sobre_mb)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[0])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="El archivo es demasiado grande")
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="No voy a convertir eso")
                return
            if video_limit and video_size > video_limit and (chat_id in admin_users or chat_id in vip_users):
                sticker = random.choice(sobre_mb)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[0])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="El archivo es demasiado grande")
                time.sleep(1)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[1])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="Pero lo haré solo por tí")
            video_path = await client.download_media(message.reply_to_message.video or message.reply_to_message.document)
        else:
            await client.send_message(chat_id=chat_id, text=f"⚠️ No se encontró un video en el mensaje.", protect_content=protect_content)
            return

        thumb_path = await generate_thumbnail(video_path)
        duration = get_video_duration(video_path)

        file_name, description, chat_id, file_path, original_video_path = \
            await procesar_video(client, message, user_id, video_path, task_id, tareas_en_ejecucion, video_settings)

        await client.send_video(
            chat_id=user_id,
            video=file_path,
            thumb=thumb_path,
            caption=file_name,
            duration=duration,
            protect_content=protect_content
        )

        await client.send_message(chat_id=chat_id, text=description, protect_content=protect_content)

        os.remove(original_video_path)
        os.remove(file_path)
        if thumb_path:
            os.remove(thumb_path)
    finally:
        try:
            del tareas_en_ejecucion[task_id]
        except KeyError:
            pass

        if cola_de_tareas:
            siguiente_tarea = cola_de_tareas.pop(0)
            await compress_video(admin_users, siguiente_tarea["client"], siguiente_tarea["message"], allowed_ids)
                                        
def get_video_metadata(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=nb_frames",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        metadata = result.stdout.strip()
        total_frames = int(metadata) if metadata.isdigit() else None

        if total_frames is None or total_frames == 0:
            raise ValueError("No se pudo obtener el número de fotogramas del video.")

        return total_frames
    except Exception as e:
        print(f"Error al obtener los metadatos del video: {e}")
        return 0

async def generate_thumbnail(video_path):
    try:
        # Obtener la duración del video
        video_duration = get_video_duration(video_path)
        if video_duration <= 0:
            raise ValueError("No se pudo determinar la duración del video.")

        # Calcular un segundo aleatorio en los primeros 10,000 fotogramas (o la duración total si es menor)
        fps = 24  # Fotogramas por segundo (supuesto común)
        max_frames = min(video_duration * fps, 10000)
        random_frame = random.randint(0, int(max_frames) - 1)

        # Convertir fotograma en tiempo (segundos)
        random_time = random_frame / fps

        output_thumb = f"{os.path.splitext(video_path)[0]}_miniatura.jpg"

        # Extraer el fotograma aleatorio
        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-ss", str(random_time),
            "-vframes", "1",
            output_thumb
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Verificar que la miniatura se haya generado correctamente
        if not os.path.exists(output_thumb):
            raise IOError("No se pudo generar la miniatura.")

        return output_thumb
    except Exception as e:
        print(f"Error al generar la miniatura: {e}")
        return None

def get_video_duration(video_path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Manejar resultados no válidos
        duration = result.stdout.strip()
        if duration == 'N/A' or not duration:
            raise ValueError("No se pudo obtener la duración del video.")
        return int(float(duration))  # Convertir a segundos
    except Exception as e:
        print(f"Error al obtener la duración del video: {e}")
        return 0

async def cambiar_miniatura(client: Client, message: Message):
    if message.reply_to_message:
        # Verifica si el mensaje al que se responde contiene un video
        reply = message.reply_to_message
        if reply.video or (reply.document and reply.document.mime_type.startswith("video")):
            # Descarga el video original
            video_path = await reply.download()

            # Verifica si el mensaje actual contiene una imagen válida
            if message.photo or (message.document and message.document.mime_type.startswith(("image/jpeg", "image/png"))):
                # Descarga la imagen recibida como miniatura
                image_path = await message.download()

                # Ajusta la imagen usando PIL
                try:
                    with Image.open(image_path) as img:
                        img = img.convert("RGB")  # Convierte a RGB para asegurar compatibilidad

                        # Calcula las dimensiones proporcionales para mantener el aspecto original
                        width, height = img.size
                        max_dimension = 320  # Dimensión máxima permitida por Telegram
                        if width > height:
                            new_width = max_dimension
                            new_height = int((max_dimension / width) * height)
                        else:
                            new_height = max_dimension
                            new_width = int((max_dimension / height) * width)

                        # Redimensiona manteniendo proporciones
                        img = img.resize((new_width, new_height))

                        # Guarda la miniatura como JPEG con calidad optimizada
                        thumb_path = "thumbnail.jpg"
                        quality = 85  # Calidad inicial
                        img.save(thumb_path, format="JPEG", quality=quality)

                        # Reduce la calidad si excede 200 KB
                        while os.path.getsize(thumb_path) > 200 * 1024 and quality > 10:
                            quality -= 5
                            img.save(thumb_path, format="JPEG", quality=quality)

                    # Obtén la duración del video si Telegram no lo proporciona
                    duration = reply.video.duration if hasattr(reply.video, "duration") else None
                    if duration is None:  # Si no tiene duración, calcula manualmente
                        duration = get_video_duration(video_path)

                    # Reenvía el video descargado con la nueva miniatura
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=video_path,
                        thumb=thumb_path,
                        duration=duration,  # Incluye la duración
                        caption="🎥 Vídeo con miniatura actualizada."
                    )

                    await message.reply("✅ Miniatura cambiada exitosamente.")
                except Exception as e:
                    await message.reply(f"⚠️ Error al procesar la miniatura: {e}")
                finally:
                    # Limpieza de archivos temporales
                    if os.path.exists(video_path):
                        os.remove(video_path)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
            else:
                await message.reply("⚠️ Debes responder a un mensaje que contenga una imagen válida (JPEG/PNG).")
        else:
            await message.reply("⚠️ El mensaje al que respondes no contiene un vídeo válido.")
    else:
        await message.reply("⚠️ Debes responder a un mensaje que contenga un vídeo.")
