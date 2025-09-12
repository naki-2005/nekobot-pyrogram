import aiohttp
import asyncio
import json
import os
import requests
import shutil
import subprocess
import tempfile
import time
import unicodedata
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaPhoto

async def send_nhentai_results(message, client, arg_text):
    try:
        parts = arg_text.split()
        page = 1
        if '-p' in parts:
            try:
                p_index = parts.index('-p')
                page = int(parts[p_index + 1])
                parts = parts[:p_index]
            except (ValueError, IndexError):
                pass

        query = ' '.join(parts).strip()
        query_quoted = f'"{query}"'

        command = [
            'python3',
            'command/get_files/scrap_nh.py',
            '--search', query_quoted,
            '--page', str(page)
        ]

        result = subprocess.run(
            ' '.join(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )

        output = result.stdout
        start = output.find('[')
        end = output.rfind(']') + 1
        json_data = output[start:end]

        galleries = json.loads(json_data)
        if not galleries:
            await message.reply("No se encontraron resultados.")
            return

        for result in galleries[:25]:
            image_url = None
            image_data = None

            for link in result.get('image_links', []):
                try:
                    response = requests.get(link, timeout=10)
                    if response.status_code == 200:
                        image_data = response.content
                        image_url = link
                        break
                except Exception:
                    continue

            if not image_data:
                await message.reply(f"No se pudo descargar imagen para: {result['name']}")
                continue

            try:
                img = Image.open(BytesIO(image_data))
                if img.format == 'WEBP':
                    img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
            except Exception as e:
                await message.reply(f"Error procesando imagen: {e}")
                continue

            caption = (
                f"📚 *Título:* {result['name']}\n"
                f"📥 Puedes descargar este doujin usando el comando:\n"
                f"`/nh {result['code']`}"
            )

            try:
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=buffer,
                    caption=caption,
                    parse_mode='Markdown'
                )
            except Exception as e:
                await message.reply(f"Error enviando imagen: {e}")
                continue

            time.sleep(5)

    except Exception as e:
        await message.reply(f"Error general: {e}")
            
BASE_DIR = "vault_files/doujins"
os.makedirs(BASE_DIR, exist_ok=True)

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
    from command.get_files.hitomi import descargar_y_comprimir_hitomi
    from command.get_files.nh_selenium import scrape_nhentai
    from command.get_files.h3_links import obtener_titulo_y_imagenes as obtener_info_y_links_h3

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
    temp_uuid_dir = os.path.join(BASE_DIR, str(uuid.uuid4()))
    os.makedirs(temp_uuid_dir, exist_ok=True)

    try:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, url in enumerate(imagenes):
                ext = os.path.splitext(url)[1].lower()
                if ext not in [".jpg", ".jpeg", ".png"]:
                    ext = ".jpg"
                path = os.path.join(temp_uuid_dir, f"{idx+1:03d}{ext}")
                tasks.append(descargarimagen_async(session, url, path, referer))
            await asyncio.gather(*tasks)

        shutil.make_archive(nombrebase, 'zip', temp_uuid_dir)
        os.rename(f"{nombrebase}.zip", cbz_path)
        return cbz_path
    finally:
        shutil.rmtree(temp_uuid_dir, ignore_errors=True)
        
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
        async with session.get(url) as resp:
            resp.raise_for_status()
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)
    except Exception as e:
        print(f"❌ Error descargando imagen {url}: {e}")
        await asyncio.sleep(2)
        await descargarimagen_async(session, url, path)

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
        carpeta_temporal = os.path.join(BASE_DIR, str(uuid.uuid4()))
        os.makedirs(carpeta_temporal, exist_ok=True)

        imagenes = datos["imagenes"]
        if not imagenes:
            await safe_call(message.reply, f"❌ No se encontraron imágenes para {codigo}", reply_to_message_id=message.id)
            shutil.rmtree(carpeta_temporal, ignore_errors=True)
            continue

        try:
            previewpath = os.path.join(carpeta_temporal, f"{nombrebase}_preview.jpg")
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

        except Exception as e:
            await safe_call(message.reply, f"❌ No pude enviar la portada para {texto_titulo}: {e}", reply_to_message_id=message.id)
            shutil.rmtree(carpeta_temporal, ignore_errors=True)
            continue

        if operacion == "cover":
            shutil.rmtree(carpeta_temporal, ignore_errors=True)
            continue

        progresomsg = await safe_call(message.reply,
            f"📦 Procesando imágenes para {texto_titulo} ({len(imagenes)} páginas)...\nProgreso 0/{len(imagenes)}",
            reply_to_message_id=message.id
        )

        try:
            paths = []
            async with aiohttp.ClientSession() as session:
                tasks = []
                for idx, url in enumerate(imagenes):
                    ext = os.path.splitext(url)[1].lower()
                    if ext not in [".jpg", ".jpeg", ".png"]:
                        ext = ".jpg"
                    path = os.path.join(carpeta_temporal, f"{idx+1:03d}{ext}")
                    tasks.append(descargarimagen_async(session, url, path))
                    paths.append(path)
                
                for i, task in enumerate(asyncio.as_completed(tasks)):
                    await task
                    if (i + 1) % 5 == 0 or i + 1 == len(tasks):
                        await progresomsg.edit_text(
                            f"📦 Procesando imágenes para {texto_titulo} ({len(imagenes)} páginas)...\nProgreso {i+1}/{len(imagenes)}"
                        )

            finalimage_path = os.path.join("command", "spam.png")
            finalpage_path = os.path.join(carpeta_temporal, f"{len(paths)+1:03d}.png")
            shutil.copyfile(finalimage_path, finalpage_path)
            paths.append(finalpage_path)

            archivos = []

            if seleccion in ["cbz", "both"]:
                cbzbase = f"{nombrebase}"
                cbzpath = f"{cbzbase}.cbz"
                shutil.make_archive(cbzbase, 'zip', carpeta_temporal)
                os.rename(f"{cbzbase}.zip", cbzpath)
                archivos.append(cbzpath)

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
                except Exception as e:
                    await safe_call(message.reply, f"❌ Error al generar PDF para {texto_titulo}: {e}", reply_to_message_id=cover_message.id)

            for archivo in archivos:
                await safe_call(client.send_document,
                    chat_id=message.chat.id,
                    document=archivo,
                    caption=texto_titulo,
                    protect_content=proteger,
                    reply_to_message_id=cover_message.id
                )
                os.remove(archivo)

        except Exception as e:
            await safe_call(message.reply, f"❌ Error procesando {texto_titulo}: {e}", reply_to_message_id=cover_message.id)
        finally:
            shutil.rmtree(carpeta_temporal, ignore_errors=True)
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
