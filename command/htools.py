import aiohttp
import asyncio
import json
import os
import requests
import shutil
import subprocess
import tempfile
import time
import re
import unicodedata
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaPhoto
from command.get_files.scrap_nh import scrape_nhentai_with_selenium

from command.get_files.search_3h import scrape_3hentai_search

async def api_search_3hentai(search_term, page=1):
    try:
        result_data = scrape_3hentai_search(search_term=search_term, page=page)
        galleries = []
        
        for key, result in result_data.get('resultados', {}).items():
            galleries.append({
                'name': result['titulo'],
                'code': result['codigo'],
                'image_links': [result['imagen']]
            })
        
        return {
            'results': galleries,
            'total_pages': result_data.get('total_paginas', 1),
            'total_results': result_data.get('total_resultados', 0)
        }
    except Exception as e:
        print(f"Error en búsqueda 3hentai API: {e}")
        return {'results': [], 'total_pages': 1, 'total_results': 0}

async def send_3hentai_results(message, client, arg_text):
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

        result_data = await api_search_3hentai(search_term=query, page=page)
        galleries = result_data.get('results', [])
        
        if not galleries:
            await message.reply("No se encontraron resultados.")
            return

        for result in galleries[:25]:
            image_data = None

            for link in result.get('image_links', []):
                try:
                    response = requests.get(link, timeout=10)
                    if response.status_code == 200:
                        image_data = response.content
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
                f"`/3h {result['code']}`"
            )

            try:
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=buffer,
                    caption=caption
                )
            except Exception as e:
                await message.reply(f"Error enviando imagen: {e}")
                continue

            time.sleep(3)

    except Exception as e:
        await message.reply(f"Error general: {e}")
        
async def api_search_nhentai(search_term, page=1):
    try:
        galleries = scrape_nhentai_with_selenium(search_term=search_term, page=page)
        return galleries
    except Exception as e:
        print(f"Error en búsqueda API: {e}")
        return []

async def api_download_nhentai(codigo):
    try:
        cbz_path = await crear_cbz_desde_fuente(codigo, "nh")
        return cbz_path
    except Exception as e:
        print(f"Error en descarga API: {e}")
        raise
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

        result_data = scrape_nhentai_with_selenium(search_term=query, page=page)
        galleries = result_data.get('results', [])
        
        if not galleries:
            await message.reply("No se encontraron resultados.")
            return

        for result in galleries[:25]:
            image_data = None

            for link in result.get('image_links', []):
                try:
                    response = requests.get(link, timeout=10)
                    if response.status_code == 200:
                        image_data = response.content
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
                f"`/nh {result['code']}`"
            )

            try:
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=buffer,
                    caption=caption
                )
            except Exception as e:
                await message.reply(f"Error enviando imagen: {e}")
                continue

            time.sleep(3)

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
        result = scrape_nhentai(codigo)
        title = result["title"]
        imagenes = result["links"]
        tags = result["tags"]
        datos = {"texto": title, "imagenes": imagenes, "tags": tags}
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
    opcionesvalidas = [None, "pdf", "cbz", "both", "pics"]
    if nuevaseleccion is not None:
        nuevaseleccion = nuevaseleccion.lower()
    if nuevaseleccion not in opcionesvalidas:
        raise ValueError("Seleccion invalida: debe ser None, pdf, cbz, both o pics")
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

async def descargar_imagen_con_extensiones_alternativas(session, base_url, path, referer):
    extensiones = ['.jpg', '.png', '.webp', '.jpeg']
    
    for ext in extensiones:
        try:
            url = base_url + ext
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": referer
            }
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    with open(path, 'wb') as f:
                        f.write(content)
                    return True
        except Exception:
            continue
    
    return False

from command.get_files.nh_selenium import scrape_nhentai
from command.get_files.h3_links import obtener_titulo_y_imagenes as obtener_info_y_links_h3

