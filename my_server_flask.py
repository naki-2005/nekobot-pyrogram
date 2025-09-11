import os
import json
import asyncio
import subprocess
from flask import Flask, request, send_from_directory, render_template_string, redirect, session, jsonify, url_for, abort
from threading import Thread, Lock
from command.torrets_tools import download_from_magnet, get_download_progress, cleanup_old_downloads
from command.htools import crear_cbz_desde_fuente
from my_flask_templates import LOGIN_TEMPLATE, MAIN_TEMPLATE, UTILS_TEMPLATE, DOWNLOADS_TEMPLATE, GALLERY_TEMPLATE
import uuid
from datetime import datetime
import re
import zipfile
import py7zr
from flask import send_file
import shutil

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]
    
explorer = Flask("file_explorer")
explorer.secret_key = os.getenv("FLASK_SECRET", "supersecretkey")
BASE_DIR = "vault_files"
WEBACCESS_FILE = "web_access.json"

doujin_downloads = {}
doujin_lock = Lock()

def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def validate_path(input_path):
    """Valida que una ruta esté dentro del directorio base permitido"""
    if not input_path:
        return False
    abs_base = os.path.abspath(BASE_DIR)
    abs_path = os.path.abspath(input_path)
    return abs_path.startswith(abs_base)

@explorer.route("/", defaults={"path": ""})
@explorer.route("/<path:path>")
def serve_root(path):
    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    abs_base = os.path.abspath(BASE_DIR)
    
    if not abs_path.startswith(abs_base):
        abort(404)
    
    if os.path.isfile(abs_path):
        return send_from_directory(
            os.path.dirname(abs_path), 
            os.path.basename(abs_path), 
            as_attachment=False
        )
    if os.path.isdir(abs_path):
        rel_path = os.path.relpath(abs_path, abs_base)
        if rel_path == ".":
            rel_path = ""
        return redirect(url_for("browse", path=rel_path))
    abort(404)

@explorer.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        try:
            with open(WEBACCESS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except:
            users = {}
        for uid, creds in users.items():
            if creds.get("user") == u and creds.get("pass") == p:
                session["logged_in"] = True
                return redirect("/")
        return "<h3 style='color:red;'>❌ Credenciales incorrectas</h3>", 403

    return render_template_string(LOGIN_TEMPLATE)

@explorer.route("/browse")
@login_required
def browse():
    rel_path = request.args.get("path", "")
    abs_requested = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    abs_base = os.path.abspath(BASE_DIR)

    if not abs_requested.startswith(abs_base):
        return "<h3>❌ Acceso denegado: ruta fuera de 'vault_files'.</h3>", 403

    try:
        items = []
        for name in sorted(os.listdir(abs_requested), key=natural_sort_key):
            full_path = os.path.join(abs_requested, name)
            is_dir = os.path.isdir(full_path)
            size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2) if not is_dir else "-"
            
            rel_item_path = os.path.relpath(full_path, abs_base)
            items.append({
                "name": name,
                "rel_path": rel_item_path,
                "full_path": full_path,
                "is_dir": is_dir,
                "size_mb": size_mb
            })
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        has_images = any(
            os.path.isfile(os.path.join(abs_requested, name)) and 
            any(name.lower().endswith(ext) for ext in image_extensions)
            for name in os.listdir(abs_requested)
        )
        
        current_rel_path = os.path.relpath(abs_requested, abs_base)
        if current_rel_path == ".":
            current_rel_path = ""
            
        return render_template_string(MAIN_TEMPLATE, 
                                    items=items, 
                                    has_images=has_images, 
                                    current_path=current_rel_path)
    except Exception as e:
        return f"<h3>Error al acceder a los archivos: {e}</h3>", 500

@explorer.route("/gallery")
@login_required
def gallery():
    rel_path = request.args.get("path", "")
    abs_requested = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    abs_base = os.path.abspath(BASE_DIR)

    if not abs_requested.startswith(abs_base):
        return "<h3>❌ Acceso denegado: ruta fuera de 'vault_files'.</h3>", 403

    try:
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        image_files = []
        
        for name in sorted(os.listdir(abs_requested), key=natural_sort_key):
            full_path = os.path.join(abs_requested, name)
            if os.path.isfile(full_path) and any(name.lower().endswith(ext) for ext in image_extensions):
                image_files.append({
                    "name": name,
                    "url_path": f"/{os.path.relpath(full_path, abs_base)}"
                })
        
        current_rel_path = os.path.relpath(abs_requested, abs_base)
        if current_rel_path == ".":
            current_rel_path = ""
            
        return render_template_string(GALLERY_TEMPLATE, 
                                    image_files=image_files, 
                                    current_path=current_rel_path)
    except Exception as e:
        return f"<h3>Error al acceder a la galería: {e}</h3>", 500

@explorer.route("/utils")
@login_required
def utils_page():
    return render_template_string(UTILS_TEMPLATE)

