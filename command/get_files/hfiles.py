import os
import requests
from uuid import uuid4
from fpdf import FPDF
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import shutil
from command.get_files.hfiles import descargar_hentai

MAIN_ADMIN = os.getenv("MAIN_ADMIN")
callback_data_map = {}
operation_status = {}
default_selection_map = {}  # Diccionario para asociar default_selection con user_id

def convertir_a_png_con_compresion(image_path, output_dir):
    """Convierte imágenes de cualquier formato a PNG optimizado."""
    try:
        os.makedirs(output_dir, exist_ok=True)  # Crear la carpeta si no existe
        with Image.open(image_path) as img:
            nuevo_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(image_path))[0]}.png")
            img.save(nuevo_path, "PNG", optimize=True)  # Comprimir al máximo
            return nuevo_path
    except Exception as e:
        print(f"Error al convertir la imagen {image_path} a PNG: {e}")
        return None

def crear_pdf_desde_png(page_title, png_dir, output_path):
    """Crea un PDF usando las imágenes PNG en una carpeta."""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        for image_name in sorted(os.listdir(png_dir)):
            image_path = os.path.join(png_dir, image_name)
            if image_name.lower().endswith('.png'):
                pdf.add_page()
                pdf.image(image_path, x=10, y=10, w=190)
        pdf.output(output_path)
        return True
    except Exception as e:
        print(f"Error al crear el PDF: {e}")
        return False

def cambiar_default_selection(user_id, nueva_seleccion):
    """Cambia la selección predeterminada del usuario."""
    if nueva_seleccion not in [None, "PDF", "CBZ", "Both"]:
        raise ValueError("Selección inválida. Debe ser None, 'PDF', 'CBZ', o 'Both'.")
    default_selection_map[user_id] = nueva_seleccion

async def nh_combined_operation(client, message, codes, link_type, protect_content, user_id, operation_type="download"):
    if link_type not in ["nh", "3h"]:
        await message.reply("Tipo de enlace no válido. Use 'nh' o '3h'.")
        return

    # Configuración inicial del usuario
    user_default_selection = default_selection_map.get(user_id, None)

    # Restaurando base_url
    base_url = "nhentai.net/g" if link_type == "nh" else "3hentai.net/d"

    for code in codes:
        try:
            url = f"https://{base_url}/{code}/"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            await message.reply(f"Error con el código {code}: {str(e)}")
            continue

        try:
            result = descargar_hentai(url, code, base_url, operation_type, protect_content, "downloads")
            if not result:
                await message.reply(f"Error con el código {code}: La función descargar_hentai retornó 'None'.")
                continue
            if result.get("error"):
                await message.reply(f"Error con el código {code}: {result['error']}")
                continue

            caption = result.get("caption", "Contenido descargado")
            img_file = result.get("img_file")
            if not img_file:
                await message.reply(f"Error con el código {code}: Imagen no encontrada.")
                continue

            cbz_file_path = result.get("cbz_file")
            pdf_file_path = result.get("pdf_file")

            if not pdf_file_path:
                pdf_file_path = f"{result.get('caption', 'output')}.pdf"
                new_png_dir = "new_png"
                os.makedirs(new_png_dir, exist_ok=True)
                for image_name in os.listdir("downloads"):
                    image_path = os.path.join("downloads", image_name)
                    convertir_a_png_con_compresion(image_path, new_png_dir)
                pdf_creado = crear_pdf_desde_png(result.get("caption", "output"), new_png_dir, pdf_file_path)
                if not pdf_creado:
                    await message.reply(f"Error al generar el PDF para el código {code}.")
                    continue

            if user_default_selection:
                if user_default_selection in ["Both", "CBZ"] and cbz_file_path:
                    await client.send_document(message.chat.id, cbz_file_path, caption="Aquí está tu CBZ 📚", protect_content=protect_content)
                if user_default_selection in ["Both", "PDF"] and pdf_file_path:
                    await client.send_document(message.chat.id, pdf_file_path, caption="Aquí está tu PDF 🖨️", protect_content=protect_content)

                await message.reply_photo(photo=img_file, caption=caption)  # Enviar la foto
            else:
                # Enviar archivo al administrador y obtener file_id
                cbz_file_id = None
                pdf_file_id = None

                if cbz_file_path:
                    cbz_message = await client.send_document(MAIN_ADMIN, cbz_file_path)
                    cbz_file_id = cbz_message.document.file_id
                    await cbz_message.delete()  # Borrar archivo del chat del admin
                if pdf_file_path:
                    pdf_message = await client.send_document(MAIN_ADMIN, pdf_file_path)
                    pdf_file_id = pdf_message.document.file_id
                    await pdf_message.delete()  # Borrar archivo del chat del admin

                # Crear botones para descargar desde file_id
                buttons = []
                if cbz_file_id:
                    cbz_button_id = str(uuid4())
                    callback_data_map[cbz_button_id] = cbz_file_id
                    operation_status[cbz_button_id] = False
                    buttons.append(InlineKeyboardButton("Descargar CBZ", callback_data=f"cbz|{cbz_button_id}"))
                if pdf_file_id:
                    pdf_button_id = str(uuid4())
                    callback_data_map[pdf_button_id] = pdf_file_id
                    operation_status[pdf_button_id] = False
                    buttons.append(InlineKeyboardButton("Descargar PDF", callback_data=f"pdf|{pdf_button_id}"))

                keyboard = InlineKeyboardMarkup([buttons])

                # Enviar imagen y botones al usuario
                await message.reply_photo(photo=img_file, caption=caption, reply_markup=keyboard)

            # Limpieza de archivos
            if cbz_file_path and os.path.exists(cbz_file_path):
                os.remove(cbz_file_path)
            if pdf_file_path and os.path.exists(pdf_file_path):
                os.remove(pdf_file_path)
            if os.path.exists("downloads"):
                shutil.rmtree("downloads")

        except Exception as e:
            await message.reply(f"Error al manejar archivos para el código {code}: {str(e)}")
