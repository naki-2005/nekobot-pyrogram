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
    fname = fname.strip().replace(" ", "_")
    fname = re.sub(r"[^a-zA-Z0-9_.-]", "", fname)
    return fname or "file"

async def clear_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        return
    for fname in os.listdir(VAULT_FOLDER):
        fpath = os.path.join(VAULT_FOLDER, fname)
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
                await message.reply(f"✅ Archivo borrados")
            except Exception:
                pass

async def handle_up_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply("❌ Este comando debe responder a un archivo.")
        return
    fname, fid, size_mb = get_info(message.reply_to_message)
    safe_name = secure_filename(fname)
    path = os.path.join(VAULT_FOLDER, safe_name)
    os.makedirs(VAULT_FOLDER, exist_ok=True)
    await client.download_media(message.reply_to_message, path)
    await message.reply(f"✅ Archivo guardado como `{safe_name}` en `{VAULT_FOLDER}`.")
  