@explorer.route("/downloads")
@login_required
def downloads_page():
    cleanup_old_downloads()
    downloads = get_download_progress()
    
    current_time = datetime.now()
    with doujin_lock:
        to_delete = []
        for download_id, download_info in doujin_downloads.items():
            if download_info.get("state") == "completed" and "end_time" in download_info:
                end_time = datetime.fromisoformat(download_info["end_time"])
                if (current_time - end_time).total_seconds() > 3600:  # 1 hora
                    to_delete.append(download_id)
        
        for download_id in to_delete:
            del doujin_downloads[download_id]
    
    return render_template_string(DOWNLOADS_TEMPLATE, 
                                downloads=downloads, 
                                doujin_downloads=doujin_downloads)

@explorer.route("/api/downloads")
@login_required
def api_downloads():
    cleanup_old_downloads()
    downloads = get_download_progress()
    return jsonify({"torrents": downloads, "doujins": doujin_downloads})

@explorer.route("/download")
def download():
    rel_path = request.args.get("path")
    if not rel_path:
        return "<h3>Archivo no especificado.</h3>", 400
        
    abs_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    abs_base = os.path.abspath(BASE_DIR)
    
    if not abs_path.startswith(abs_base) or not os.path.isfile(abs_path):
        return "<h3>Archivo no válido para descarga.</h3>", 400
        
    if 'Range' in request.headers:
        range_header = request.headers.get('Range')
        range_start = int(range_header.split('=')[1].split('-')[0])
        return send_from_directory(
            os.path.dirname(abs_path), 
            os.path.basename(abs_path), 
            as_attachment=True,
            conditional=True,
            download_name=os.path.basename(abs_path)
        )
    else:
        return send_from_directory(
            os.path.dirname(abs_path), 
            os.path.basename(abs_path), 
            as_attachment=True
        )

@explorer.route("/crear_cbz", methods=["POST"])
def crear_cbz():
    codigo_input = request.form.get("codigo", "").strip()
    tipo = request.form.get("tipo", "").strip()

    if not codigo_input or tipo not in ["nh", "h3", "hito"]:
        return "<h3>❌ Código o tipo inválido.</h3>", 400

    if tipo == "hito":
        codigos = [codigo_input]
    else:
        if codigo_input.replace(",", "").replace(" ", "").isdigit():
            codigos = [c.strip() for c in codigo_input.split(",") if c.strip()]
        else:
            codigos = [codigo_input]
    
    if not codigos:
        return "<h3>❌ No se proporcionaron códigos válidos.</h3>", 400

    total_codigos = len(codigos)
    plural = "s" if total_codigos > 1 else ""
    response_msg = f"<h3>✅ Iniciando descarga de {total_codigos} doujin{plural}</h3>"
    response_msg += f"<p>Procesando: {', '.join(codigos[:3])}{'...' if total_codigos > 3 else ''}</p>"
    response_msg += "<p>Puedes ver el progreso en la <a href='/downloads'>página de descargas</a></p>"

    download_id = str(uuid.uuid4())
    
    with doujin_lock:
        doujin_downloads[download_id] = {
            "state": "processing",
            "codigos": codigos,
            "tipo": tipo,
            "progress": 0,
            "total": total_codigos,
            "completados": 0,
            "errores": 0,
            "start_time": datetime.now().isoformat(),
            "current_item": f"Preparando {codigos[0]}" if codigos else "Iniciando",
            "resultados": []
        }

    def run_async_download():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            resultados = []
            for i, codigo in enumerate(codigos):
                with doujin_lock:
                    doujin_downloads[download_id]["progress"] = i + 1
                    doujin_downloads[download_id]["current_item"] = f"Procesando {codigo} ({i+1}/{total_codigos})"
                
                try:
                    cbz_path = loop.run_until_complete(crear_cbz_desde_fuente(codigo, tipo))
                    resultados.append({
                        "codigo": codigo,
                        "estado": "completado",
                        "ruta": cbz_path,
                        "nombre": os.path.basename(cbz_path)
                    })
                    with doujin_lock:
                        doujin_downloads[download_id]["completados"] += 1
                except Exception as e:
                    resultados.append({
                        "codigo": codigo,
                        "estado": "error",
                        "error": str(e)
                    })
                    with doujin_lock:
                        doujin_downloads[download_id]["errores"] += 1
                
                with doujin_lock:
                    doujin_downloads[download_id]["resultados"] = resultados
            
            with doujin_lock:
                doujin_downloads[download_id]["state"] = "completed"
                doujin_downloads[download_id]["end_time"] = datetime.now().isoformat()
                doujin_downloads[download_id]["current_item"] = "Descarga completada"
            
        except Exception as e:
            with doujin_lock:
                doujin_downloads[download_id]["state"] = "error"
                doujin_downloads[download_id]["error"] = str(e)
                doujin_downloads[download_id]["current_item"] = f"Error: {str(e)}"
        finally:
            loop.close()

    Thread(target=run_async_download, daemon=True).start()
    return response_msg

