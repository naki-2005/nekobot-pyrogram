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

import subprocess
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
MAX_SIZE_MB = 2000

def parse_indices(text):
    indices = set()
    for part in text.split(","):
        if "-" in part:
            start, end = part.split("-")
            if start.isdigit() and end.isdigit():
                indices.update(range(int(start), int(end) + 1))
        elif part.strip().isdigit():
            indices.add(int(part.strip()))
    return sorted(indices)

async def send_vault_file_by_index(client: Client, message: Message):
    text = message.text.strip()
    args = text.split(maxsplit=1)
    if len(args) != 2:
        await client.send_message(message.chat.id, "❌ Debes especificar los índices")
        return

    mode = None
    content = args[1]
    if content.startswith("-z "):
        mode = "auto_compress"
        content = content[3:].strip()
    elif content.startswith("-Z "):
        mode = "named_compress"
        content = content[3:].strip()

    archivos = sorted([f for f in os.listdir(VAULT_FOLDER) if os.path.isfile(os.path.join(VAULT_FOLDER, f))])
    if not archivos:
        await client.send_message(message.chat.id, "❌ No hay archivos en el servidor")
        return

    match = re.match(r"([\d\-,]+)(?:\s+(.*))?", content)
    if not match:
        await client.send_message(message.chat.id, "❌ Formato incorrecto. Usa: /sendfiles 1-3,5 o /sendfiles -Z 1-3 Nombre")
        return

    index_str, custom_name = match.groups()
    indices = parse_indices(index_str)
    selected_files = []

    for i in indices:
        if 1 <= i <= len(archivos):
            selected_files.append(os.path.join(VAULT_FOLDER, archivos[i - 1]))

    if not selected_files:
        await client.send_message(message.chat.id, "❌ No se encontraron archivos válidos")
        return

    if mode in ["auto_compress", "named_compress"]:
        archive_name = custom_name.strip() if mode == "named_compress" and custom_name else "archivos_comprimidos"
        archive_path = os.path.join(VAULT_FOLDER, f"{archive_name}.7z")

        total_size_mb = sum(os.path.getsize(f) for f in selected_files) / (1024 * 1024)
        volume_flag = []
        if total_size_mb > MAX_SIZE_MB:
            volume_flag = [f"-v{MAX_SIZE_MB}m"]

        cmd_args = [SEVEN_ZIP_EXE, "a", "-mx=0"] + volume_flag + [archive_path] + selected_files

        try:
            subprocess.run(cmd_args, check=True)
            base_name = os.path.splitext(archive_path)[0]
            for f in sorted(os.listdir(VAULT_FOLDER)):
                if f.startswith(os.path.basename(base_name)) and f.endswith(".7z") or f.endswith(".7z.001"):
                    full_path = os.path.join(VAULT_FOLDER, f)
                    await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await client.send_document(message.chat.id, document=full_path, caption=f"📦 {f}")
            await client.send_chat_action(message.chat.id, enums.ChatAction.CANCEL)
        except Exception as e:
            await client.send_message(message.chat.id, f"❌ Error al comprimir: {e}")
        return

    for path in selected_files:
        await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
        await client.send_document(message.chat.id, document=path, caption=f"📤 {os.path.basename(path)}")
    await client.send_chat_action(message.chat.id, enums.ChatAction.CANCEL)
