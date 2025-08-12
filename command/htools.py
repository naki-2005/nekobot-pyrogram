import os
import re
import tempfile
import shutil
import requests
import subprocess
import aiohttp
import asyncio
from PIL import Image
from pyrogram.types import InputMediaPhoto

defaultselectionmap = {}

def cambiar_default_selection(userid, nuevaseleccion):
    opcionesvalidas = [None, "pdf", "cbz", "both"]
    if nuevaseleccion is not None:
        nuevaseleccion = nuevaseleccion.lower()
    if nuevaseleccion not in opcionesvalidas:
        raise ValueError("Seleccion invalida Debe ser None pdf cbz o both")
    defaultselectionmap[userid] = nuevaseleccion

def limpiarnombre(nombre):
    return re.sub(r'[^a-zA-Z0-9 ]', '', nombre.replace('\n', ' ')).strip()

async def descargarimagen_async(session, url, path):
    try:
        async with session.get(url, timeout=10) as resp:
            resp.raise_for_status()
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)
    except Exception:
        pass

async def convertir_a_webp(raw_path, final_path):
    try:
        with Image.open(raw_path) as img:
            img.convert("RGB").save(final_path, "WEBP", quality=90, method=6)
        os.remove(raw_path)
    except Exception:
        shutil.copyfile(raw_path, final_path)
        os.remove(raw_path)

async def convertir_a_jpeg(raw_path, final_path):
    try:
        with Image.open(raw_path) as img:
            img.convert("RGB").save(final_path, "JPEG", quality=85, optimize=True)
        os.remove(raw_path)
    except Exception:
        shutil.copyfile(raw_path, final_path)
        os.remove(raw_path)

def obtenerporcli(codigo, tipo, cover):
    script = "nh_links.py" if tipo == "nh" else "h3_links.py"
    path = os.path.join("command", "get_files", script)
    comando = ["python3", path, "-C", codigo]
    if cover:
        comando.append("--cover")

    try:
        result = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1200)
        salida = result.stdout.splitlines()
        texto = ""
        imagenes = []
        modotexto = False
        for linea in salida:
            if linea.strip().startswith("📄"):
                modotexto = True
            elif linea.strip().startswith("🖼️"):
                modotexto = False
            elif modotexto:
                texto += linea.strip() + " "
            elif linea.strip().startswith("http"):
                imagenes.append(linea.strip())
        return {"texto": texto.strip(), "imagenes": imagenes}
    except Exception as e:
        print("❌ Error ejecutando script externo:", e)
        return {"texto": "", "imagenes": []}

async def nh_combined_operation(client, message, codigos, tipo, proteger, userid, operacion):
    seleccion = defaultselectionmap.get(userid, "cbz")

    for codigo in codigos:
        datos = obtenerporcli(codigo, tipo, cover=(operacion == "cover"))
        nombrebase = limpiarnombre(datos["texto"]) or f"{tipo} {codigo}"
        imagenes = datos["imagenes"]

        if not imagenes:
            await message.reply(f"❌ No se encontraron imágenes para {codigo}")
            continue

        try:
            previewpath = f"{nombrebase} preview.png"
            async with aiohttp.ClientSession() as session:
                await descargarimagen_async(session, imagenes[0], previewpath)

            await client.send_photo(
                chat_id=message.chat.id,
                photo=previewpath,
                caption=f"{nombrebase} Número de páginas {len(imagenes)}",
                protect_content=proteger
            )
            os.remove(previewpath)

        except Exception:
            fallbackpath = f"{nombrebase} fallback.png"
            try:
                with Image.open(previewpath) as img:
                    img.convert("RGB").save(fallbackpath)
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=fallbackpath,
                    caption=f"{nombrebase} Número de páginas {len(imagenes)}",
                    protect_content=proteger
                )
                os.remove(fallbackpath)
                os.remove(previewpath)

            except Exception:
                try:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=previewpath,
                        caption=f"{nombrebase} Número de páginas {len(imagenes)}",
                        protect_content=proteger
                    )
                    os.remove(previewpath)
                except Exception as e:
                    await message.reply(f"❌ No pude enviar la portada. {type(e).__name__}: {e}")

        if operacion == "cover":
            continue

        progresomsg = await message.reply(
            f"📦 Procesando imágenes para {nombrebase} ({len(imagenes)} páginas)...\nProgreso 0/{len(imagenes)}"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_paths = []
            final_paths = []
            async with aiohttp.ClientSession() as session:
                tasks = []
                for idx, url in enumerate(imagenes):
                    ext = os.path.splitext(url)[1].lower()
                    if ext not in [".jpg", ".jpeg", ".png", ".webp"]: ext = ".jpg"
                    raw_path = os.path.join(tmpdir, f"{idx+1:03d}_raw{ext}")
                    raw_paths.append(raw_path)
                    tasks.append(descargarimagen_async(session, url, raw_path))
                    if (idx + 1) % 5 == 0 or (idx + 1) == len(imagenes):
                        try:
                            await progresomsg.edit_text(
                                f"📦 Procesando imágenes para {nombrebase} ({len(imagenes)} páginas)...\nProgreso {idx + 1}/{len(imagenes)}"
                            )
                        except Exception:
                            pass
                await asyncio.gather(*tasks)

            if seleccion is None:
                # Convertir a JPEG para enviar como fotos
                for idx, raw in enumerate(raw_paths):
                    final_path = os.path.join(tmpdir, f"{idx+1:03d}.jpg")
                    await convertir_a_jpeg(raw, final_path)
                    final_paths.append(final_path)

                # Enviar en grupos de 10
                for i in range(0, len(final_paths), 10):
                    grupo = final_paths[i:i+10]
                    media_group = [InputMediaPhoto(media=path) for path in grupo]
                    try:
                        await client.send_media_group(
                            chat_id=message.chat.id,
                            media=media_group
                        )
                    except Exception as e:
                        await message.reply(f"❌ Error al enviar grupo de imágenes: {type(e).__name__}: {e}")
            else:
                # Convertir a WebP para cbz/pdf
                for idx, raw in enumerate(raw_paths):
                    final_path = os.path.join(tmpdir, f"{idx+1:03d}.webp")
                    await convertir_a_webp(raw, final_path)
                    final_paths.append(final_path)

                finalimage_path = os.path.join("command", "spam.png")
                finalpage_path = os.path.join(tmpdir, f"{len(final_paths)+1:03d}.webp")
                shutil.copyfile(finalimage_path, finalpage_path)
                final_paths.append(finalpage_path)

                archivos = []

                if seleccion in ["cbz", "both"]:
                    cbzpath = f"{nombrebase}.cbz"
                    shutil.make_archive(nombrebase, 'zip', tmpdir)
                    os.rename(f"{nombrebase}.zip", cbzpath)
                    archivos.append(cbzpath)

                if seleccion in ["pdf", "both"]:
                    pdfpath = f"{nombrebase}.pdf"
                    try:
                        mainimages = []
                        for path in final_paths:
                            try:
                                with Image.open(path) as im:
                                    mainimages.append(im.convert("RGB"))
                            except Exception:
                                continue
                        if mainimages:
                            mainimages[0].save(pdfpath, save_all=True, append_images=mainimages[1:])
                            archivos.append(pdfpath)
                    except Exception:
                        await message.reply(f"❌ Error al generar PDF para {nombrebase}")

                for archivo in archivos:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=archivo,
                        caption=nombrebase,
                        protect_content=proteger
                    )
                    os.remove(archivo)

        try:
            await progresomsg.delete()
        except Exception:
            pass
