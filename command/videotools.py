import asyncio
import os
import uuid
import re
import subprocess
import random
from command.video_processor import procesar_video
from data.vars import video_limit, video_settings
from data.stickers import sobre_mb
import time
from pyrogram import Client
from pyrogram.types import Message
from PIL import Image

max_tareas = int(os.getenv('MAX_TASKS', '1'))

tareas_en_ejecucion = {}
cola_de_tareas = []

import copy
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def update_video_settings(client, message, protect_content):
    user_id = message.from_user.id
    global video_settings
    
    if user_id not in video_settings:
        video_settings[user_id] = copy.deepcopy(video_settings.get('default', {}))

    try:
        command_params = message.text.split()[1:]

        if not command_params:
            await mostrar_menu_configuracion(client, message, user_id, protect_content)
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
                elif key == 'fps' and not value.replace('.', '').isdigit():
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

async def mostrar_menu_configuracion(client, message, user_id, protect_content):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎞️ Resolución", callback_data="vs_resolution")],
        [InlineKeyboardButton("📊 CRF", callback_data="vs_crf")],
        [InlineKeyboardButton("🔊 Audio Bitrate", callback_data="vs_audio_bitrate")],
        [InlineKeyboardButton("⚡ FPS", callback_data="vs_fps")],
        [InlineKeyboardButton("🚀 Preset", callback_data="vs_preset")],
        [InlineKeyboardButton("🔧 Codec", callback_data="vs_codec")],
        [InlineKeyboardButton("✅ Aplicar configuración", callback_data="vs_apply")]
    ])
    
    config_text = "⚙️ **Configuración Actual:**\n"
    for key, value in video_settings[user_id].items():
        config_text += f"• **{key}**: `{value}`\n"
    
    await message.reply_text(config_text, reply_markup=keyboard, protect_content=protect_content)

async def handle_video_settings_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "vs_back":
        await mostrar_menu_configuracion(client, callback_query.message, user_id, True)
        await callback_query.answer()
        return
        
    if data == "vs_apply":
        config_text = "⚙️ **Configuración Aplicada:**\n"
        for key, value in video_settings[user_id].items():
            config_text += f"• **{key}**: `{value}`\n"
        await callback_query.message.edit_text(config_text)
        await callback_query.answer("✅ Configuración aplicada")
        return

    if data.startswith("vs_set_"):
        param = data.split("_")[2]
        value = data.split("_")[3]
        video_settings[user_id][param] = value
        await mostrar_submenu(client, callback_query.message, user_id, param, True)
        await callback_query.answer(f"✅ {param} cambiado a {value}")
        return

    if data in ["vs_resolution", "vs_crf", "vs_audio_bitrate", "vs_fps", "vs_preset", "vs_codec"]:
        param = data.split("_")[1]
        await mostrar_submenu(client, callback_query.message, user_id, param, True)
        await callback_query.answer()
        return

async def mostrar_submenu(client, message, user_id, param, protect_content):
    back_button = InlineKeyboardButton("🔙 Atrás", callback_data="vs_back")
    
    if param == "resolution":
        opciones = [
            ["640x360", "vs_set_resolution_640x360"],
            ["854x480", "vs_set_resolution_854x480"], 
            ["1280x720", "vs_set_resolution_1280x720"],
            ["1920x1080", "vs_set_resolution_1920x1080"]
        ]
    elif param == "crf":
        opciones = [
            ["23 (Calidad Alta)", "vs_set_crf_23"],
            ["25 (Calidad Media)", "vs_set_crf_25"],
            ["28 (Calidad Baja)", "vs_set_crf_28"],
            ["30 (Muy Comprimido)", "vs_set_crf_30"]
        ]
    elif param == "audio_bitrate":
        opciones = [
            ["64k", "vs_set_audio_bitrate_64k"],
            ["80k", "vs_set_audio_bitrate_80k"],
            ["96k", "vs_set_audio_bitrate_96k"], 
            ["128k", "vs_set_audio_bitrate_128k"]
        ]
    elif param == "fps":
        opciones = [
            ["18", "vs_set_fps_18"],
            ["24", "vs_set_fps_24"],
            ["30", "vs_set_fps_30"],
            ["60", "vs_set_fps_60"]
        ]
    elif param == "preset":
        opciones = [
            ["ultrafast", "vs_set_preset_ultrafast"],
            ["veryfast", "vs_set_preset_veryfast"],
            ["medium", "vs_set_preset_medium"],
            ["slow", "vs_set_preset_slow"]
        ]
    elif param == "codec":
        opciones = [
            ["libx264", "vs_set_codec_libx264"],
            ["libx265", "vs_set_codec_libx265"],
            ["libvpx", "vs_set_codec_libvpx"]
        ]
    
    keyboard = []
    for opcion in opciones:
        keyboard.append([InlineKeyboardButton(opcion[0], callback_data=opcion[1])])
    keyboard.append([back_button])
    
    current_value = video_settings[user_id].get(param, "N/A")
    text = f"⚙️ **Seleccionar {param}**\n\n**Valor actual:** `{current_value}`"
    
    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def cancelar_tarea(int_lvl, client, task_id, chat_id, message, protect_content):
    user_id_requesting = message.from_user.id

    global cola_de_tareas, tareas_en_ejecucion

    if task_id in tareas_en_ejecucion:
        tarea = tareas_en_ejecucion[task_id]
        if tarea["user_id"] == user_id_requesting or int_lvl >= 4:  # Admin o superior
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
        if tarea and (tarea["user_id"] == user_id_requesting or int_lvl >= 4):  # Admin o superior
            cola_de_tareas = [t for t in cola_de_tareas if t["id"] != task_id]
            await client.send_message(chat_id=chat_id, text=f"❌ Tarea `{task_id}` eliminada de la cola.", protect_content=protect_content)
        else:
            await client.send_message(chat_id=chat_id, text="⚠️ No tienes permiso para eliminar esta tarea de la cola.", protect_content=protect_content)

    else:
        await client.send_message(chat_id=chat_id, text=f"⚠️ No se encontró la tarea con ID `{task_id}`.", protect_content=protect_content)

