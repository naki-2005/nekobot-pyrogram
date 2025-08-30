import os
import re
import shutil
from datetime import datetime
from pyrogram import Client
from pyrogram.types import Message
from pyrogram import enums

VAULT_FOLDER = "vault_files"

def get_info(msg: Message):
    media = next((m for m in [msg.document, msg.photo, msg.audio, msg.video, msg.voice, msg.animation, msg.sticker] if m), None)
    fname = getattr(media, "file_name", None) or media.file_id if media else None
    fid = media.file_id if media else None
    size = getattr(media, "file_size", 0) / (1024 * 1024) if media else 0.0
    return fname, fid, size

def secure_filename(fname: str) -> str:
    fname = os.path.basename(fname)
    fname = re.sub(r"[^a-zA-Z0-9_.\- ]", "", fname)
    return fname or "file"

async def clear_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        await message.reply("📁 La carpeta no existe.")
        return

    try:
        shutil.rmtree(VAULT_FOLDER)
        os.makedirs(VAULT_FOLDER, exist_ok=True)
        await message.reply("✅ Todos los archivos y carpetas fueron eliminados.")
    except Exception as e:
        await message.reply(f"❌ Error al borrar: {e}")


async def handle_up_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("❌ Este comando debe responder a un archivo.")
        return

    fname, fid, size_mb = get_info(message.reply_to_message)

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) == 2:
        custom_name = secure_filename(parts[1])
    else:
        custom_name = secure_filename(fname)

    path = os.path.join(VAULT_FOLDER, custom_name)
    os.makedirs(VAULT_FOLDER, exist_ok=True)
    await client.download_media(message.reply_to_message, path)
    await message.reply(f"✅ Archivo guardado como `{custom_name}` en `{VAULT_FOLDER}`.")

async def list_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        await client.send_message(message.from_user.id, "📁 La carpeta está vacía o no existe.")
        return

    archivos = sorted([f for f in os.listdir(VAULT_FOLDER) if os.path.isfile(os.path.join(VAULT_FOLDER, f))])
    if not archivos:
        await client.send_message(message.from_user.id, "📁 No hay archivos guardados.")
        return

    texto = "📄 Archivos disponibles:\n\n"
    for idx, fname in enumerate(archivos, start=1):
        fpath = os.path.join(VAULT_FOLDER, fname)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        texto += f"{idx}. {fname} — {size_mb:.2f} MB\n"

    await client.send_message(message.from_user.id, texto.strip())


async def send_vault_file_by_index(client: Client, message: Message):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        await client.send_message(message.chat.id, "❌ Debes especificar uno o más índices")
        return

    index_str = parts[1]
    archivos = sorted([f for f in os.listdir(VAULT_FOLDER) if os.path.isfile(os.path.join(VAULT_FOLDER, f))])

    if not archivos:
        await client.send_message(message.chat.id, "📁 No hay archivos guardados.")
        return

    def parse_indices(index_str):
        indices = set()
        for part in index_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = map(int, part.split("-"))
                    indices.update(range(start, end + 1))
                except:
                    continue
            elif part.isdigit():
                indices.add(int(part))
        return sorted(i for i in indices if 1 <= i <= len(archivos))

    indices = parse_indices(index_str)
    if not indices:
        await client.send_message(message.chat.id, "❌ No se encontraron índices válidos.")
        return

    for i in indices:
        selected_file = archivos[i - 1]
        path = os.path.join(VAULT_FOLDER, selected_file)

        if not os.path.exists(path):
            await client.send_message(message.chat.id, f"❌ Archivo no encontrado: {selected_file}")
            continue

        try:
            await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
            await client.send_document(message.chat.id, document=path, caption=f"📤 {selected_file}")
            await client.send_chat_action(message.chat.id, enums.ChatAction.CANCEL)
        except Exception as e:
            await client.send_message(message.chat.id, f"⚠️ Error al enviar `{selected_file}`: {e}")
