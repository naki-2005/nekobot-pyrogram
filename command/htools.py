import os
import re
import tempfile
import shutil
import requests
import threading
import subprocess
from PIL import Image

defaultselectionmap = {}

def cambiardefaultselection(userid, nuevaseleccion):
    opcionesvalidas = [None, "pdf", "cbz", "both"]
    if nuevaseleccion is not None:
        nuevaseleccion = nuevaseleccion.lower()
    if nuevaseleccion not in opcionesvalidas:
        raise ValueError("Seleccion invalida Debe ser None pdf cbz o both")
    defaultselectionmap[userid] = nuevaseleccion

def limpiarnombre(nombre):
    return re.sub(r'[^a-zA-Z0-9 ]', '', nombre.replace('\n', ' ')).strip()

def descargarimagen(url, path):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            f.write(resp.content)
    except Exception:
        pass

def obtenerporcli(codigo, tipo, cover):
    script = "nhlinkspy" if tipo == "nh" else "h3linkspy"
    path = os.path.join("command", "getfiles", script)
    comando = ["python3", path, "-C", codigo]
    if cover:
        comando.append("--cover")

    try:
        result = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=60)
        salida = result.stdout.splitlines()
        texto = ""
        imagenes = []

        modotexto = False
        for linea in salida:
            if linea.strip().startswith(""):
                modotexto = True
            elif linea.strip().startswith(""):
                modotexto = False
            elif modotexto:
                texto += linea.strip() + " "
            elif linea.strip().startswith("http"):
                imagenes.append(linea.strip())

        return {"texto": texto.strip(), "imagenes": imagenes}
    except Exception as e:
        print("Error ejecutando script externo", e)
        return {"texto": "", "imagenes": []}

async def nh_combined_operation(client, message, codigos, tipo, proteger, userid, operacion):
    seleccion = defaultselectionmap.get(userid, "cbz")

    for codigo in codigos:
        datos = obtenerporcli(codigo, tipo, cover=(operacion == "cover"))
        nombrebase = limpiarnombre(datos["texto"]) or f"{tipo} {codigo}"
        imagenes = datos["imagenes"]

        if not imagenes:
            await message.reply(f"No se encontraron imagenes para {codigo}")
            continue

        try:
            previewurl = imagenes[0]
            ext = os.path.splitext(previewurl)[1].lower()
            safeext = ext if ext in [".jpg", ".jpeg", ".png"] else ".jpg"
            previewpath = f"{nombrebase} preview{safeext}"
            descargarimagen(previewurl, previewpath)

            await client.send_photo(
                chat_id=message.chat.id,
                photo=previewpath,
                caption=f"{nombrebase} Numero de paginas {len(imagenes)}",
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
                    caption=f"{nombrebase} Numero de paginas {len(imagenes)}",
                    protect_content=proteger
                )
                os.remove(fallbackpath)
                os.remove(previewpath)

            except Exception:
                try:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=previewpath,
                        caption=f"{nombrebase} Numero de paginas {len(imagenes)}",
                        protect_content=proteger
                    )
                    os.remove(previewpath)
                except Exception as e:
                    await message.reply(f"No pude enviar la portada {type(e).__name__} {e}")

        if operacion == "cover":
            continue

        progresomsg = await message.reply(
            f"Generando archivo para {nombrebase} {len(imagenes)} paginas Progreso 0 de {len(imagenes)}"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            threads = []

            for idx, url in enumerate(imagenes):
                ext = os.path.splitext(url)[1].lower()
                ext = ext if ext in [".jpg", ".jpeg", ".png", ".webp"] else ".jpg"
                path = os.path.join(tmpdir, f"{idx+1:03d}{ext}")
                t = threading.Thread(target=descargarimagen, args=(url, path))
                threads.append(t)
                paths.append(path)

                if (idx + 1) % 5 == 0 or (idx + 1) == len(imagenes):
                    try:
                        await progresomsg.edit_text(
                            f"Generando archivo para {nombrebase} {len(imagenes)} paginas Progreso {idx + 1} de {len(imagenes)}"
                        )
                    except Exception:
                        pass

            for t in threads:
                t.start()
            for t in threads:
                t.join()

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
                            try:
                                with Image.open(path) as badimg:
                                    fixed = badimg.convert("RGB")
                                    mainimages.append(fixed)
                            except Exception:
                                continue
                    if mainimages:
                        mainimages[0].save(pdfpath, save_all=True, append_images=mainimages[1:])
                        archivos.append(pdfpath)
                except Exception:
                    await message.reply(f"Error al generar PDF para {nombrebase}")

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
