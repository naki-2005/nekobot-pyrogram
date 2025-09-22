import os
import json
import asyncio
import subprocess
from flask import Flask, request, send_from_directory, render_template_string, redirect, session, jsonify, url_for, abort
from threading import Thread, Lock
from command.torrets_tools import download_from_magnet_or_torrent, get_download_progress, cleanup_old_downloads
from command.htools import crear_cbz_desde_fuente
from my_flask_templates import LOGIN_TEMPLATE, MAIN_TEMPLATE, UTILS_TEMPLATE, DOWNLOADS_TEMPLATE, GALLERY_TEMPLATE
import uuid
from datetime import datetime
import re
import zipfile
import py7zr
from flask import send_file
import shutil
import base64
from cryptography.fernet import Fernet
import hashlib

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]
    
explorer = Flask("file_explorer")
explorer.secret_key = os.getenv("FLASK_SECRET", "supersecretkey")
BASE_DIR = "vault_files"
WEBACCESS_FILE = "web_access.json"

TOKEN_KEY = os.getenv("TOKEN_KEY", "TOKEN_KEY")
fernet_key = base64.urlsafe_b64encode(hashlib.sha256(TOKEN_KEY.encode()).digest())
cipher_suite = Fernet(fernet_key)

doujin_downloads = {}
doujin_lock = Lock()

def encrypt_token(data):
    json_data = json.dumps(data)
    encrypted = cipher_suite.encrypt(json_data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_token(token):
    try:
        decoded = base64.urlsafe_b64decode(token.encode())
        decrypted = cipher_suite.decrypt(decoded)
        return json.loads(decrypted.decode())
    except:
        return None

def validate_credentials(username, password):
    try:
        with open(WEBACCESS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = {}
    
    for uid, creds in users.items():
        if creds.get("user") == username and creds.get("pass") == password:
            return True
    return False

def check_token_auth():
    token = request.args.get('token')
    if token:
        token_data = decrypt_token(token)
        if token_data and validate_credentials(token_data.get('user'), token_data.get('pass')):
            session["logged_in"] = True
            session["username"] = token_data.get('user')
            return True
    return False

def login_required(f):
    def wrapper(*args, **kwargs):
        if not check_token_auth() and not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def validate_path(input_path):
    if not input_path:
        return False
    abs_base = os.path.abspath(BASE_DIR)
    abs_path = os.path.abspath(input_path)
    return abs_path.startswith(abs_base)

@explorer.route("/auth", methods=["GET", "POST"])
def generate_token():
    if request.method == "POST":
        username = request.form.get("u", "").strip()
        password = request.form.get("p", "").strip()
    else:
        username = request.args.get("u", "").strip()
        password = request.args.get("p", "").strip()
    
    if not username or not password:
        return jsonify({"error": "Usuario y contraseña requeridos"}), 400
    
    if validate_credentials(username, password):
        token_data = {
            "user": username,
            "pass": password,
            "timestamp": datetime.now().isoformat()
        }
        token = encrypt_token(token_data)
        return jsonify({
            "token": token,
            "message": "Token generado exitosamente",
            "url_example": f"{request.host_url}?token={token}"
        })
    else:
        return jsonify({"error": "Credenciales inválidas"}), 401

@explorer.route("/", defaults={"path": ""})
@explorer.route("/<path:path>")
def serve_root(path):
    check_token_auth()
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
    token = request.args.get('token')
    if token:
        token_data = decrypt_token(token)
        if token_data and validate_credentials(token_data.get('user'), token_data.get('pass')):
            session["logged_in"] = True
            session["username"] = token_data.get('user')
            return redirect("/")
    
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

@explorer.route("/browse", methods=["GET", "POST"])
@login_required
def browse():
    if request.method == "POST":
        rel_path = request.form.get("path", "")
    else:
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

@explorer.route("/files", methods=["GET", "POST"])
@login_required
def list_files():
    """Endpoint para listar todos los archivos recursivamente (uso con curl)"""
    abs_base = os.path.abspath(BASE_DIR)
    
    def list_files_recursive(directory, base_path):
        file_list = []
        try:
            for item in sorted(os.listdir(directory), key=natural_sort_key):
                full_path = os.path.join(directory, item)
                rel_path = os.path.relpath(full_path, base_path)
                
                if os.path.isdir(full_path):
                    file_list.append(f"[DIR]  {rel_path}/")
                    file_list.extend(list_files_recursive(full_path, base_path))
                else:
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2)
                    file_list.append(f"[FILE] {rel_path} ({size_mb} MB)")
        except Exception as e:
            file_list.append(f"[ERROR] No se pudo acceder a {directory}: {e}")
        
        return file_list
    
    try:
        all_files = list_files_recursive(abs_base, abs_base)
        response_text = "\n".join(all_files)
        return response_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return f"Error al listar archivos: {e}", 500

@explorer.route("/gallery", methods=["GET", "POST"])
@login_required
def gallery():
    if request.method == "POST":
        rel_path = request.form.get("path", "")
    else:
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

@explorer.route("/utils", methods=["GET", "POST"])
@login_required
def utils_page():
    return render_template_string(UTILS_TEMPLATE)

@explorer.route("/downloads", methods=["GET", "POST"])
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
                if (current_time - end_time).total_seconds() > 3600:
                    to_delete.append(download_id)
        
        for download_id in to_delete:
            del doujin_downloads[download_id]
    
    return render_template_string(DOWNLOADS_TEMPLATE, 
                                downloads=downloads, 
                                doujin_downloads=doujin_downloads)

@explorer.route("/api/downloads", methods=["GET", "POST"])
@login_required
def api_downloads():
    cleanup_old_downloads()
    downloads = get_download_progress()
    return jsonify({"torrents": downloads, "doujins": doujin_downloads})

@explorer.route("/download", methods=["GET", "POST"])
@login_required
def download():
    if request.method == "POST":
        rel_path = request.form.get("path")
    else:
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

@explorer.route("/crear_cbz", methods=["GET", "POST"])
@login_required
def crear_cbz():
    if request.method == "POST":
        codigo_input = request.form.get("codigo", "").strip()
        tipo = request.form.get("tipo", "").strip()
    else:
        codigo_input = request.args.get("codigo", "").strip()
        tipo = request.args.get("tipo", "").strip()

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

@explorer.route("/upload", methods=["GET", "POST"])
@login_required
def upload_file():
    if request.method == "GET":
        return '''
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file">
            <input type="submit" value="Upload">
        </form>
        '''
    
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    file = request.files.get("file")
    if file and file.filename:
        save_path = os.path.join(BASE_DIR, file.filename)
        file.save(save_path)
        return redirect("/")
    return "Archivo inválido.", 400

@explorer.route("/magnet", methods=["GET", "POST"])
@login_required
def handle_magnet():
    if request.method == "POST":
        link = request.form.get("magnet", "").strip()
    else:
        link = request.args.get("magnet", "").strip()
        
    if not link:
        return "<h3>❌ Magnet link vacío.</h3>", 400

    try:
        download_id = str(uuid.uuid4())
        
        def run_async_download():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(download_from_magnet_or_torrent(link, BASE_DIR, None, download_id))
            finally:
                loop.close()

        Thread(target=run_async_download).start()
        return redirect("/downloads")
    except Exception as e:
        return f"<h3>Error al iniciar descarga: {e}</h3>", 500

@explorer.route("/delete", methods=["GET", "POST"])
@login_required
def delete_file():
    if request.method == "POST":
        path = request.form.get("path")
    else:
        path = request.args.get("path")
    
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

@explorer.route("/compress", methods=["GET", "POST"])
@login_required
def compress_items():
    if request.method == "POST":
        archive_name = request.form.get("archive_name", "").strip()
        selected = request.form.getlist("selected")
    else:
        archive_name = request.args.get("archive_name", "").strip()
        selected = request.args.getlist("selected")
    
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

        for path in selected:
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)

        return redirect(request.referrer or "/")
    except Exception as e:
        return f"<h3>❌ Error al comprimir: {e}</h3>", 500

