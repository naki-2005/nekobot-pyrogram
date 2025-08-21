import os
import re
import tempfile
import shutil
import subprocess
import aiohttp
import asyncio
from PIL import Image
from pyrogram.types import InputMediaPhoto
from pyrogram.errors import FloodWait

defaultselectionmap = {}

def cambiar_default_selection(userid, nuevaseleccion):
    opcionesvalidas = [None, "pdf", "cbz", "both"]
    if nuevaseleccion is not None:
        nuevaseleccion = nuevaseleccion.lower()
    if nuevaseleccion not in opcionesvalidas:
        raise ValueError("Seleccion invalida: debe ser None, pdf, cbz o both")
    defaultselectionmap[userid] = nuevaseleccion

import unicodedata

def limpiarnombre(nombre):
    nombre = nombre.replace('\n', ' ').strip()
    nombre = unicodedata.normalize('NFC', nombre)
    return re.sub(r'[^a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ ]', '', nombre)

async def descargarimagen_async(session, url, path):
    try:
        async with session.get(url, timeout=10) as resp:
            resp.raise_for_status()
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)
    except Exception:
        pass

from command.get_files.nh_links import obtener_info_y_links
from command.get_files.h3_links import obtener_titulo_y_imagenes as obtener_info_y_links_h3

def obtenerporcli(codigo, tipo, cover):
    try:
        if tipo == "nh":
            datos = obtener_info_y_links(codigo, cover=cover)
        else:
            datos = obtener_info_y_links_h3(codigo, cover=cover)
        texto = datos.get("texto", "").strip()
        imagenes = datos.get("imagenes", [])
        return {"texto": texto, "imagenes": imagenes}
    except Exception as e:
        print(f"❌ Error ejecutando función de extracción para {codigo}:", e)
        return {"texto": "", "imagenes": []}

# Funciones tolerantes a FloodWait
async def safe_call(func, *args, **kwargs):
    while True:
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            print(f"⏳ Esperando {e.value} seg para continuar")
            await asyncio.sleep(e.value)