@explorer.route("/upload", methods=["POST"])
def upload_file():
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    file = request.files.get("file")
    if file and file.filename:
        save_path = os.path.join(BASE_DIR, file.filename)
        file.save(save_path)
        return redirect("/")
    return "Archivo inválido.", 400

@explorer.route("/magnet", methods=["POST"])
def handle_magnet():
    link = request.form.get("magnet", "").strip()
    if not link:
        return "<h3>❌ Magnet link vacío.</h3>", 400

    try:
        download_id = str(uuid.uuid4())
        
        def run_async_download():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(download_from_magnet(link, BASE_DIR, None, download_id))
            finally:
                loop.close()

        Thread(target=run_async_download).start()
        return redirect("/downloads")
    except Exception as e:
        return f"<h3>Error al iniciar descarga: {e}</h3>", 500

@explorer.route("/delete", methods=["POST"])
@login_required
def delete_file():
    path = request.form.get("path")
    
    if not path:
        return "<h3>❌ Archivo no especificado.</h3>", 400
        
    if not validate_path(path):
        return "<h3>❌ Ruta no válida.</h3>", 400
        
    if not os.path.exists(path):
        return "<h3>❌ Archivo no encontrado.</h3>", 404
        
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            return "<h3>❌ Elemento no válido para eliminar.</h3>", 400
            
        return redirect(request.referrer or "/")
    except Exception as e:
        return f"<h3>Error al eliminar: {e}</h3>", 500

@explorer.route("/compress", methods=["POST"])
@login_required
def compress_items():
    archive_name = request.form.get("archive_name", "").strip()
    selected = request.form.getlist("selected")
    
    if not archive_name or not selected:
        return "<h3>❌ Debes proporcionar un nombre y seleccionar archivos.</h3>", 400

    selected = [path for path in selected if path.strip()]
    if not selected:
        return "<h3>❌ No se seleccionaron archivos válidos.</h3>", 400
    for path in selected:
        if not validate_path(path):
            return "<h3>❌ Ruta no válida detectada.</h3>", 400

    archive_path = os.path.join(BASE_DIR, f"{archive_name}.7z")
    try:
        cmd_args = [
            os.path.join("7z", "7zz"),
            'a',
            '-mx=0',
            '-v2000m',
            archive_path
        ] + selected
        
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        
        if result.returncode != 0:
            return f"<h3>❌ Error al comprimir: {result.stderr}</h3>", 500

        # Eliminar archivos originales después de comprimir exitosamente
        for path in selected:
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)

        return redirect(request.referrer or "/")
    except Exception as e:
        return f"<h3>❌ Error al comprimir: {e}</h3>", 500

@explorer.route("/extract", methods=["POST"])
@login_required
def extract_archive():
    archive_path = request.form.get("path")
    
    if not archive_path or not os.path.isfile(archive_path):
        return "<h3>❌ Archivo no válido para descomprimir.</h3>", 400
    
    if not validate_path(archive_path):
        return "<h3>❌ Ruta no válida.</h3>", 400
    
    try:
        extract_dir = os.path.splitext(archive_path)[0]
        if os.path.exists(extract_dir):
            counter = 1
            while os.path.exists(f"{extract_dir}_{counter}"):
                counter += 1
            extract_dir = f"{extract_dir}_{counter}"
        
        os.makedirs(extract_dir, exist_ok=True)
        
        if archive_path.lower().endswith('.7z'):
            cmd_args = [
                os.path.join("7z", "7zz"),
                'x',
                archive_path,
                f'-o{extract_dir}',
                '-y' 
            ]
            result = subprocess.run(cmd_args, capture_output=True, text=True)
            
            if result.returncode != 0:
                return f"<h3>❌ Error al descomprimir archivo 7z: {result.stderr}</h3>", 500
                
        elif archive_path.lower().endswith('.cbz') or archive_path.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as z:
                z.extractall(extract_dir)
        else:
            return "<h3>❌ Formato de archivo no compatible para descompresión.</h3>", 400
        
        return redirect(request.referrer or "/")
    except Exception as e:
        return f"<h3>Error al descomprimir archivo: {e}</h3>", 500

@explorer.route("/rename", methods=["POST"])
@login_required
def rename_item():
    old_path = request.form.get("old_path")
    new_name = request.form.get("new_name")
    
    if not old_path or not new_name:
        return "<h3>❌ Datos inválidos para renombrar.</h3>", 400
    if not validate_path(old_path):
        return "<h3>❌ Ruta no válida.</h3>", 400
    
    try:
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        if not validate_path(new_path):
            return "<h3>❌ El nuevo nombre crea una ruta no válida.</h3>", 400
            
        os.rename(old_path, new_path)
        return redirect(request.referrer or "/")
    except Exception as e:
        return f"<h3>Error al renombrar: {e}</h3>", 500

def run_flask():
    explorer.run(host="0.0.0.0", port=10000)