def obtenerporcli(codigo, tipo, cover):
    try:
        if tipo == "hito":
            return {"texto": "Procesando Hitomi.la", "imagenes": [], "tags": {}}
        elif tipo == "nh":
            result = scrape_nhentai(codigo)
            title = result["title"]
            imagenes = result["links"]
            tags = result["tags"]
            
            if imagenes:
                base_url_pattern = re.search(r'(https://i\d+\.nhentai\.net/galleries/\d+/)', imagenes[0])
                if base_url_pattern:
                    base_url = base_url_pattern.group(1)
                    total_pages = len(imagenes)
                    
                    nuevas_imagenes = []
                    for i in range(1, total_pages + 1):
                        nuevas_imagenes.append(f"{base_url}{i}.jpg")
                    
                    imagenes = nuevas_imagenes
            
            datos = {"texto": title, "imagenes": imagenes, "tags": tags}
        else:
            datos = obtener_info_y_links_h3(codigo, cover=cover)
        texto = datos.get("texto", "").strip()
        imagenes = datos.get("imagenes", [])
        tags = datos.get("tags", {})
        return {"texto": texto, "imagenes": imagenes, "tags": tags}
    except Exception as e:
        print(f"❌ Error ejecutando función de extracción para {codigo}:", e)
        return {"texto": "", "imagenes": [], "tags": {}}

def limpiarnombre(nombre: str) -> str:
    nombre = nombre.replace('\n', ' ').strip()
    nombre = unicodedata.normalize('NFC', nombre)
    return re.sub(r'[^a-zA-Z0-9ñÑáéíóúÁÉÍÓÚ ]', '', nombre)

async def enviar_grupo_imagenes(client, chat_id, paths, caption, proteger, reply_to_message_id):
    grupos = [paths[i:i + 10] for i in range(0, len(paths), 10)]
    
    for grupo in grupos:
        media_grupo = []
        for path in grupo:
            media_grupo.append(InputMediaPhoto(media=path))
        
        if media_grupo:
            await safe_call(client.send_media_group,
                chat_id=chat_id,
                media=media_grupo,
                protect_content=proteger,
                reply_to_message_id=reply_to_message_id
            )
            