@explorer.route("/extract", methods=["GET", "POST"])
@login_required
def extract_archive():
    if request.method == "POST":
        archive_path = request.form.get("path")
    else:
        archive_path = request.args.get("path")
    
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

@explorer.route("/api/snh/<path:search_term>")
def api_search_nh(search_term):
    try:
        from command.get_files.scrap_nh import scrape_nhentai_with_selenium
        
        page = request.args.get('p', 1, type=int)
        if page < 1:
            page = 1
            
        galleries = scrape_nhentai_with_selenium(search_term=search_term, page=page)
        
        if not galleries:
            return jsonify({"error": "No se encontraron resultados"}), 404
            
        return jsonify({
            "search_term": search_term,
            "page": page,
            "results": galleries
        })
        
    except Exception as e:
        return jsonify({"error": f"Error en la búsqueda: {str(e)}"}), 500

@explorer.route("/api/dnh/<codigo>")
def api_download_nh(codigo):
    try:
        download_id = str(uuid.uuid4())
        
        with doujin_lock:
            doujin_downloads[download_id] = {
                "state": "processing",
                "codigos": [codigo],
                "tipo": "nh",
                "progress": 0,
                "total": 1,
                "completados": 0,
                "errores": 0,
                "start_time": datetime.now().isoformat(),
                "current_item": f"Preparando {codigo}",
                "resultados": []
            }

        def download_sync():
            try:
                from command.htools import crear_cbz_desde_fuente
                import asyncio
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                cbz_path = loop.run_until_complete(crear_cbz_desde_fuente(codigo, "nh"))
                
                with doujin_lock:
                    doujin_downloads[download_id]["state"] = "completed"
                    doujin_downloads[download_id]["completados"] = 1
                    doujin_downloads[download_id]["progress"] = 1
                    doujin_downloads[download_id]["resultados"] = [{
                        "codigo": codigo,
                        "estado": "completado",
                        "ruta": cbz_path,
                        "nombre": os.path.basename(cbz_path)
                    }]
                    doujin_downloads[download_id]["end_time"] = datetime.now().isoformat()
                    doujin_downloads[download_id]["cbz_path"] = cbz_path
                    
                loop.close()
                
            except Exception as e:
                with doujin_lock:
                    doujin_downloads[download_id]["state"] = "error"
                    doujin_downloads[download_id]["errores"] = 1
                    doujin_downloads[download_id]["error"] = str(e)

        Thread(target=download_sync, daemon=True).start()
        
        return jsonify({
            "download_id": download_id,
            "codigo": codigo,
            "status": "processing",
            "message": "Descarga iniciada"
        })
        
    except Exception as e:
        return jsonify({"error": f"Error al iniciar descarga: {str(e)}"}), 500

