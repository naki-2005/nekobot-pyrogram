import asyncio
import os
import uuid
import re
import subprocess
import random
from command.video_processor import procesar_video
from data.vars import admin_users, vip_users, video_limit, video_settings, allowed_ids
from data.stickers import sobre_mb
import time

max_tareas = int(os.getenv('MAX_TASKS', '1'))

tareas_en_ejecucion = {}
cola_de_tareas = []

async def update_video_settings(client, message):
    user_id = message.from_user.id
    protect_content = user_id not in allowed_ids
    user_id = str(message.from_user.id)

    global video_settings
    try:
        # Obtener los parámetros del comando
        command_params = message.text.split()[1:]
        
        # Si no hay parámetros, mostrar las configuraciones actuales del usuario
        if not command_params:
            if user_id in video_settings:
                user_config = video_settings[user_id]
            else:
                user_config = video_settings['default']  # Usamos configuración por defecto si no hay personalización
            configuracion_actual = "/calidad " + " ".join(f"{k}={v}" for k, v in user_config.items())
            await message.reply_text(f"⚙️ Configuración actual:\n`{configuracion_actual}`", protect_content=protect_content)
            return
        
        # Crear un diccionario con los parámetros, validando el formato clave=valor
        params = {}
        for item in command_params:
            if "=" not in item or len(item.split("=")) != 2:
                raise ValueError(f"Formato inválido para el parámetro: '{item}'. Usa clave=valor.")
            key, value = item.split("=")
            params[key] = value

        # Validar parámetros y crear o actualizar configuraciones del usuario
        if user_id not in video_settings:
            video_settings[user_id] = video_settings['default'].copy()  # Copiar configuración por defecto

        for key, value in params.items():
            if key in video_settings['default']:  # Validamos contra las claves por defecto
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
                
                video_settings[user_id][key] = value  # Actualizamos la configuración del usuario

        # Mostrar las configuraciones actualizadas del usuario
        configuracion_texto = "/calidad " + " ".join(f"{k}={v}" for k, v in video_settings[user_id].items())
        await message.reply_text(f"⚙️ Configuraciones de video actualizadas para User ID {user_id}:\n`{configuracion_texto}`", protect_content=protect_content)
    
    except ValueError as ve:
        await message.reply_text(f"❌ Error de validación:\n{ve}", protect_content=protect_content)
    except Exception as e:
        await message.reply_text(f"❌ Error al procesar el comando:\n{e}", protect_content=protect_content)

# Cancelar tareas
async def cancelar_tarea(admin_users, client, task_id, chat_id, message, allowed_ids):
    user_id_requesting = message.from_user.id
    protect_content = user_id_requesting not in allowed_ids

    global cola_de_tareas
    if task_id in tareas_en_ejecucion:
        tarea = tareas_en_ejecucion[task_id]
        if tarea["user_id"] == user_id_requesting or user_id_requesting in admin_users:
            tarea["cancel"] = True
            await client.send_message(chat_id=chat_id, text=f"❌ Tarea `{task_id}` cancelada.", protect_content=protect_content)
        else:
            await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para cancelar esta tarea.", protect_content=protect_content)
    elif task_id in [t["id"] for t in cola_de_tareas]:
        tarea = next((t for t in cola_de_tareas if t["id"] == task_id), None)
        if tarea and (tarea["user_id"] == user_id_requesting or user_id_requesting in admin_users):
            cola_de_tareas = [t for t in cola_de_tareas if t["id"] != task_id]
            await client.send_message(chat_id=chat_id, text=f"❌ Tarea `{task_id}` eliminada de la cola.", protect_content=protect_content)
        else:
            await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para eliminar esta tarea de la cola.", protect_content=protect_content)
    else:
        await client.send_message(chat_id=chat_id, text=f"⚠️ No se encontró la tarea con ID `{task_id}`.", protect_content=protect_content)

