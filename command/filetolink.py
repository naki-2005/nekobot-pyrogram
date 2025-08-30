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
    if len(parts) == 2:
        raw_path = parts[1].strip()
    else:
        raw_path = fname or "archivo"
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
    folder_map = {}

    for root, dirs, files in os.walk(VAULT_FOLDER):
        rel_root = os.path.relpath(root, VAULT_FOLDER)
        if rel_root == ".":
            rel_root = "Root"
        folder_map.setdefault(rel_root, []).extend(sorted(files))

    folder_keys = sorted(folder_map.keys())
    for folder_idx, folder in enumerate(folder_keys, start=1):
        texto += f"{folder}:\n"
        for file_idx, fname in enumerate(folder_map[folder], start=1):
            fpath = os.path.join(VAULT_FOLDER, folder if folder != "Root" else "", fname)
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            label = f"{folder_idx}.{file_idx}" if folder != "Root" else f"{file_idx}"
            texto += f"{label}. {fname} — {size_mb:.2f} MB\n"
        texto += "\n"

    await client.send_message(message.from_user.id, texto.strip())


def parse_nested_indices(text):
    result = []
    for part in text.split(","):
        part = part.strip()
        if part.endswith(".*"):
            try:
                folder_idx = int(part[:-2])
                result.append((folder_idx, None))  # carpeta completa
            except:
                continue
        elif "-" in part:
            try:
                start, end = part.split("-")
                f_start, i_start = map(int, start.split("."))
                f_end, i_end = map(int, end.split("."))
                if f_start == f_end:
                    for i in range(i_start, i_end + 1):
                        result.append((f_start, i))
            except:
                continue
        elif "." in part:
            try:
                f_idx, i_idx = map(int, part.split("."))
                result.append((f_idx, i_idx))
            except:
                continue
        elif part.isdigit():
            result.append((int(part), None))
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
    folder_map = {}
    for root, dirs, files in os.walk(VAULT_FOLDER):
        rel_root = os.path.relpath(root, VAULT_FOLDER)
        if rel_root == ".":
            rel_root = ""
        folder_map.setdefault(rel_root, []).extend(sorted(files))
    folder_keys = sorted(folder_map.keys())
    selected_files = []
    for item in parse_nested_indices(index_str):
        folder_idx, file_idx = item
        if 1 <= folder_idx <= len(folder_keys):
            folder = folder_keys[folder_idx - 1]
            files = folder_map[folder]
            if file_idx is None:
                for fname in files:
                    fpath = os.path.join(VAULT_FOLDER, folder, fname) if folder else os.path.join(VAULT_FOLDER, fname)
                    selected_files.append(fpath)
            elif 1 <= file_idx <= len(files):
                fname = files[file_idx - 1]
                fpath = os.path.join(VAULT_FOLDER, folder, fname) if folder else os.path.join(VAULT_FOLDER, fname)
                selected_files.append(fpath)
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
