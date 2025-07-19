import os
import re
import tempfile
import shutil
import requests
import threading
import subprocess
from PIL import Image

default_selection_map = {}

def cambiar_default_selection(user_id, nueva_seleccion):
    opciones_validas = [None, "pdf", "cbz", "both"]
    if nueva_seleccion is not None:
        nueva_seleccion = nueva_seleccion.lower()
    if nueva_seleccion not in opciones_validas:
        raise ValueError("Selección inválida. Debe ser None, 'pdf', 'cbz', o 'both'.")
    default_selection_map[user_id] = nueva_seleccion

def limpiar_nombre(nombre):
    # Elimina caracteres no válidos y convierte saltos de línea en espacios
    return re.sub(r'[\\/:*?"<>|]', '', nombre.replace('\n', ' ')).strip()

def descargar_imagen(url, path):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            f.write(resp.content)
    except Exception:
        pass

def obtener_por_cli(codigo, tipo, cover):
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
        print(f"❌ Error ejecutando script externo: {e}")
        return {"texto": "", "imagenes": []}

async def nh_combined_operation(client, message, codigos, tipo, proteger, user_id, operacion):
    seleccion = default_selection_map.get(user_id, "cbz")

    for codigo in codigos:
        datos = obtener_por_cli(codigo, tipo, cover=(operacion == "cover"))
        nombre = limpiar_nombre(datos["texto"]) or f"{tipo}_{codigo}"
        imagenes = datos["imagenes"]

        if not imagenes:
            await message.reply(f"❌ No se encontraron imágenes para {codigo}.")
            continue

        # 🖼️ Enviar preview con fallbacks
        try:
            preview_url = imagenes[0]
            ext = os.path.splitext(preview_url)[1].lower()
            safe_ext = ext if ext in [".jpg", ".jpeg", ".png"] else ".jpg"
            preview_path = f"{nombre}_preview{safe_ext}"
            descargar_imagen(preview_url, preview_path)

            await client.send_photo(
                chat_id=message.chat.id,
                photo=preview_path,
                caption=f"{nombre}\nNúmero de páginas: {len(imagenes)}",
                protect_content=proteger
            )
            os.remove(preview_path)

        except Exception:
            fallback_path = f"{nombre}_fallback.png"
            try:
                with Image.open(preview_path) as img:
                    img.convert("RGB").save(fallback_path)

                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=fallback_path,
                    caption=f"{nombre}\nNúmero de páginas: {len(imagenes)}",
                    protect_content=proteger
                )
                os.remove(fallback_path)
                os.remove(preview_path)

            except Exception:
                try:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=preview_path,
                        caption=f"{nombre}\nNúmero de páginas: {len(imagenes)}",
                        protect_content=proteger
                    )
                    os.remove(preview_path)
                except Exception as e:
                    await message.reply(f"❌ No pude enviar la portada. {type(e).__name__}: {e}")

        if operacion == "cover":
            continue

        progreso_msg = await message.reply(
            f"📦 Generando archivo para {nombre} ({len(imagenes)} páginas)...\nProgreso 0/{len(imagenes)}"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            threads = []

            for idx, url in enumerate(imagenes):
                ext = os.path.splitext(url)[1].lower()
                ext = ext if ext in [".jpg", ".jpeg", ".png", ".webp"] else ".jpg"
                path = os.path.join(tmpdir, f"{idx+1:03d}{ext}")
                t = threading.Thread(target=descargar_imagen, args=(url, path))
                threads.append(t)
                paths.append(path)

                if (idx + 1) % 5 == 0 or (idx + 1) == len(imagenes):
                    try:
                        await progreso_msg.edit_text(
                            f"📦 Generando archivo para {nombre} ({len(imagenes)} páginas)...\nProgreso {idx + 1}/{len(imagenes)}"
                        )
                    except Exception:
                        pass

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

        try:
            await progreso_msg.delete()
        except Exception:
            pass