@explorer.route("/api/dnh_status/<download_id>")
def api_download_status(download_id):
    with doujin_lock:
        download_info = doujin_downloads.get(download_id)
    
    if not download_info:
        return jsonify({"error": "ID de descarga no encontrado"}), 404
        
    return jsonify(download_info)

@explorer.route("/api/download_cbz/<download_id>")
def api_download_cbz(download_id):
    with doujin_lock:
        download_info = doujin_downloads.get(download_id)
    
    if not download_info:
        return jsonify({"error": "ID de descarga no encontrado"}), 404
        
    if download_info.get("state") != "completed":
        return jsonify({"error": "La descarga no está completada"}), 400
        
    cbz_path = download_info.get("cbz_path")
    if not cbz_path or not os.path.exists(cbz_path):
        return jsonify({"error": "Archivo CBZ no encontrado"}), 404
        
    return send_file(cbz_path, as_attachment=True)

@explorer.route("/rename", methods=["GET", "POST"])
@login_required
def rename_item():
    if request.method == "POST":
        old_path = request.form.get("old_path")
        new_name = request.form.get("new_name")
    else:
        old_path = request.args.get("old_path")
        new_name = request.args.get("new_name")
    
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
        
@explorer.route("/help", methods=["GET"])
def help_page():
    base_url = request.host_url.rstrip('/')
    help_text = f"# Guía de uso con CURL\n\n## Autenticación\nPrimero genera un token de autenticación:\ncurl \"{base_url}/auth?u=TU_USUARIO&p=TU_CONTRASEÑA\"\n\nO usa autenticación básica en cada request:\ncurl -u \"usuario:contraseña\" {base_url}/files\n\n## Listar archivos recursivamente\ncurl \"{base_url}/files?token=TU_TOKEN\"\n# o\ncurl -u \"usuario:contraseña\" {base_url}/files\n\n## Descargar archivo\ncurl \"{base_url}/download?path=ruta/archivo.jpg&token=TU_TOKEN\" \\\n  -o \"archivo.jpg\"\n\n## Crear CBZ desde códigos\n\n### Un solo código (nhentai, hentai3, hitomi)\n# nhentai\ncurl \"{base_url}/crear_cbz?codigo=177013&tipo=nh&token=TU_TOKEN\"\n\n# hentai3\ncurl \"{base_url}/crear_cbz?codigo=12345&tipo=h3&token=TU_TOKEN\"\n\n# hitomi\ncurl \"{base_url}/crear_cbz?codigo=abc123&tipo=hito&token=TU_TOKEN\"\n\n### Múltiples códigos (solo nhentai y hentai3)\n# nhentai múltiple\ncurl \"{base_url}/crear_cbz?codigo=177013,228922,309437&tipo=nh&token=TU_TOKEN\"\n\n# hentai3 múltiple\ncurl \"{base_url}/crear_cbz?codigo=12345,67890,54321&tipo=h3&token=TU_TOKEN\"\n\n## Descargar desde magnet link\ncurl \"{base_url}/magnet?magnet=magnet:?xt=urn:btih:TU_HASH&token=TU_TOKEN\"\n\n## Renombrar archivo/directorio\ncurl \"{base_url}/rename?old_path=ruta/vieja/archivo.txt&new_name=archivo_nuevo.txt&token=TU_TOKEN\"\n\n## Eliminar archivo/directorio\ncurl \"{base_url}/delete?path=ruta/a/eliminar&token=TU_TOKEN\"\n\n## Subir archivo (requiere POST)\ncurl -X POST \"{base_url}/upload?token=TU_TOKEN\" \\\n  -F \"file=@archivo_local.jpg\"\n\n## Notas:\n- Reemplaza `TU_TOKEN` con el token obtenido del endpoint `/auth`\n- Reemplaza `TU_USUARIO` y `TU_CONTRASEÑA` con tus credenciales\n- Las rutas deben estar dentro del directorio base permitido\n- Para hitomi solo se permite un código a la vez"
    return help_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    

def run_flask():
    explorer.run(host="0.0.0.0", port=10000)
