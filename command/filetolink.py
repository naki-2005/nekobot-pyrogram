import os
import re
import shutil
import subprocess
from datetime import datetime
from pyrogram import Client, enums
from pyrogram.types import Message

VAULT_FOLDER = "vault_files"
SEVEN_ZIP_EXE = os.path.join("7z", "7zz")
MAX_SIZE_MB = 2000

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
    raw_path = parts[1].strip() if len(parts) == 2 else fname or "archivo"
    safe_parts = [secure_filename(p) for p in raw_path.split("/")]
    relative_path = os.path.join(*safe_parts)
    full_path = os.path.join(VAULT_FOLDER, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    await client.download_media(message.reply_to_message, full_path)
    await message.reply(f"✅ Archivo guardado como `{relative_path}` en `{VAULT_FOLDER}`.")

async def list_vault_files(client: Client, message: Message):
    if not os.path.isdir(VAULT_FOLDER):
        await client.send_message(message.from_user.id, "📁 La carpeta está vacía o no existe.")
        return

    texto = "📄 Archivos disponibles:\n\n"
    all_files = []

    for root, _, files in os.walk(VAULT_FOLDER):
        rel_root = os.path.relpath(root, VAULT_FOLDER)
        rel_root = "" if rel_root == "." else rel_root
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            all_files.append((rel_root, fname, fpath))

    for idx, (folder, fname, fpath) in enumerate(all_files, start=1):
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        ruta = folder if folder else "Root"
        texto += f"{idx}. {fname} — {size_mb:.2f} MB ({ruta})\n"

    await client.send_message(message.from_user.id, texto.strip())

def parse_nested_indices(text):
    result = []
    for part in text.split(","):
        part = part.strip()
        if part == "*":
            result.append("ALL")
        elif part.isdigit():
            result.append(int(part))
    return result

async def send_vault_file_by_index(client: Client, message: Message):
    text = message.text.strip()
    args = text.split()
    if len(args) < 2:
        await client.send_message(message.chat.id, "❌ Debes especificar los índices")
        return

    mode = None
    delete_after = False
    index_str = ""
    custom_name = ""
    flags = [arg for arg in args if arg.startswith("-")]
    for flag in flags:
        if flag == "-z":
            mode = "auto_compress"
        elif flag == "-Z":
            mode = "named_compress"
        elif flag == "-d":
            delete_after = True
    non_flags = [arg for arg in args if not arg.startswith("-")]
    index_str = non_flags[0]
    if mode == "named_compress" and len(non_flags) > 1:
        custom_name = " ".join(non_flags[1:])

    all_files = []
    for root, _, files in os.walk(VAULT_FOLDER):
        rel_root = os.path.relpath(root, VAULT_FOLDER)
        rel_root = "" if rel_root == "." else rel_root
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            all_files.append(fpath)

    selected_files = []
    for idx in parse_nested_indices(index_str):
        if idx == "ALL":
            selected_files = all_files[:]
            break
        elif isinstance(idx, int) and 1 <= idx <= len(all_files):
            selected_files.append(all_files[idx - 1])

    if not selected_files:
        await client.send_message(message.chat.id, "❌ No se encontraron archivos válidos")
        return

    if mode in ["auto_compress", "named_compress"]:
        archive_name = custom_name.strip() if mode == "named_compress" and custom_name else "archivos_comprimidos"
        archive_path = os.path.join(VAULT_FOLDER, f"{archive_name}.7z")
        total_size_mb = sum(os.path.getsize(f) for f in selected_files) / (1024 * 1024)
        volume_flag = [f"-v{MAX_SIZE_MB}m"] if total_size_mb > MAX_SIZE_MB else []
        cmd_args = [SEVEN_ZIP_EXE, "a", "-mx=0"] + volume_flag + [archive_path] + selected_files
        try:
            subprocess.run(cmd_args, check=True)
            base_name = os.path.splitext(archive_path)[0]
            sent_files = []
            for f in sorted(os.listdir(VAULT_FOLDER)):
                if f.startswith(os.path.basename(base_name)) and (f.endswith(".7z") or f.endswith(".7z.001")):
                    full_path = os.path.join(VAULT_FOLDER, f)
                    await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
                    await client.send_document(message.chat.id, document=full_path, caption=f"📦 {f}")
                    await client.send_chat_action(message.chat.id, enums.ChatAction.CANCEL)
                    sent_files.append(full_path)
            if delete_after:
                for f in selected_files + sent_files:
                    if os.path.exists(f):
                        os.remove(f)
        except Exception as e:
            await client.send_message(message.chat.id, f"❌ Error al comprimir: {e}")
        return

    for path in selected_files:
        try:
            await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_DOCUMENT)
            await client.send_document(message.chat.id, document=path, caption=f"📤 {os.path.basename(path)}")
            await client.send_chat_action(message.chat.id, enums.ChatAction.CANCEL)
            if delete_after and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            await client.send_message(message.chat.id, f"⚠️ Error al enviar `{os.path.basename(path)}`: {e}")
    