async def listar_tareas(client, chat_id, protect_content, message, int_lvl):
    user_id_requesting = int(message.from_user.id) 

    global cola_de_tareas, tareas_en_ejecucion

    lista_tareas = "📝 Lista de tareas:\n\n"

    # Filtrar tareas según permisos
    tareas_en_ejecucion_filtradas = tareas_en_ejecucion if int_lvl >= 4 else {
        k: v for k, v in tareas_en_ejecucion.items() if int(v["user_id"]) == user_id_requesting
    }

    cola_enumerada = [(index + 1, tarea) for index, tarea in enumerate(cola_de_tareas)]

    cola_de_tareas_filtradas = cola_enumerada if int_lvl >= 4 else [
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

async def compress_video(client, message, protect_content, int_lvl):
    user_id = message.from_user.id
    chat_id = message.chat.id

    global cola_de_tareas, tareas_en_ejecucion
    task_id = str(uuid.uuid4())

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

            # Verificar límite de tamaño según nivel de usuario
            if video_limit and video_size > video_limit and int_lvl < 3:  # Usuarios normales
                sticker = random.choice(sobre_mb)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[0])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="El archivo es demasiado grande")
                return
            if video_limit and video_size > video_limit and int_lvl >= 3:  # VIP o superior
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

            # Verificar límite de tamaño según nivel de usuario
            if video_limit and video_size > video_limit and int_lvl < 3:  # Usuarios normales
                sticker = random.choice(sobre_mb)
                await client.send_sticker(chat_id=chat_id, sticker=sticker[0])
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="El archivo es demasiado grande")
                time.sleep(1)
                await client.send_message(chat_id=chat_id, text="No voy a convertir eso")
                return
            if video_limit and video_size > video_limit and int_lvl >= 3:  # VIP o superior
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

        # Limpieza
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
            # Pasar también int_lvl para la siguiente tarea
            siguiente_int_lvl = 1  # Necesitarías una forma de obtener el int_lvl del usuario de la siguiente tarea
            await compress_video(siguiente_tarea["client"], siguiente_tarea["message"], protect_content, siguiente_int_lvl)

# Las funciones restantes permanecen igual...
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
        video_duration = get_video_duration(video_path)
        if video_duration <= 0:
            raise ValueError("No se pudo determinar la duración del video.")

        fps = 24
        max_frames = min(video_duration * fps, 10000)
        random_frame = random.randint(0, int(max_frames) - 1)
        random_time = random_frame / fps

        output_thumb = f"{os.path.splitext(video_path)[0]}_miniatura.jpg"

        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-ss", str(random_time),
            "-vframes", "1",
            output_thumb
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

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
        duration = result.stdout.strip()
        if duration == 'N/A' or not duration:
            raise ValueError("No se pudo obtener la duración del video.")
        return int(float(duration))
    except Exception as e:
        print(f"Error al obtener la duración del video: {e}")
        return 0

async def cambiar_miniatura(client: Client, message: Message):
    if message.reply_to_message:
        reply = message.reply_to_message
        if reply.video or (reply.document and reply.document.mime_type.startswith("video")):
            video_path = await reply.download()

            if message.photo or (message.document and message.document.mime_type.startswith(("image/jpeg", "image/png"))):
                image_path = await message.download()

                try:
                    with Image.open(image_path) as img:
                        img = img.convert("RGB")
                        width, height = img.size
                        max_dimension = 320
                        if width > height:
                            new_width = max_dimension
                            new_height = int((max_dimension / width) * height)
                        else:
                            new_height = max_dimension
                            new_width = int((max_dimension / height) * width)

                        img = img.resize((new_width, new_height))
                        thumb_path = "thumbnail.jpg"
                        quality = 85
                        img.save(thumb_path, format="JPEG", quality=quality)

                        while os.path.getsize(thumb_path) > 200 * 1024 and quality > 10:
                            quality -= 5
                            img.save(thumb_path, format="JPEG", quality=quality)

                    duration = reply.video.duration if hasattr(reply.video, "duration") else None
                    if duration is None:
                        duration = get_video_duration(video_path)

                    await client.send_video(
                        chat_id=message.chat.id,
                        video=video_path,
                        thumb=thumb_path,
                        duration=duration,
                        caption="🎥 Vídeo con miniatura actualizada."
                    )

                    await message.reply("✅ Miniatura cambiada exitosamente.")
                except Exception as e:
                    await message.reply(f"⚠️ Error al procesar la miniatura: {e}")
                finally:
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
