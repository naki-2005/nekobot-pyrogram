import os
import re
import tempfile
import shutil
import requests
import threading
import subprocess
from PIL import Image
import aiofiles
from command.get_files.nh_links import obtener_info_y_links as obtener_nh
from command.get_files.h3_links import obtener_titulo_y_imagenes as obtener_3h

default_selection_map = {}

def cambiar_default_selection(user_id, nueva_seleccion):
    """Cambia la selección predeterminada del usuario."""
    opciones_validas = [None, "pdf", "cbz", "both"]
    if nueva_seleccion is not None:
        nueva_seleccion = nueva_seleccion.lower()
    if nueva_seleccion not in opciones_validas:
        raise ValueError("Selección inválida. Debe ser None, 'PDF', 'CBZ', o 'Both'.")
    default_selection_map[user_id] = nueva_seleccion

def limpiar_nombre(nombre):
    return re.sub(r'[\\/:*?"<>|]', '', nombre).strip()

def descargar_imagen(url, path):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            f.write(resp.content)
    except Exception:
        pass

def obtener_cover_externo(codigo, tipo):
    comando = ["python3"]
    if tipo == "nh":
        comando.append("command/get_files/nh_links.py")
    else:
        comando.append("command/get_files/h3_links.py")
    comando.extend(["-C", codigo, "--cover"])

    try:
        result = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20)
        salida = result.stdout.splitlines()
        texto = ""
        imagenes = []

        modo_texto = False
        for linea in salida:
            if linea.strip().startswith("📄"):
                modo_texto = True
            elif linea.strip().startswith("🖼️"):
                modo_texto = False
            elif modo_texto:
                texto += linea.strip() + "\n"
            elif linea.strip().startswith("http"):
                imagenes.append(linea.strip())

        return {"texto": texto.strip(), "imagenes": imagenes}
    except Exception as e:
        print(f"❌ Error ejecutando CLI externo: {e}")
        return {"texto": "", "imagenes": []}

async def nh_combined_operation(client, message, codigos, tipo, proteger, user_id, operacion):
    seleccion = default_selection_map.get(user_id, "cbz")  # Valor predeterminado

    for codigo in codigos:
        datos = obtener_cover_externo(codigo, tipo) if operacion == "cover" else (
            obtener_nh(codigo, False) if tipo == "nh" else obtener_3h(codigo, False)
        )

        nombre = limpiar_nombre(datos["texto"]) or f"{tipo}_{codigo}"
        imagenes = datos["imagenes"]

        if not imagenes:
            await message.reply(f"❌ No se encontraron imágenes para {codigo}.")
            continue

        # 🖼️ Siempre enviar preview de la primera imagen
        try:
            preview_path = f"{nombre}_preview.jpg"
            descargar_imagen(imagenes[0], preview_path)
            caption = f"{nombre}\nNúmero de páginas: {len(imagenes)}"
            await client.send_photo(
                chat_id=message.chat.id,
                photo=preview_path,
                caption=caption,
                protect_content=proteger
            )
            os.remove(preview_path)
        except Exception:
            pass

        if operacion == "cover":
            continue

        await message.reply(f"📦 Generando archivo para {nombre} ({len(imagenes)} páginas)...")

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            threads = []

            for idx, url in enumerate(imagenes):
                ext = os.path.splitext(url)[1].lower()
                ext = ext if ext in [".jpg", ".jpeg", ".png"] else ".jpg"
                path = os.path.join(tmpdir, f"{idx+1:03d}{ext}")
                t = threading.Thread(target=descargar_imagen, args=(url, path))
                threads.append(t)
                paths.append(path)

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            archivos = []

            if seleccion in ["cbz", "both"]:
                cbz_path = f"{nombre}.cbz"
                shutil.make_archive(nombre, 'zip', tmpdir)
                os.rename(f"{nombre}.zip", cbz_path)
                archivos.append(cbz_path)

            if seleccion in ["pdf", "both"]:
                pdf_path = f"{nombre}.pdf"
                try:
                    main_images = []
                    for path in paths:
                        try:
                            with Image.open(path) as im:
                                main_images.append(im.convert("RGB"))
                        except Exception:
                            try:
                                with Image.open(path) as bad_img:
                                    fixed = bad_img.convert("RGB")
                                    main_images.append(fixed)
                            except Exception:
                                continue
                    if main_images:
                        main_images[0].save(pdf_path, save_all=True, append_images=main_images[1:])
                        archivos.append(pdf_path)
                except Exception:
                    await message.reply(f"❌ Error al generar PDF para {nombre}.")

            for archivo in archivos:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=archivo,
                    caption=nombre,
                    protect_content=proteger
                )
                os.remove(archivo)
