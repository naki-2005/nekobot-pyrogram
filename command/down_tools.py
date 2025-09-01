import os
import subprocess
import asyncio
from pyrogram import Client
from pyrogram.types import Message

async def handle_megadl_command(client: Client, message: Message, mega_url: str, chat_id: int):
    desmega_path = os.path.join("command", "desmega")
    output_dir = os.path.join("vault_files", "mega_dl")
    os.makedirs(output_dir, exist_ok=True)

    try:
        result = subprocess.run(
            [desmega_path, mega_url, "--path", output_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            await message.reply(f"❌ Error al ejecutar desmega:\n{result.stderr}")
            return

        files = os.listdir(output_dir)
        if not files:
            await message.reply("⚠️ No se encontró ningún archivo descargado.")
            return

        seven_zip_exe = os.path.join("7z", "7zz")

        for file_name in files:
            file_path = os.path.join(output_dir, file_name)
            if not os.path.isfile(file_path):
                continue

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            if file_size_mb > 2000:
                archive_base = os.path.join(output_dir, f"{file_name}_archive.7z")
                cmd_args = [
                    seven_zip_exe,
                    'a',
                    '-mx=0',
                    f'-v2000m',
                    archive_base,
                    file_path
                ]

                zip_result = subprocess.run(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if zip_result.returncode != 0:
                    await message.reply(f"❌ Error al comprimir {file_name}:\n{zip_result.stderr}")
                    continue

                os.remove(file_path)

                archive_parts = sorted([
                    f for f in os.listdir(output_dir)
                    if f.startswith(f"{file_name}_archive.7z")
                ])
                for part in archive_parts:
                    part_path = os.path.join(output_dir, part)
                    await client.send_document(chat_id, document=part_path)
                    os.remove(part_path)

            else:
                await client.send_document(chat_id, document=file_path)
                os.remove(file_path)

        await message.reply("✅ Archivos enviados correctamente.")

    except Exception as e:
        await message.reply(f"❌ Error inesperado: {str(e)}")
