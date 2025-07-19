import os
import re
import tempfile
import requests
import threading
import subprocess
from io import BytesIO
from PIL import Image

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

def descargarimagen(url, path):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            f.write(resp.content)
    except Exception:
        pass

def obtenerporcli(codigo, tipo, cover):
    script = "nh_links.py" if tipo == "nh" else "h3_links.py"
    path = os.path.join("command", "get_files", script)
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

        # 🖼️ Portada
        try:
            previewurl = imagenes[0]
            ext = os.path.splitext(previewurl)[1].lower()
            safeext = ext if ext in [".jpg", ".jpeg", ".png"] else ".jpg"
            previewpath = f"{nombrebase} preview{safeext}"
            descargarimagen(previewurl, previewpath)

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
            f"📦 Descargando archivos desde el servidor para {nombrebase}..."
        )

        try:
            if seleccion in ["cbz", "both"]:
                cbz_url = f"https://naki-hdl.onrender.com/direct/dl1/{codigo}"
                resp = requests.get(cbz_url, timeout=600)
                resp.raise_for_status()
                archivo_cbz = BytesIO(resp.content)
                archivo_cbz.name = f"{nombrebase}.cbz"

                await client.send_document(
                    message.chat.id,
                    archivo_cbz,
                    caption=nombrebase,
                    protect_content=proteger
                )

            if seleccion in ["pdf", "both"]:
                pdf_url = f"https://naki-hdl.onrender.com/direct/dl1-pdf/{codigo}"
                resp = requests.get(pdf_url, timeout=600)
                resp.raise_for_status()
                archivo_pdf = BytesIO(resp.content)
                archivo_pdf.name = f"{nombrebase}.pdf"

                await client.send_document(
                    message.chat.id,
                    archivo_pdf,
                    caption=nombrebase,
                    protect_content=proteger
                )

        except Exception as e:
            await message.reply(f"❌ No pude descargar los archivos para {codigo}. {type(e).__name__}: {e}")

        try:
            await progresomsg.delete()
        except Exception:
            pass
