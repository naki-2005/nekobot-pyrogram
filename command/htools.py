import os
import re
import tempfile
import shutil
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
            previewpath = f"{nombrebase} preview.jpg"
            async with aiohttp.ClientSession() as session:
                await descargarimagen_async(session, imagenes[0], previewpath)

            await client.send_photo(
                chat_id=message.chat.id,
                photo=previewpath,
                caption=f"{nombrebase} Número de páginas: {len(imagenes)}",
                protect_content=proteger
            )
            os.remove(previewpath)

        except Exception:
            await message.reply(f"❌ No pude enviar la portada para {nombrebase}")

        if operacion == "cover":
            continue

        progresomsg = await message.reply(
            f"📦 Procesando imágenes para {nombrebase} ({len(imagenes)} páginas)...\nProgreso 0/{len(imagenes)}"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            async with aiohttp.ClientSession() as session:
                tasks = []
                for idx, url in enumerate(imagenes):
                    ext = os.path.splitext(url)[1].lower()
                    if ext not in [".jpg", ".jpeg", ".png"]: ext = ".jpg"
                    path = os.path.join(tmpdir, f"{idx+1:03d}{ext}")
                    tasks.append(descargarimagen_async(session, url, path))
                    paths.append(path)
                    if (idx + 1) % 5 == 0 or (idx + 1) == len(imagenes):
                        try:
                            await progresomsg.edit_text(
                                f"📦 Procesando imágenes para {nombrebase} ({len(imagenes)} páginas)...\nProgreso {idx + 1}/{len(imagenes)}"
                            )
                        except Exception:
                            pass
                await asyncio.gather(*tasks)

            if seleccion is None:
                # Enviar como grupos de fotos
                for i in range(0, len(paths), 10):
                    grupo = paths[i:i+10]
                    media_group = [InputMediaPhoto(media=path) for path in grupo]
                    try:
                        await client.send_media_group(
                            chat_id=message.chat.id,
                            media=media_group
                        )
                    except Exception as e:
                        await message.reply(f"❌ Error al enviar grupo de imágenes: {type(e).__name__}: {e}")
            else:
                # Añadir página final
                finalimage_path = os.path.join("command", "spam.png")
                finalpage_path = os.path.join(tmpdir, f"{len(paths)+1:03d}.png")
                shutil.copyfile(finalimage_path, finalpage_path)
                paths.append(finalpage_path)

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