# Listar tareas
async def listar_tareas(client, chat_id, message, admin_users):
    user_id_requesting = message.from_user.id
    protect_content = user_id_requesting not in admin_users

    global cola_de_tareas, tareas_en_ejecucion

    # Inicializa la lista de tareas
    lista_tareas = "📝 Lista de tareas:\n\n"
    total_tareas = len(tareas_en_ejecucion) + len(cola_de_tareas)

    if user_id_requesting in admin_users:
        lista_tareas += f"🔢 Número total de tareas: {total_tareas}\n\n"

        # Agrega tareas en ejecución
        if tareas_en_ejecucion:
            for task_id, tarea in tareas_en_ejecucion.items():
                user_info = await client.get_users(tarea["user_id"])
                username = f"@{user_info.username}" if user_info.username else "Usuario Anónimo"
                lista_tareas += f"Tarea actual: ID {task_id} {username} (`{tarea['user_id']}`)\n\n"

        # Agrega tareas en cola
        if cola_de_tareas:
            for index, tarea in enumerate(cola_de_tareas, start=1):
                user_info = await client.get_users(tarea["user_id"])
                username = f"@{user_info.username}" if user_info.username else "Usuario Anónimo"
                lista_tareas += f"{index}. ID: `{tarea['id']}`\n   Usuario: {username} (`{tarea['user_id']}`)\n\n"
        else:
            lista_tareas += "📝 No hay tareas en ejecución ni en cola.\n"
    else:
        user_specific_tasks = [
            tarea for tarea in cola_de_tareas + list(tareas_en_ejecucion.values())
            if tarea["user_id"] == user_id_requesting
        ]
        lista_tareas += f"🔢 Número total de tareas: {total_tareas}\n\n"
        lista_tareas += f"Tareas de usuario ID {user_id_requesting}:\n\n"
        
        if user_specific_tasks:
            for tarea in user_specific_tasks:
                lista_tareas += f"- ID: `{tarea['id']}`\n\n"
        else:
            lista_tareas += "📝 No tienes tareas asignadas.\n"

    # Envía el mensaje
    await client.send_message(chat_id=chat_id, text=lista_tareas, protect_content=protect_content)




import random
import subprocess
import os

# Función para obtener el número total de fotogramas
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
        

# Ajuste en compress_video
async def compress_video(admin_users, client, message):
    user_id = message.from_user.id
    protect_content = user_id not in allowed_ids

    global cola_de_tareas
    task_id = str(uuid.uuid4())
    chat_id = message.chat.id

    user_info = await client.get_users(user_id)
    username = f"@{user_info.username}" if user_info.username else f"Usuario Anónimo ({user_id})"

    if len(tareas_en_ejecucion) >= max_tareas:
        cola_de_tareas.append({
            "id": task_id,
            "user_id": user_id,
            "username": username,
            "client": client,
            "message": message
        })
        await client.send_message(chat_id=chat_id, text=f"🕒 Tarea añadida a la cola con ID `{task_id}`.", protect_content=protect_content)
        return

    tareas_en_ejecucion[task_id] = {"cancel": False, "user_id": user_id}
    await client.send_message(chat_id=chat_id, text=f"🎥 Preparando la compresión del video...\n", protect_content=protect_content)

    try:
        if message.video or (message.document and message.document.mime_type.startswith("video/")):
            video_size = message.video.file_size if message.video else message.document.file_size

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

            video_path = await client.download_media(message.video or message.document)
        elif message.reply_to_message and (message.reply_to_message.video or (message.reply_to_message.document and message.reply_to_message.document.mime_type.startswith("video/"))):
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
            await client.send_message(chat_id=chat_id, text=f"⚠️ No se encontró un video en el mensaje o respuesta asociada.", protect_content=protect_content)
            return

        # Generar la miniatura del video
        thumb_path = await generate_thumbnail(video_path)
        if not thumb_path:
            await client.send_message(chat_id=chat_id, text="⚠️ No se pudo generar una miniatura para el video.", protect_content=protect_content)

        # Obtener la duración del video
        duration = get_video_duration(video_path)
        if duration <= 0:
            await client.send_message(chat_id=chat_id, text="⚠️ No se pudo obtener la duración del video.", protect_content=protect_content)

        # Procesar el video
        file_name, description, chat_id, file_path, original_video_path = await procesar_video(client, message, video_path, task_id, tareas_en_ejecucion)

        # Enviar el video comprimido con la miniatura generada
        await client.send_video(
            chat_id=user_id,
            video=file_path,
            thumb=thumb_path,  # Miniatura generada aleatoriamente
            caption=file_name,
            duration=duration,
            protect_content=protect_content
        )

        # Notificar el resultado al usuario
        await client.send_message(chat_id=chat_id, text=description, protect_content=protect_content)

        # Eliminar los archivos temporales
        os.remove(original_video_path)
        os.remove(file_path)
        if thumb_path:
            os.remove(thumb_path)  # Eliminar la miniatura
    finally:
        try:
            del tareas_en_ejecucion[task_id]
        except KeyError:
            pass

        if cola_de_tareas:
            siguiente_tarea = cola_de_tareas.pop(0)
            user_id = siguiente_tarea["user_id"]  # Obtener el ID del usuario desde la tarea
            await compress_video(admin_users, siguiente_tarea["client"], siguiente_tarea["message"], user_id)
    