async def nh_combined_operation(client, message, codigos, tipo, proteger, userid, operacion, int_lvl):
    seleccion = defaultselectionmap.get(userid, "cbz")
    EXTENSIONES = {"cbz": ".cbz", "pdf": ".pdf", "both": ".cbz", "pics": ""}
    extension = EXTENSIONES.get(seleccion, ".cbz")
    MAX_FILENAME_LEN = 63

    for codigo in codigos:
        if tipo == "hito":
            try:
                cbz_path = await crear_cbz_desde_fuente(codigo, tipo)
                texto_titulo = os.path.basename(cbz_path).replace('.cbz', '')
                
                if seleccion == "cbz" or seleccion == "both":
                    await safe_call(client.send_document,
                        chat_id=message.chat.id,
                        document=cbz_path,
                        caption=texto_titulo,
                        protect_content=proteger,
                        reply_to_message_id=message.id
                    )
                
                if seleccion == "pdf" or seleccion == "both" or seleccion == "pics":
                    carpeta_temporal = os.path.join(BASE_DIR, str(uuid.uuid4()))
                    os.makedirs(carpeta_temporal, exist_ok=True)
                    
                    try:
                        with zipfile.ZipFile(cbz_path, 'r') as zip_ref:
                            zip_ref.extractall(carpeta_temporal)
                        
                        paths = []
                        for root, dirs, files in os.walk(carpeta_temporal):
                            for file in sorted(files):
                                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                                    paths.append(os.path.join(root, file))
                        
                        paths.sort()
                        
                        if seleccion == "pdf" or seleccion == "both":
                            pdfpath = f"{texto_titulo}.pdf"
                            try:
                                mainimages = []
                                for path in paths:
                                    try:
                                        with Image.open(path) as im:
                                            if im.mode != 'RGB':
                                                im = im.convert('RGB')
                                            mainimages.append(im)
                                    except Exception:
                                        continue
                                if mainimages:
                                    mainimages[0].save(pdfpath, save_all=True, append_images=mainimages[1:])
                                    await safe_call(client.send_document,
                                        chat_id=message.chat.id,
                                        document=pdfpath,
                                        caption=texto_titulo,
                                        protect_content=proteger,
                                        reply_to_message_id=message.id
                                    )
                                    os.remove(pdfpath)
                            except Exception as e:
                                await safe_call(message.reply, f"❌ Error al generar PDF para {texto_titulo}: {e}", reply_to_message_id=message.id)
                        
                        if seleccion == "pics":
                            await enviar_grupo_imagenes(client, message.chat.id, paths, texto_titulo, proteger, message.id)
                    
                    finally:
                        shutil.rmtree(carpeta_temporal, ignore_errors=True)
                
                os.remove(cbz_path)
                continue
                
            except Exception as e:
                await safe_call(message.reply, f"❌ Error con Hitomi.la: {e}", reply_to_message_id=message.id)
                continue

        datos = obtenerporcli(codigo, tipo, cover=(operacion == "cover"))
        texto_original = datos.get("texto", "").strip()
        tags = datos.get("tags", {})
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
            
            if tipo == "nh":
                base_url_pattern = re.search(r'(https://i\d+\.nhentai\.net/galleries/\d+/)', imagenes[0])
                if base_url_pattern:
                    base_url = base_url_pattern.group(1)
                    referer = "https://nhentai.net/"
                    success = await descargar_imagen_con_extensiones_alternativas(
                        aiohttp.ClientSession(), base_url + "1", previewpath, referer
                    )
                    if not success:
                        async with aiohttp.ClientSession() as session:
                            await descargarimagen_async(session, imagenes[0], previewpath)
                else:
                    async with aiohttp.ClientSession() as session:
                        await descargarimagen_async(session, imagenes[0], previewpath)
            else:
                async with aiohttp.ClientSession() as session:
                    await descargarimagen_async(session, imagenes[0], previewpath)

            caption_lines = [f"{texto_titulo} Número de páginas: {len(imagenes)}"]
            
            if tags:
                caption_lines.append("\n🏷️ **Tags:**")
                for category, tag_list in tags.items():
                    if tag_list:
                        caption_lines.append(f"• **{category}:** {', '.join(tag_list)}")

            caption = "\n".join(caption_lines)

            cover_message = await safe_call(client.send_photo,
                chat_id=message.chat.id,
                photo=previewpath,
                caption=caption,
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
                
                if tipo == "nh" and imagenes:
                    base_url_pattern = re.search(r'(https://i\d+\.nhentai\.net/galleries/\d+/)', imagenes[0])
                    if base_url_pattern:
                        base_url = base_url_pattern.group(1)
                        referer = "https://nhentai.net/"
                        
                        for idx in range(len(imagenes)):
                            page_num = idx + 1
                            path = os.path.join(carpeta_temporal, f"{page_num:03d}.jpg")
                            task = asyncio.create_task(
                                descargar_imagen_con_extensiones_alternativas(
                                    session, base_url + str(page_num), path, referer
                                )
                            )
                            tasks.append((task, path))
                    else:
                        for idx, url in enumerate(imagenes):
                            ext = os.path.splitext(url)[1].lower()
                            if ext not in [".jpg", ".jpeg", ".png"]:
                                ext = ".jpg"
                            path = os.path.join(carpeta_temporal, f"{idx+1:03d}{ext}")
                            task = asyncio.create_task(descargarimagen_async(session, url, path))
                            tasks.append((task, path))
                else:
                    for idx, url in enumerate(imagenes):
                        ext = os.path.splitext(url)[1].lower()
                        if ext not in [".jpg", ".jpeg", ".png"]:
                            ext = ".jpg"
                        path = os.path.join(carpeta_temporal, f"{idx+1:03d}{ext}")
                        task = asyncio.create_task(descargarimagen_async(session, url, path))
                        tasks.append((task, path))
                
                completed = 0
                for task, path in tasks:
                    success = await task
                    if success:
                        paths.append(path)
                    completed += 1
                    if completed % 5 == 0 or completed == len(tasks):
                        await progresomsg.edit_text(
                            f"📦 Procesando imágenes para {texto_titulo} ({len(imagenes)} páginas)...\nProgreso {completed}/{len(imagenes)}"
                        )

            if int_lvl < 5:
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

            if seleccion == "pics":
                await enviar_grupo_imagenes(client, message.chat.id, paths, texto_titulo, proteger, cover_message.id)

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

async def nh_combined_operation_txt(client, message, tipo, proteger, userid, operacion, int_lvl):
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

        await nh_combined_operation(client, message, [primer_codigo], tipo, proteger, userid, operacion, int_lvl)

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
