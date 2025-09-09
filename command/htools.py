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
import unicodedata
from datetime import datetime

async def safe_call(func, *args, **kwargs):
    while True:
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            print(f"⏳ Esperando {e.value} seg para continuar")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"❌ Error inesperado en {func.__name__}: {type(e).__name__}: {e}")
            raise

async def crear_cbz_desde_fuente(codigo: str, tipo: str) -> str:
    import os, shutil, tempfile, unicodedata, re, aiohttp, asyncio
    from PIL import Image
    from command.get_files.hitomi import descargar_y_comprimir_hitomi
    from command.get_files.nh_selenium import scrape_nhentai
    from command.get_files.h3_links import obtener_titulo_y_imagenes as obtener_info_y_links_h3

    BASE_DIR = "vault_files"
    os.makedirs(BASE_DIR, exist_ok=True)

    def limpiarnombre(nombre: str) -> str:
        nombre = nombre.replace('\n', ' ').strip()
        nombre = unicodedata.normalize('NFC', nombre)
        return re.sub(r'[^a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ ]', '', nombre)

    async def descargarimagen_async(session, url, path, referer):
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": referer
        }
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                with open(path, 'wb') as f:
                    f.write(await resp.read())

    if tipo == "hito":
        cbz_path = descargar_y_comprimir_hitomi(codigo)
        final_path = os.path.join(BASE_DIR, os.path.basename(cbz_path))
        shutil.move(cbz_path, final_path)
        return final_path

    if tipo == "nh":
        title, imagenes = scrape_nhentai(codigo)
        datos = {"texto": title, "imagenes": imagenes}
        referer = "https://nhentai.net/"
    else:
        datos = obtener_info_y_links_h3(codigo, cover=False)
        referer = "https://3hentai.net/"

    texto = datos.get("texto", "").strip()
    imagenes = datos.get("imagenes", [])
    if not imagenes:
        raise ValueError(f"No se encontraron imágenes para {codigo}")

    nombrelimpio = limpiarnombre(texto)
    nombrebase = f"{codigo} {nombrelimpio}" if nombrelimpio else f"{tipo} {codigo}"
    nombrebase = nombrebase.strip()
    cbz_filename = f"{nombrebase}.cbz"
    cbz_path = os.path.join(BASE_DIR, cbz_filename)

    with tempfile.TemporaryDirectory() as tmpdir:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, url in enumerate(imagenes):
                ext = os.path.splitext(url)[1].lower()
                if ext not in [".jpg", ".jpeg", ".png"]:
                    ext = ".jpg"
                path = os.path.join(tmpdir, f"{idx+1:03d}{ext}")
                tasks.append(descargarimagen_async(session, url, path, referer))
            await asyncio.gather(*tasks)

        shutil.make_archive(nombrebase, 'zip', tmpdir)
        os.rename(f"{nombrebase}.zip", cbz_path)
        return cbz_path
        
defaultselectionmap = {}

def cambiar_default_selection(userid, nuevaseleccion):
    opcionesvalidas = [None, "pdf", "cbz", "both"]
    if nuevaseleccion is not None:
        nuevaseleccion = nuevaseleccion.lower()
    if nuevaseleccion not in opcionesvalidas:
        raise ValueError("Seleccion invalida: debe ser None, pdf, cbz o both")
    defaultselectionmap[userid] = nuevaseleccion

async def descargarimagen_async(session, url, path):
    try:
        async with session.get(url, timeout=10) as resp:
            resp.raise_for_status()
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)
    except Exception:
        pass

from command.get_files.nh_selenium import scrape_nhentai
from command.get_files.h3_links import obtener_titulo_y_imagenes as obtener_info_y_links_h3

def obtenerporcli(codigo, tipo, cover):
    try:
        if tipo == "hito":
            return {"texto": "Procesando Hitomi.la", "imagenes": []}
        elif tipo == "nh":
            title, imagenes = scrape_nhentai(codigo)
            datos = {"texto": title, "imagenes": imagenes}
        else:
            datos = obtener_info_y_links_h3(codigo, cover=cover)
        texto = datos.get("texto", "").strip()
        imagenes = datos.get("imagenes", [])
        return {"texto": texto, "imagenes": imagenes}
    except Exception as e:
        print(f"❌ Error ejecutando función de extracción para {codigo}:", e)
        return {"texto": "", "imagenes": []}

def limpiarnombre(nombre: str) -> str:
    nombre = nombre.replace('\n', ' ').strip()
    nombre = unicodedata.normalize('NFC', nombre)
    return re.sub(r'[^a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ ]', '', nombre)

