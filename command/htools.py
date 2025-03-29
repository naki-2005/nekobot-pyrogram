import os
import requests
import zipfile
from uuid import uuid4  # Generar identificadores únicos
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from command.get_files.hfiles import descargar_hentai, borrar_carpeta

# Variable MAIN_ADMIN definida en las variables de entorno
MAIN_ADMIN = os.getenv("MAIN_ADMIN")

# Diccionario para mapear callback_data a datos reales
callback_data_map = {}
message_ids_to_delete = []  # Lista para almacenar los IDs de mensajes a borrar

async def nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type="download"):
    """
    Operación combinada para manejar la descarga y el envío de archivos antes de la limpieza.
    """
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

                # Subir CBZ al chat de MAIN_ADMIN y registrar el ID del mensaje
                cbz_message = await client.send_document(
                    MAIN_ADMIN,
                    result['cbz_file']
                )
                cbz_file_id = cbz_message.document.file_id
                message_ids_to_delete.append(cbz_message.id)  # Registrar mensaje para borrar

                # Subir PDF al chat de MAIN_ADMIN y registrar el ID del mensaje
                pdf_message = await client.send_document(
                    MAIN_ADMIN,
                    result['pdf_file']
                )
                pdf_file_id = pdf_message.document.file_id
                message_ids_to_delete.append(pdf_message.id)  # Registrar mensaje para borrar

                # Generar identificadores únicos para botones Inline
                cbz_button_id = str(uuid4())
                pdf_button_id = str(uuid4())
                fotos_button_id = str(uuid4())

                # Mapear los identificadores a los File IDs
                callback_data_map[cbz_button_id] = cbz_file_id
                callback_data_map[pdf_button_id] = pdf_file_id
                callback_data_map[fotos_button_id] = cbz_file_id  # Para fotos, usamos el CBZ File ID

                # Crear botones Inline para opciones posteriores
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Descargar CBZ", callback_data=f"cbz|{cbz_button_id}"),
                        InlineKeyboardButton("Descargar PDF", callback_data=f"pdf|{pdf_button_id}")
                    ],
                    [InlineKeyboardButton("Ver Fotos", callback_data=f"fotos|{fotos_button_id}")]
                ])

                await message.reply("Opciones disponibles para los archivos:", reply_markup=keyboard)
        except Exception as e:
            await message.reply(f"Error al manejar archivos para el código {code}: {str(e)}")

        try:
            # Limpiar únicamente la carpeta temporal
            borrar_carpeta(random_folder_name, result.get("cbz_file"))
        except Exception as e:
            await message.reply(f"Error al limpiar carpeta para el código {code}: {str(e)}")

    # Borrar los mensajes enviados al administrador
    await client.delete_messages(MAIN_ADMIN, message_ids_to_delete)

async def manejar_opcion(client, callback_query):
    """
    Procesa las opciones seleccionadas usando File IDs.
    """
    data = callback_query.data.split('|')
    opcion = data[0]
    identificador = data[1]

    # Obtener los datos reales del diccionario
    datos_reales = callback_data_map.get(identificador)

    if not datos_reales:
        await callback_query.answer("La opción ya no es válida.", show_alert=True)
        return

    if opcion == "cbz":
        cbz_file_id = datos_reales
        await client.send_document(
            callback_query.message.chat.id,
            cbz_file_id,
            caption="Aquí está tu CBZ 📚"
        )
    elif opcion == "pdf":
        pdf_file_id = datos_reales
        await client.send_document(
            callback_query.message.chat.id,
            pdf_file_id,
            caption="Aquí está tu PDF 🖨️"
        )
    elif opcion == "fotos":
        cbz_file_id = datos_reales
        # Descargar el CBZ desde Telegram
        cbz_file_path = await client.download_media(cbz_file_id)
        extract_folder = cbz_file_path.replace(".cbz", "_photos")

        # Verificar si extract_folder es un archivo en lugar de un directorio
        if os.path.isfile(extract_folder):
            os.remove(extract_folder)

        # Crear el directorio si no existe
        os.makedirs(extract_folder, exist_ok=True)

        # Descomprimir el archivo CBZ
        with zipfile.ZipFile(cbz_file_path, 'r') as zipf:
            zipf.extractall(extract_folder)
        os.remove(cbz_file_path)  # Borrar el CBZ después de descomprimirlo

        # Enviar fotos en lotes de 10
        archivos = sorted([os.path.join(extract_folder, f) for f in os.listdir(extract_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        lote = 10
        for i in range(0, len(archivos), lote):
            grupo_fotos = [InputMediaPhoto(open(archivo, 'rb')) for archivo in archivos[i:i + lote]]
            await client.send_media_group(callback_query.message.chat.id, grupo_fotos)

        # Borrar las fotos después de enviarlas
        for archivo in archivos:
            os.remove(archivo)
        os.rmdir(extract_folder)

    await callback_query.answer("¡Opción procesada!")
