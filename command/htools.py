import os
import requests
import re
from uuid import uuid4  # Generar identificadores únicos
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from command.get_files.hfiles import descargar_hentai, borrar_carpeta

async def nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type="download"):
    if link_type not in ["nh", "3h"]:
        await message.reply("Tipo de enlace no válido. Use 'nh' o '3h'.")
        return

    base_url = "nhentai.net/g" if link_type == "nh" else "3hentai.net/d"

    for code in codes:
        try:
            url = f"https://{base_url}/{code}/"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            await message.reply(f"El código {code} es erróneo: {str(e)}")
            continue

        # Generar nombre único para la carpeta
        random_folder_name = f"h3dl/{uuid4()}"

        try:
            # Descargar el contenido
            result = descargar_hentai(url, code, base_url, operation_type, protect_content, random_folder_name)
            if result.get("error"):
                await message.reply(f"Error con el código {code}: {result['error']}")
            else:
                # Usar el título de la página como caption y nombre del archivo
                caption = result.get("caption", "Contenido descargado")
                
                # Enviar botones Inline
                await enviar_opciones(client, message, caption, result['cbz_file'], result['pdf_file'], random_folder_name)
        except Exception as e:
            await message.reply(f"Error al manejar archivos para el código {code}: {str(e)}")

        try:
            # Limpiar únicamente la carpeta temporal
            borrar_carpeta(random_folder_name, result.get("cbz_file"))
        except Exception as e:
            await message.reply(f"Error al limpiar carpeta para el código {code}: {str(e)}")

async def enviar_opciones(client, message, caption, cbz_file, pdf_file, folder_name):
    """
    Envía botones Inline para que el usuario elija entre CBZ, PDF o fotos.
    """
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Descargar CBZ", callback_data=f"cbz|{cbz_file}"),
            InlineKeyboardButton("Descargar PDF", callback_data=f"pdf|{pdf_file}")
        ],
        [InlineKeyboardButton("Ver Fotos (10 por lote)", callback_data=f"fotos|{folder_name}")]
    ])
    
    await message.reply(caption, reply_markup=keyboard)

async def manejar_opcion(client, callback_query):
    """
    Procesa las opciones seleccionadas en los botones Inline.
    """
    data = callback_query.data.split('|')
    opcion = data[0]

    if opcion == "cbz":
        cbz_file = data[1]
        # Enviar el archivo CBZ
        await client.send_document(
            callback_query.message.chat.id,
            cbz_file,
            caption="Aquí está tu CBZ 📚"
        )
    elif opcion == "pdf":
        pdf_file = data[1]
        # Enviar el archivo PDF
        await client.send_document(
            callback_query.message.chat.id,
            pdf_file,
            caption="Aquí está tu PDF 🖨️"
        )
    elif opcion == "fotos":
        folder_name = data[1]
        # Enviar fotos en lotes de 10
        archivos = sorted([os.path.join(folder_name, f) for f in os.listdir(folder_name) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        lote = 10
        for i in range(0, len(archivos), lote):
            await client.send_media_group(
                callback_query.message.chat.id,
                [
                    {"type": "photo", "media": archivo} for archivo in archivos[i:i + lote]
                ]
            )
    await callback_query.answer("¡Opción procesada!")