async def nh_combined_operation(client, message, codigos, tipo, proteger, userid, operacion):
    seleccion = defaultselectionmap.get(userid, "cbz")
    EXTENSIONES = {"cbz": ".cbz", "pdf": ".pdf", "both": ".cbz"}
    extension = EXTENSIONES.get(seleccion, ".cbz")
    MAX_FILENAME_LEN = 63

    for codigo in codigos:
        if tipo == "hito":
            try:
                cbz_path = await crear_cbz_desde_fuente(codigo, tipo)
                texto_titulo = os.path.basename(cbz_path).replace('.cbz', '')
                
                await safe_call(client.send_document,
                    chat_id=message.chat.id,
                    document=cbz_path,
                    caption=texto_titulo,
                    protect_content=proteger,
                    reply_to_message_id=message.id
                )
                os.remove(cbz_path)
                continue
            except Exception as e:
                await safe_call(message.reply, f"❌ Error con Hitomi.la: {e}", reply_to_message_id=message.id)
                continue

        datos = obtenerporcli(codigo, tipo, cover=(operacion == "cover"))
        texto_original = datos.get("texto", "").strip()
        texto_titulo = f"{codigo} {texto_original}"
        nombrelimpio = limpiarnombre(texto_original)
        nombrebase = f"{codigo} {nombrelimpio}" if nombrelimpio else f"{tipo} {codigo}"
        nombrebase = nombrebase.strip()
        max_nombre_len = MAX_FILENAME_LEN - len(extension)
        if len(nombrebase) > max_nombre_len:
            nombrebase = nombrebase[:max_nombre_len].rstrip()

        nombrelimpio_completo = limpiarnombre(texto_original)
        carpeta_raiz = os.path.abspath(f"{codigo} - {nombrelimpio_completo}")

        imagenes = datos["imagenes"]
        if not imagenes:
            await safe_call(message.reply, f"❌ No se encontraron imágenes para {codigo}", reply_to_message_id=message.id)
            continue

        try:
            previewpath = f"{nombrebase}_preview.jpg"
            async with aiohttp.ClientSession() as session:
                await descargarimagen_async(session, imagenes[0], previewpath)

            cover_message = await safe_call(client.send_photo,
                chat_id=message.chat.id,
                photo=previewpath,
                caption=f"{texto_titulo} Número de páginas: {len(imagenes)}",
                protect_content=proteger,
                reply_to_message_id=message.id
            )
            os.remove(previewpath)

        except Exception:
            await safe_call(message.reply, f"❌ No pude enviar la portada para {texto_titulo}", reply_to_message_id=message.id)
            continue

        if operacion == "cover":
            continue

        progresomsg = await safe_call(message.reply,
            f"📦 Procesando imágenes para {texto_titulo} ({len(imagenes)} páginas)...\nProgreso 0/{len(imagenes)}",
            reply_to_message_id=message.id
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
                await asyncio.gather(*tasks)

            finalimage_path = os.path.join("command", "spam.png")
            finalpage_path = os.path.join(tmpdir, f"{len(paths)+1:03d}.png")
            shutil.copyfile(finalimage_path, finalpage_path)
            paths.append(finalpage_path)

            archivos = []

            if seleccion in ["cbz", "both"]:
                os.makedirs(carpeta_raiz, exist_ok=True)
                for path in paths:
                    shutil.move(path, os.path.join(carpeta_raiz, os.path.basename(path)))

                cbzbase = f"{nombrebase}"
                cbzpath = f"{cbzbase}.cbz"
                shutil.make_archive(cbzbase, 'zip', os.path.dirname(carpeta_raiz), os.path.basename(carpeta_raiz))
                os.rename(f"{cbzbase}.zip", cbzpath)
                archivos.append(cbzpath)

                for file in os.listdir(carpeta_raiz):
                    os.remove(os.path.join(carpeta_raiz, file))
                os.rmdir(carpeta_raiz)

            if seleccion in ["pdf", "both"]:
                pdfpath = f"{nombrebase}.pdf"
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
                    await safe_call(message.reply, f"❌ Error al generar PDF para {texto_titulo}", reply_to_message_id=cover_message.id)

            for archivo in archivos:
                await safe_call(client.send_document,
                    chat_id=message.chat.id,
                    document=archivo,
                    caption=texto_titulo,
                    protect_content=proteger,
                    reply_to_message_id=cover_message.id
                )
                os.remove(archivo)

        await safe_call(progresomsg.delete)

async def nh_combined_operation_txt(client, message, tipo, proteger, userid, operacion):
    if not message.reply_to_message or not message.reply_to_message.document:
        await safe_call(message.reply, "❌ Debes responder a un archivo .txt", reply_to_message_id=message.id)
        return

    doc = message.reply_to_message.document
    if not doc.file_name.lower().endswith(".txt"):
        await safe_call(client.download_media, doc.file_id, file_name="temp_invalid")
        os.remove("temp_invalid")
        await safe_call(message.reply, "❌ Usar en un archivo txt", reply_to_message_id=message.id)
        return

    filepath = await safe_call(client.download_media, doc.file_id, file_name="temp_input.txt")
    mensaje_txt = message.reply_to_message

    while True:
        with open(filepath, "r", encoding="utf-8") as f:
            if tipo == "hito":
                contenido = f.read().strip()
                urls = [line.strip() for line in contenido.split('\n') if line.strip()]
                codigos = urls
            else:
                contenido = f.read().strip()
                codigos = contenido.split(",")

        if not codigos:
            os.remove(filepath)
            try: await safe_call(mensaje_txt.delete)
            except: pass
            await safe_call(message.reply, "✅ Descarga terminada", reply_to_message_id=message.id)
            return

        if tipo != "hito" and not all(c in "0123456789," for c in contenido):
            os.remove(filepath)
            try: await safe_call(mensaje_txt.delete)
            except: pass
            await safe_call(message.reply, "❌ Estructura incorrecta", reply_to_message_id=message.id)
            return

        primer_codigo = codigos[0]
        siguientes = codigos[1:]

        await nh_combined_operation(client, message, [primer_codigo], tipo, proteger, userid, operacion)

        os.remove(filepath)
        try: await safe_call(mensaje_txt.delete)
        except: pass

        if siguientes:
            nuevo_path = "temp_next.txt"
            with open(nuevo_path, "w", encoding="utf-8") as f:
                if tipo == "hito":
                    f.write('\n'.join(siguientes))
                else:
                    f.write(",".join(siguientes))

            mensaje_txt = await safe_call(client.send_document,
                chat_id=message.chat.id,
                document=nuevo_path,
                caption=f"💻 Pendientes: {len(siguientes)}",
                protect_content=proteger,
                reply_to_message_id=message.id
            )

            filepath = nuevo_path
        else:            
            await safe_call(message.reply, "✅ Descarga terminada", reply_to_message_id=message.id)
            return