async def nh_combined_operation(client, message, codigos, tipo, proteger, userid, operacion):
    seleccion = defaultselectionmap.get(userid, "cbz")
    MAX_FILENAME_LEN = 100

    for codigo in codigos:
        datos = obtenerporcli(codigo, tipo, cover=(operacion == "cover"))
        texto_original = datos.get("texto", "").strip()
        texto_titulo = f"{codigo} {texto_original}"
        nombrelimpio = limpiarnombre(texto_original)
        nombrebase = f"{codigo}_{nombrelimpio}" if nombrelimpio else f"{tipo}_{codigo}"
        if len(nombrebase) > MAX_FILENAME_LEN:
            nombrebase = nombrebase[:MAX_FILENAME_LEN].rstrip("_")

        imagenes = datos["imagenes"]
        if not imagenes:
            await safe_call(message.reply, f"❌ No se encontraron imágenes para {codigo}")
            continue

        try:
            previewpath = f"{nombrebase}_preview.jpg"
            async with aiohttp.ClientSession() as session:
                await descargarimagen_async(session, imagenes[0], previewpath)

            await safe_call(client.send_photo,
                chat_id=message.chat.id,
                photo=previewpath,
                caption=f"{texto_titulo} Número de páginas: {len(imagenes)}",
                protect_content=proteger
            )
            os.remove(previewpath)

        except Exception:
            await safe_call(message.reply, f"❌ No pude enviar la portada para {texto_titulo}")

        if operacion == "cover":
            continue

        progresomsg = await safe_call(message.reply,
            f"📦 Procesando imágenes para {texto_titulo} ({len(imagenes)} páginas)...\nProgreso 0/{len(imagenes)}"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            async with aiohttp.ClientSession() as session:
                tasks = []
                for idx, url in enumerate(imagenes):
                    ext = os.path.splitext(url)[1].lower()
                    if ext not in [".jpg", ".jpeg", ".png"]:
                        ext = ".jpg"
                    path = os.path.join(tmpdir, f"{idx+1:03d}{ext}")
                    tasks.append(descargarimagen_async(session, url, path))
                    paths.append(path)
                    if (idx + 1) % 5 == 0 or (idx + 1) == len(imagenes):
                        await safe_call(progresomsg.edit_text,
                            f"📦 Procesando imágenes para {texto_titulo} ({len(imagenes)} páginas)...\nProgreso {idx + 1}/{len(imagenes)}"
                        )
                await asyncio.gather(*tasks)

            if seleccion is None:
                for i in range(0, len(paths), 10):
                    grupo = paths[i:i+10]
                    media_group = [InputMediaPhoto(media=path) for path in grupo]
                    try:
                        await safe_call(client.send_media_group,
                            chat_id=message.chat.id,
                            media=media_group
                        )
                    except Exception as e:
                        await safe_call(message.reply, f"❌ Error al enviar grupo de imágenes: {type(e).__name__}: {e}")
            else:
                finalimage_path = os.path.join("command", "spam.png")
                finalpage_path = os.path.join(tmpdir, f"{len(paths)+1:03d}.png")
                shutil.copyfile(finalimage_path, finalpage_path)
                paths.append(finalpage_path)

                archivos = []

                if seleccion in ["cbz", "both"]:
                    cbzbase = f"{nombrebase}_cbz"
                    cbzpath = f"{cbzbase}.cbz"
                    shutil.make_archive(cbzbase, 'zip', tmpdir)
                    os.rename(f"{cbzbase}.zip", cbzpath)
                    archivos.append(cbzpath)

                if seleccion in ["pdf", "both"]:
                    pdfpath = f"{nombrebase}_pdf.pdf"
                    try:
                        mainimages = []
                        for path in paths:
                            try:
                                with Image.open(path) as im:
                                    mainimages.append(im.convert("RGB"))
                            except Exception:
                                continue
                        if mainimages:
                            mainimages[0].save(pdfpath, save_all=True, append_images=mainimages[1:])
                            archivos.append(pdfpath)
                    except Exception:
                        await safe_call(message.reply, f"❌ Error al generar PDF para {texto_titulo}")

                for archivo in archivos:
                    await safe_call(client.send_document,
                        chat_id=message.chat.id,
                        document=archivo,
                        caption=texto_titulo,
                        protect_content=proteger
                    )
                    os.remove(archivo)

        await safe_call(progresomsg.delete)

async def nh_combined_operation_txt(client, message, tipo, proteger, userid, operacion):
    if not message.reply_to_message or not message.reply_to_message.document:
        await safe_call(message.reply, "❌ Debes responder a un archivo .txt")
        return

    doc = message.reply_to_message.document
    if not doc.file_name.lower().endswith(".txt"):
        await safe_call(client.download_media, doc.file_id, file_name="temp_invalid")
        os.remove("temp_invalid")
        await safe_call(message.reply, "❌ Usar en un archivo txt")
        return

    filepath = await safe_call(client.download_media, doc.file_id, file_name="temp_input.txt")
    mensaje_txt = message.reply_to_message

    while True:
        with open(filepath, "r", encoding="utf-8") as f:
            contenido = f.read().strip()

        if not contenido:
            os.remove(filepath)
            try: await safe_call(mensaje_txt.delete)
            except: pass
            await safe_call(message.reply, "✅ Descarga terminada")
            return

        if not all(c in "0123456789," for c in contenido):
            os.remove(filepath)
            try: await safe_call(mensaje_txt.delete)
            except: pass
            await safe_call(message.reply, "❌ Estructura incorrecta")
            return

        codigos = contenido.split(",")
        primer_codigo = codigos[0]
        siguientes = codigos[1:]

        await nh_combined_operation(client, message, [primer_codigo], tipo, proteger, userid, operacion)

        os.remove(filepath)
        try: await safe_call(mensaje_txt.delete)
        except: pass

        if siguientes:
            nuevo_path = "temp_next.txt"
            with open(nuevo_path, "w", encoding="utf-8") as f:
                f.write(",".join(siguientes))

            mensaje_txt = await safe_call(client.send_document,
                chat_id=message.chat.id,
                document=nuevo_path,
                caption=f"💻 Pendientes: {len(siguientes)}",
                protect_content=proteger
            )

            filepath = nuevo_path
        else:
            await safe_call(message.reply, "✅ Descarga terminada")
            return
