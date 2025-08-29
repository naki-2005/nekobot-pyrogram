import os
import re
from datetime import datetime
from pyrogram import Client
from pyrogram.types import Message

VAULT_FOLDER = "vault_files"

def get_info(msg: Message):
    media = next((m for m in [msg.document, msg.photo, msg.audio, msg.video, msg.voice, msg.animation, msg.sticker] if m), None)
    fname = getattr(media, "file_name", None) or media.file_id if media else None
    fid = media.file_id if media else None
    size = getattr(media, "file_size", 0) / (1024 * 1024) if media else 0.0
    return fname, fid, size

def secure_filename(fname: str) -> str:
    fname = os.path.basename(fname)
    fname = re.sub(r"[^a-zA-Z0-9_.\- ]", "", fname)  # Conserva espacios
    return fname or "file"

async def clear_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        return
    for fname in os.listdir(VAULT_FOLDER):
        fpath = os.path.join(VAULT_FOLDER, fname)
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
                await message.reply(f"✅ Archivos borrados")
            except Exception:
                pass

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
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await client.send_message(message.from_user.id, "❌ El ID debe ser un número")
        return

    index = int(parts[1])
    archivos = sorted([f for f in os.listdir(VAULT_FOLDER) if os.path.isfile(os.path.join(VAULT_FOLDER, f))])

    if index < 1 or index > len(archivos):
        await client.send_message(message.from_user.id, "❌ Ese archivo no existe")
        return

    selected_file = archivos[index - 1]
    path = os.path.join(VAULT_FOLDER, selected_file)
    await client.send_document(message.from_user.id, document=path, caption=f"📤 {selected_file}")
