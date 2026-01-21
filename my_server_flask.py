import os
import json
import asyncio
import subprocess
from flask import Flask, request, send_from_directory, render_template_string, redirect, session, jsonify, url_for, abort
from threading import Thread, Lock
from command.torrets_tools import download_from_magnet_or_torrent, get_download_progress, cleanup_old_downloads
from command.htools import crear_cbz_desde_fuente
from my_flask_templates import LOGIN_TEMPLATE, MANGA_TEMPLATE, NEW_MAIN_TEMPLATE, WEBUSERS_TEMPLATE, UTILS_TEMPLATE, DOWNLOADS_TEMPLATE, GALLERY_TEMPLATE, SEARCH_NH_TEMPLATE, SEARCH_3H_TEMPLATE, VIEW_NH_TEMPLATE, VIEW_3H_TEMPLATE
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
import requests
from io import BytesIO
from command.hapi.h3 import create_3hentai_cbz, serve_and_clean
from command.get_files.scrap_nh import scrape_nhentai_with_selenium
from command.db.db import save_user_data_to_db, load_user_config

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
mega_downloads = {}
manga_downloads = {}
doujin_lock = Lock()
mega_lock = Lock()
manga_lock = Lock()

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

@explorer.route("/auth", methods=["GET"])
def generate_auth_token():
    username = request.args.get("u", "").strip()
    password = request.args.get("p", "").strip()
    
    if not username or not password:
        return jsonify({
            "error": "Se requieren parámetros u (usuario) y p (contraseña)"
        }), 400
    
    user_info = validate_credentials(username, password)
    if not user_info:
        return jsonify({"error": "Credenciales inválidas"}), 401
    
    token_data = {
        "user": username,
        "pass": password,
        "user_id": user_info["user_id"],
        "level": user_info["level"],
        "timestamp": datetime.now().isoformat()
    }
    
    token = encrypt_token(token_data)
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        "success": True,
        "token": token,
        "url_with_token": f"{base_url}/?token={token}",
        "url_for_files": f"{base_url}/files?token={token}",
        "user_info": {
            "username": username,
            "user_id": user_info["user_id"],
            "level": user_info["level"]
        }
    })

@explorer.route("/verify_token", methods=["GET"])
def verify_token():
    token = request.args.get("token", "")
    
    if not token:
        return jsonify({"error": "Se requiere parámetro token"}), 400
    
    token_data = decrypt_token(token)
    if not token_data:
        return jsonify({"valid": False, "error": "Token inválido o expirado"}), 401
    
    user_info = validate_credentials(token_data.get('user'), token_data.get('pass'))
    if not user_info:
        return jsonify({"valid": False, "error": "Credenciales ya no válidas"}), 401
    
    return jsonify({
        "valid": True,
        "user": token_data.get('user'),
        "user_id": token_data.get('user_id'),
        "level": token_data.get('level'),
        "timestamp": token_data.get('timestamp')
    })

def get_user_level(user_id_str):
    user_level = load_user_config(user_id_str, "lvl")
    if user_level and user_level.isdigit():
        return int(user_level)
    return 0

def validate_credentials(username, password):
    try:
        with open(WEBACCESS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = {}
    
    for uid, creds in users.items():
        if creds.get("user") == username and creds.get("pass") == password:
            user_level = get_user_level(uid)
            return {"user_id": uid, "username": username, "level": user_level, "password": password}
    return None
    
def check_direct_auth():
    username = request.args.get('u', '').strip()
    p_values = request.args.getlist('p')
    password = p_values[-1].strip() if p_values else ''
    
    if username and password:
        user_info = validate_credentials(username, password)
        if user_info:
            session["logged_in"] = True
            session["username"] = user_info["username"]
            session["user_id"] = user_info["user_id"]
            session["user_level"] = user_info["level"]
            session["user_password"] = user_info["password"]
            return True
    return False
    
def check_token_auth():
    token = request.args.get('token')
    if token:
        token_data = decrypt_token(token)
        if token_data:
            user_info = validate_credentials(token_data.get('user'), token_data.get('pass'))
            if user_info:
                session["logged_in"] = True
                session["username"] = user_info["username"]
                session["user_id"] = user_info["user_id"]
                session["user_level"] = user_info["level"]
                session["user_password"] = user_info["password"]
                return True
    return False
    
def login_required(f):
    def wrapper(*args, **kwargs):
        if not check_token_auth() and not check_direct_auth() and not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper



def level_required(min_level):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect("/login")
            
            user_level = session.get("user_level", 0)
            if user_level < min_level:
                abort(403)
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def validate_path(input_path):
    if not input_path:
        return False
    abs_base = os.path.abspath(BASE_DIR)
    abs_path = os.path.abspath(input_path)
    return abs_path.startswith(abs_base)

def check_empty_folder(folder_path):
    """Verifica recursivamente si una carpeta está vacía (considera subcarpetas vacías)"""
    if not os.path.isdir(folder_path):
        return False
    
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            if not check_empty_folder(item_path):
                return False
        else:
            return False
    
    return True

def delete_empty_folders(start_path):
    """Elimina recursivamente todas las carpetas vacías"""
    deleted_count = 0
    
    for root, dirs, files in os.walk(start_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if check_empty_folder(dir_path):
                try:
                    os.rmdir(dir_path)
                    deleted_count += 1
                except:
                    pass
    
    return deleted_count

def get_all_folders():
    """Obtiene lista de todas las carpetas para el menú de mover"""
    folders = ["/"]
    
    for root, dirs, files in os.walk(BASE_DIR):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            rel_path = os.path.relpath(dir_path, BASE_DIR)
            folders.append(rel_path)
    
    return sorted(set(folders))

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
        if token_data:
            user_info = validate_credentials(token_data.get('user'), token_data.get('pass'))
            if user_info:
                session["logged_in"] = True
                session["username"] = user_info["username"]
                session["user_id"] = user_info["user_id"]
                session["user_level"] = user_info["level"]
                session["user_password"] = user_info["password"]
                return redirect("/")
    
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        
        user_info = validate_credentials(u, p)
        if user_info:
            session["logged_in"] = True
            session["username"] = user_info["username"]
            session["user_id"] = user_info["user_id"]
            session["user_level"] = user_info["level"]
            session["user_password"] = user_info["password"]
            return redirect("/")
        return "<h3 style='color:red;'>❌ Credenciales incorrectas</h3>", 403

    return render_template_string(LOGIN_TEMPLATE)

@explorer.route("/browse", methods=["GET", "POST"])
@login_required
def browse():
    user_level = session.get("user_level", 0)
    
    def list_files_recursive(directory, base_path, prefix="", file_index_start=0):
        items = []
        file_count = file_index_start
        
        try:
            for name in sorted(os.listdir(directory), key=natural_sort_key):
                full_path = os.path.join(directory, name)
                rel_path = os.path.relpath(full_path, base_path)
                
                if os.path.isdir(full_path):
                    items.append({
                        "type": "dir",
                        "name": name,
                        "rel_path": rel_path,
                        "full_path": full_path,
                        "index": None
                    })
                    
                    sub_items, file_count = list_files_recursive(
                        full_path, base_path, prefix + name + "/", file_count
                    )
                    items.extend(sub_items)
                else:
                    file_count += 1
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2)
                    ext = os.path.splitext(name)[1].lower()
                    items.append({
                        "type": "file",
                        "name": name,
                        "rel_path": rel_path,
                        "full_path": full_path,
                        "size_mb": size_mb,
                        "index": file_count,
                        "ext": ext
                    })
        
        except Exception:
            pass
        
        return items, file_count
    
    all_items = []
    total_files = 0
    
    abs_base = os.path.abspath(BASE_DIR)
    items, total_files = list_files_recursive(abs_base, abs_base)
    all_items.extend(items)
    
    organized_items = {}
    
    for item in all_items:
        if item["type"] == "dir":
            dir_rel_path = item["rel_path"]
            if dir_rel_path == "":
                dir_rel_path = "root"
            
            if dir_rel_path not in organized_items:
                organized_items[dir_rel_path] = {
                    "type": "dir",
                    "items": [],
                    "full_path": item["full_path"],
                    "name": os.path.basename(item["full_path"]) if dir_rel_path != "root" else "root",
                    "has_images": False
                }
    
    for item in all_items:
        if item["type"] == "file":
            parent_dir = os.path.dirname(item["rel_path"])
            if parent_dir == "":
                parent_dir = "root"
            
            if parent_dir not in organized_items:
                parent_full_path = os.path.join(abs_base, parent_dir) if parent_dir != "root" else abs_base
                organized_items[parent_dir] = {
                    "type": "dir",
                    "items": [],
                    "full_path": parent_full_path,
                    "name": parent_dir if parent_dir != "root" else "root",
                    "has_images": False
                }
            
            organized_items[parent_dir]["items"].append(item)
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
            if item["ext"] in image_extensions:
                organized_items[parent_dir]["has_images"] = True
    
    return render_template_string(NEW_MAIN_TEMPLATE, 
                                folders=organized_items, 
                                user_level=user_level,
                                total_files=total_files)
    
@explorer.route("/files", methods=["GET", "POST"])
def list_files():
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

@explorer.route("/webusers", methods=["GET", "POST"])
@login_required
@level_required(3)
def manage_web_users():
    try:
        with open(WEBACCESS_FILE, "r", encoding="utf-8") as f:
            web_users = json.load(f)
    except:
        web_users = {}
    
    current_user_id = session.get("user_id")
    current_user_level = session.get("user_level", 0)
    current_user_password = session.get("user_password", "")
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "create":
            if current_user_level < 4:
                abort(403)
            
            new_id = request.form.get("new_id", "").strip()
            new_user = request.form.get("new_user", "").strip()
            new_pass = request.form.get("new_pass", "").strip()
            
            if not new_id or not new_user or not new_pass:
                return "Todos los campos son requeridos", 400
            
            if new_id in web_users:
                return "ID ya existe", 400
            
            web_users[new_id] = {
                "user": new_user,
                "pass": new_pass
            }
            
            with open(WEBACCESS_FILE, "w", encoding="utf-8") as f:
                json.dump(web_users, f, indent=2)
            
            return redirect("/webusers")
        
        elif action == "delete":
            user_id_to_delete = request.form.get("user_id_to_delete", "").strip()
            
            if not user_id_to_delete or user_id_to_delete not in web_users:
                return "Usuario no encontrado", 404
            
            target_level = get_user_level(user_id_to_delete)
            
            if current_user_level < 5:
                if target_level >= current_user_level:
                    return "No tienes permiso para borrar este usuario", 403
            
            del web_users[user_id_to_delete]
            
            with open(WEBACCESS_FILE, "w", encoding="utf-8") as f:
                json.dump(web_users, f, indent=2)
            
            return redirect("/webusers")
        
        elif action == "update":
            user_id_to_update = request.form.get("user_id_to_update", "").strip()
            new_username = request.form.get("new_username", "").strip()
            new_password = request.form.get("new_password", "").strip()
            
            if user_id_to_update not in web_users:
                return "Usuario no encontrado", 404
            
            target_level = get_user_level(user_id_to_update)
            
            if current_user_level < 5:
                if target_level >= current_user_level:
                    return "No tienes permiso para modificar este usuario", 403
            
            if new_username:
                web_users[user_id_to_update]["user"] = new_username
            if new_password:
                web_users[user_id_to_update]["pass"] = new_password
            
            with open(WEBACCESS_FILE, "w", encoding="utf-8") as f:
                json.dump(web_users, f, indent=2)
            
            return redirect("/webusers")
    
    filtered_users = {}
    for uid, creds in web_users.items():
        target_level = get_user_level(uid)
        
        if current_user_level == 6:
            filtered_users[uid] = {
                "user": creds["user"],
                "pass": creds["pass"],
                "level": target_level
            }
        elif current_user_level == 5:
            if target_level < 6:
                filtered_users[uid] = {
                    "user": creds["user"],
                    "pass": creds["pass"],
                    "level": target_level
                }
        elif current_user_level == 4:
            if target_level < 5:
                filtered_users[uid] = {
                    "user": creds["user"],
                    "pass": creds["pass"],
                    "level": target_level
                }
        elif current_user_level == 3:
            if target_level < 4:
                filtered_users[uid] = {
                    "user": creds["user"],
                    "pass": creds["pass"] if uid == current_user_id else "****",
                    "level": target_level
                }
    
    return render_template_string(WEBUSERS_TEMPLATE, 
                                 users=filtered_users, 
                                 current_user_level=current_user_level,
                                 current_user_id=current_user_id)

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

@explorer.route("/gallery_slideshow", methods=["GET", "POST"])
@login_required
def gallery_slideshow():
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
@level_required(1)
def utils_page():
    return render_template_string(UTILS_TEMPLATE)

@explorer.route("/downloads", methods=["GET", "POST"])
@login_required
@level_required(1)
def downloads_page():
    cleanup_old_downloads()
    torrent_downloads = get_download_progress()
    
    current_time = datetime.now()
    
    with doujin_lock:
        to_delete = []
        for download_id, download_info in doujin_downloads.items():
            if download_info.get("state") in ["completed", "error"] and "end_time" in download_info:
                end_time = datetime.fromisoformat(download_info["end_time"])
                if (current_time - end_time).total_seconds() > 3600:
                    to_delete.append(download_id)
        
        for download_id in to_delete:
            del doujin_downloads[download_id]
    
    with mega_lock:
        to_delete = []
        for download_id, download_info in mega_downloads.items():
            if download_info.get("state") in ["completed", "error"] and "end_time" in download_info:
                end_time = datetime.fromisoformat(download_info["end_time"])
                if (current_time - end_time).total_seconds() > 3600:
                    to_delete.append(download_id)
        
        for download_id in to_delete:
            del mega_downloads[download_id]
    
    with manga_lock:
        to_delete = []
        for download_id, download_info in manga_downloads.items():
            if download_info.get("state") in ["completed", "error"] and "end_time" in download_info:
                end_time = datetime.fromisoformat(download_info["end_time"])
                if (current_time - end_time).total_seconds() > 3600:
                    to_delete.append(download_id)
        
        for download_id in to_delete:
            del manga_downloads[download_id]
    
    return render_template_string(DOWNLOADS_TEMPLATE, 
                                downloads=torrent_downloads, 
                                doujin_downloads=doujin_downloads,
                                mega_downloads=mega_downloads,
                                manga_downloads=manga_downloads)

@explorer.route("/api/downloads/delete", methods=["POST"])
@login_required
@level_required(1)
def delete_download():
    try:
        data = request.json
        download_id = data.get("download_id")
        download_type = data.get("type")
        
        if not download_id or not download_type:
            return jsonify({"success": False, "message": "Faltan parámetros"}), 400
        
        deleted = False
        
        if download_type == "torrent":
            from command.torrets_tools import delete_download as delete_torrent
            deleted = delete_torrent(download_id)
        elif download_type == "doujin":
            with doujin_lock:
                if download_id in doujin_downloads:
                    del doujin_downloads[download_id]
                    deleted = True
        elif download_type == "mega":
            with mega_lock:
                if download_id in mega_downloads:
                    del mega_downloads[download_id]
                    deleted = True
        elif download_type == "manga":
            with manga_lock:
                if download_id in manga_downloads:
                    del manga_downloads[download_id]
                    deleted = True
        else:
            return jsonify({"success": False, "message": "Tipo de descarga no válido"}), 400
        
        if deleted:
            return jsonify({"success": True, "message": "Descarga eliminada"})
        else:
            return jsonify({"success": False, "message": "Descarga no encontrada"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@explorer.route("/api/downloads/delete-all", methods=["POST"])
@login_required
@level_required(1)
def delete_all_downloads():
    try:
        download_type = request.json.get("type", "all")
        deleted_count = 0
        
        if download_type in ["all", "torrent"]:
            cleanup_old_downloads()
        
        if download_type in ["all", "doujin"]:
            with doujin_lock:
                deleted_count += len(doujin_downloads)
                doujin_downloads.clear()
        
        if download_type in ["all", "mega"]:
            with mega_lock:
                deleted_count += len(mega_downloads)
                mega_downloads.clear()
        
        if download_type in ["all", "manga"]:
            with manga_lock:
                deleted_count += len(manga_downloads)
                manga_downloads.clear()
        
        return jsonify({
            "success": True, 
            "message": f"Eliminadas {deleted_count} descargas",
            "count": deleted_count
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@explorer.route("/api/downloads", methods=["GET", "POST"])
@login_required
@level_required(1)
def api_downloads():
    cleanup_old_downloads()
    downloads = get_download_progress()
    return jsonify({
        "torrents": downloads, 
        "doujins": doujin_downloads, 
        "mega": mega_downloads,
        "manga": manga_downloads
    })

@explorer.route("/download", methods=["GET", "POST"])
def download():
    check_token_auth()
    if not session.get("logged_in"):
        return redirect("/login")
    
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
@level_required(1)
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

@explorer.route("/upload_file", methods=["POST"])
@login_required
@level_required(1)
def handle_file_upload():
    try:
        destination_path = request.form.get("destination_path", "").strip()
        custom_name = request.form.get("custom_name", "").strip()
        files = request.files.getlist("files")
        
        if not files or not any(f.filename for f in files):
            return jsonify({"success": False, "message": "Seleccionar un archivo es obligatorio"}), 400
        
        if destination_path:
            if not validate_path(os.path.join(BASE_DIR, destination_path)):
                return jsonify({"success": False, "message": "Ruta destino no válida"}), 400
            save_dir = os.path.join(BASE_DIR, destination_path)
        else:
            save_dir = BASE_DIR
        
        os.makedirs(save_dir, exist_ok=True)
        
        uploaded_files = []
        for file in files:
            if file and file.filename:
                if custom_name and len(files) == 1:
                    filename = custom_name
                else:
                    filename = file.filename
                
                save_path = os.path.join(save_dir, filename)
                
                counter = 1
                while os.path.exists(save_path):
                    name, ext = os.path.splitext(filename)
                    save_path = os.path.join(save_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                file.save(save_path)
                uploaded_files.append(os.path.basename(save_path))
        
        return jsonify({
            "success": True,
            "message": f"Subidos {len(uploaded_files)} archivos",
            "files": uploaded_files
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@explorer.route("/download_file", methods=["POST"])
@login_required
@level_required(1)
def handle_file_download():
    try:
        download_url = request.form.get("download_url", "").strip()
        destination_path = request.form.get("destination_path", "").strip()
        custom_name = request.form.get("custom_name", "").strip()
        
        if not download_url:
            return jsonify({"success": False, "message": "El enlace está vacío"}), 400
        
        if destination_path:
            if not validate_path(os.path.join(BASE_DIR, destination_path)):
                return jsonify({"success": False, "message": "Ruta destino no válida"}), 400
            save_dir = os.path.join(BASE_DIR, destination_path)
        else:
            save_dir = BASE_DIR
        
        os.makedirs(save_dir, exist_ok=True)
        
        if custom_name:
            filename = custom_name
        else:
            filename = download_url.split("/")[-1].split("?")[0]
            if not filename:
                filename = "downloaded_file"
        
        save_path = os.path.join(save_dir, filename)
        
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(save_path)
        
        return jsonify({
            "success": True,
            "message": f"Archivo descargado: {filename} ({file_size} bytes)",
            "filename": filename,
            "size": file_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@explorer.route("/mega", methods=["GET", "POST"])
@login_required
@level_required(1)
def handle_mega():
    if request.method == "POST":
        mega_link = request.form.get("mega_link", "").strip()
    else:
        mega_link = request.args.get("mega_link", "").strip()
        
    if not mega_link or not mega_link.startswith("https://mega.nz/"):
        return "<h3>❌ Enlace MEGA no válido.</h3>", 400

    import pytz
    habana_tz = pytz.timezone('America/Havana')
    timestamp_folder = datetime.now(habana_tz).strftime("%Y%m%d%H%M%S")
    download_id = timestamp_folder
    
    with mega_lock:
        mega_downloads[download_id] = {
            "state": "processing",
            "link": mega_link,
            "progress": 0,
            "start_time": datetime.now().isoformat(),
            "message": "Iniciando descarga..."
        }
    
    def run_mega_download():
        try:
            current_file_path = os.path.abspath(__file__)
            current_dir = os.path.dirname(current_file_path)
            desmega_path = os.path.join(current_dir, "command", "desmega")
            
            if not os.path.exists(desmega_path):
                project_root = os.path.dirname(current_dir)
                desmega_path = os.path.join(project_root, "command", "desmega")
            
            if not os.path.exists(desmega_path):
                raise FileNotFoundError(f"No se encontró desmega en: {desmega_path}")
            
            os.chmod(desmega_path, 0o755)
            
            output_dir = os.path.join(BASE_DIR, "mega_dl", download_id)
            os.makedirs(output_dir, exist_ok=True)
            
            with mega_lock:
                mega_downloads[download_id]["output_dir"] = output_dir
                mega_downloads[download_id]["message"] = "Ejecutando desmega..."
                mega_downloads[download_id]["progress"] = 10
            
            process = subprocess.Popen(
                [desmega_path, mega_link, "--path", output_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            with mega_lock:
                mega_downloads[download_id]["progress"] = 90
                mega_downloads[download_id]["message"] = "Procesando archivos descargados..."
            
            if process.returncode != 0:
                with mega_lock:
                    mega_downloads[download_id]["state"] = "error"
                    mega_downloads[download_id]["error"] = stderr
                return
            
            files = [f for f in os.listdir(output_dir) if not f.startswith('.megatmp')]
            if not files:
                with mega_lock:
                    mega_downloads[download_id]["state"] = "error"
                    mega_downloads[download_id]["error"] = "No se encontraron archivos descargados"
                return
            
            with mega_lock:
                mega_downloads[download_id]["state"] = "completed"
                mega_downloads[download_id]["end_time"] = datetime.now().isoformat()
                mega_downloads[download_id]["progress"] = 100
                mega_downloads[download_id]["message"] = f"Descarga completada. {len(files)} archivos descargados en: {output_dir}"
            
        except Exception as e:
            with mega_lock:
                mega_downloads[download_id]["state"] = "error"
                mega_downloads[download_id]["error"] = str(e)
    
    Thread(target=run_mega_download, daemon=True).start()
    
    response_msg = "<h3>✅ Iniciando descarga desde MEGA</h3>"
    response_msg += f"<p>Enlace: {mega_link[:50]}...</p>"
    response_msg += "<p>Puedes ver el progreso en la <a href='/downloads'>página de descargas</a></p>"
    return response_msg

@explorer.route("/magnet", methods=["GET", "POST"])
@login_required
@level_required(1)
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
@level_required(4)
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
            
        return redirect("/")
    except Exception as e:
        return f"<h3>Error al eliminar: {e}</h3>", 500

@explorer.route("/delete_folder", methods=["POST"])
@login_required
@level_required(4)
def delete_folder():
    path = request.form.get("path")
    
    if not path or not validate_path(path):
        return "<h3>❌ Ruta no válida.</h3>", 400
    
    if not os.path.isdir(path):
        return "<h3>❌ No es una carpeta.</h3>", 400
    
    folder_name = os.path.basename(path)
    
    try:
        shutil.rmtree(path)
        return redirect("/")
    except Exception as e:
        return f"<h3>Error al eliminar carpeta: {e}</h3>", 500

@explorer.route("/delete_empty_folders", methods=["POST"])
@login_required
@level_required(4)
def delete_empty_folders_route():
    try:
        deleted_count = delete_empty_folders(BASE_DIR)
        return f"<h3>✅ Eliminadas {deleted_count} carpetas vacías</h3>"
    except Exception as e:
        return f"<h3>Error al eliminar carpetas vacías: {e}</h3>", 500

@explorer.route("/delete_multiple", methods=["POST"])
@login_required
@level_required(4)
def delete_multiple():
    items = request.form.getlist("items[]")
    
    if not items:
        return "<h3>❌ No se seleccionaron elementos.</h3>", 400
    
    deleted_count = 0
    errors = []
    
    for item_path in items:
        if not validate_path(item_path):
            errors.append(f"Ruta no válida: {item_path}")
            continue
        
        if not os.path.exists(item_path):
            errors.append(f"No existe: {item_path}")
            continue
        
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
                deleted_count += 1
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                deleted_count += 1
        except Exception as e:
            errors.append(f"Error eliminando {item_path}: {str(e)}")
    
    if errors:
        return f"<h3>Eliminados {deleted_count} elementos, con errores:</h3><p>{'<br>'.join(errors)}</p>"
    
    return redirect("/")

@explorer.route("/compress", methods=["GET", "POST"])
@login_required
@level_required(4)
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

@explorer.route("/compress_multiple", methods=["POST"])
@login_required
@level_required(4)
def compress_multiple():
    archive_name = request.form.get("archive_name", "").strip()
    selected = request.form.getlist("selected[]")
    
    if not archive_name:
        return "<h3>❌ Debes proporcionar un nombre para el archivo.</h3>", 400
    
    if not selected:
        return "<h3>❌ No se seleccionaron elementos.</h3>", 400
    
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
        
        return redirect("/")
    except Exception as e:
        return f"<h3>❌ Error al comprimir: {e}</h3>", 500

@explorer.route("/extract", methods=["GET", "POST"])
@login_required
@level_required(4)
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

from command.hapi.nh import create_nhentai_cbz

@explorer.route("/api/d3h/<code>")
@login_required
def api_download_3hentai(code):
    try:
        cbz_path, filename = create_3hentai_cbz(code)
        return serve_and_clean(cbz_path)
    except Exception as e:
        return jsonify({"error": f"Error al descargar desde 3hentai: {str(e)}"}), 500

@explorer.route("/api/dnh/<int:code>")
@login_required
def api_download_nhentai(code):
    try:
        cbz_path, filename = create_nhentai_cbz(code)
        return serve_and_clean(cbz_path)
    except Exception as e:
        return jsonify({"error": f"Error al descargar desde nhentai: {str(e)}"}), 500

@explorer.route("/api/snh/", methods=["GET"])
@explorer.route("/api/snh/<path:search_term>", methods=["GET"])
@login_required
def search_nhentai(search_term=None):
    if request.method == "GET" and not search_term:
        search_term = request.args.get("q", "").strip()
    
    if not search_term:
        return render_template_string(SEARCH_NH_TEMPLATE, 
                                    results=[], 
                                    search_term="", 
                                    current_page=1,
                                    total_pages=1)

    page = request.args.get("p", "1")
    try:
        page = int(page)
    except:
        page = 1
    
    try:
        data = scrape_nhentai_with_selenium(search_term, page)
        results = data.get("results", [])
        total_pages = data.get("total_pages", 1)
    except Exception as e:
        results = []
        total_pages = 1
    
    return render_template_string(SEARCH_NH_TEMPLATE, 
                                results=results, 
                                search_term=search_term, 
                                current_page=page,
                                total_pages=total_pages)

from command.get_files.search_3h import scrape_3hentai_search

@explorer.route("/api/s3h/", methods=["GET"])
@explorer.route("/api/s3h/<path:search_term>", methods=["GET"])
@login_required
def search_3hentai(search_term=None):
    if request.method == "GET" and not search_term:
        search_term = request.args.get("q", "").strip()
    
    if not search_term:
        return render_template_string(SEARCH_3H_TEMPLATE, 
                                    results=[], 
                                    search_term="", 
                                    current_page=1,
                                    total_pages=1)
    
    page = request.args.get("p", "1")
    try:
        page = int(page)
    except:
        page = 1
    
    try:
        data = scrape_3hentai_search(search_term, page)
        
        results = []
        if "resultados" in data and isinstance(data["resultados"], dict):
            for key, result in data["resultados"].items():
                results.append({
                    "code": result.get("codigo", ""),
                    "name": result.get("titulo", ""),
                    "image_links": [result.get("imagen", "")]
                })
        
        total_pages = data.get("total_paginas", 1)
        total_results = data.get("total_resultados", 0)
        
    except Exception as e:
        results = []
        total_pages = 1
        total_results = 0
    
    return render_template_string(SEARCH_3H_TEMPLATE, 
                                results=results, 
                                search_term=search_term, 
                                current_page=page,
                                total_pages=total_pages,
                                total_results=total_results)
    
@explorer.route("/api/proxy-image")
@login_required
def proxy_image():
    import requests
    from io import BytesIO
    
    image_url = request.args.get('url')
    if not image_url:
        abort(400)
    
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        return send_file(
            BytesIO(response.content),
            mimetype=response.headers.get('content-type', 'image/jpeg'),
            as_attachment=False
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@explorer.route("/api/vnh/<int:code>")
@login_required
def view_nhentai(code):
    try:
        from command.get_files.nh_selenium import scrape_nhentai
        result = scrape_nhentai(code)
        
        if not result.get("title") or not result.get("links"):
            return "<h3>❌ No se pudo obtener la información de la galería</h3>", 404
        
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', '', result["title"])[:100]
        
        return render_template_string(VIEW_NH_TEMPLATE, 
                                    code=code,
                                    title=result["title"],
                                    clean_title=clean_title,
                                    tags=result.get("tags", {}),
                                    image_links=result.get("links", []),
                                    cover_image=result.get("links", [""])[0] if result.get("links") else "")
    except Exception as e:
        return f"<h3>Error al cargar la galería: {str(e)}</h3>", 500

@explorer.route("/api/v3h/<code>")
@login_required
def view_3hentai(code):
    try:
        from command.get_files.h3_links import obtener_titulo_y_imagenes
        
        result = obtener_titulo_y_imagenes(code, cover=False)
        
        if not result.get("texto") or not result.get("imagenes"):
            return "<h3>No se pudo obtener la información de la galería 3Hentai</h3>", 404
        
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', '', result["texto"])[:100]
        
        return render_template_string(VIEW_3H_TEMPLATE, 
                                    code=code,
                                    title=result["texto"],
                                    clean_title=clean_title,
                                    tags=result.get("tags", {}),
                                    image_links=result.get("imagenes", []),
                                    cover_image=result.get("imagenes", [""])[0] if result.get("imagenes") else "",
                                    total_pages=result.get("total_paginas", 0))
    except Exception as e:
        return f"<h3>Error al cargar la galería 3Hentai: {str(e)}</h3>", 500

@explorer.route("/api/create-cbz", methods=["POST"])
@login_required
def api_create_cbz():
    try:
        if not request.files:
            return jsonify({"error": "No se recibieron archivos"}), 400
        
        title = request.form.get("title", "doujin")
        code = request.form.get("code", "")
        
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', '', title)[:100]
        
        import tempfile
        import zipfile
        import os
        
        temp_dir = tempfile.mkdtemp()
        cbz_filename = f"{clean_title}_{code}.cbz" if code else f"{clean_title}.cbz"
        cbz_path = os.path.join(temp_dir, cbz_filename)
        
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/webp': '.webp',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff'
        }
        
        with zipfile.ZipFile(cbz_path, 'w') as zipf:
            file_index = 0
            
            for key in sorted(request.files.keys()):
                file_storage = request.files[key]
                if file_storage and file_storage.filename:
                    mime_type = file_storage.mimetype
                    
                    if mime_type in mime_to_ext:
                        ext = mime_to_ext[mime_type]
                    else:
                        original_filename = file_storage.filename.lower()
                        if any(original_filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']):
                            _, ext = os.path.splitext(original_filename)
                        else:
                            ext = '.jpg'
                    
                    file_index += 1
                    zip_filename = f"{str(file_index).zfill(3)}{ext}"
                    
                    file_data = file_storage.read()
                    zipf.writestr(zip_filename, file_data)
        
        if file_index == 0:
            return jsonify({"error": "No se pudieron procesar los archivos"}), 400
        
        response = send_file(
            cbz_path,
            as_attachment=True,
            download_name=cbz_filename,
            mimetype='application/x-cbz'
        )
        
        @response.call_on_close
        def cleanup():
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
        
        return response
        
    except Exception as e:
        return jsonify({"error": f"Error al crear CBZ: {str(e)}"}), 500

@explorer.route("/rename", methods=["GET", "POST"])
@login_required
@level_required(4)
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
        return redirect("/")
    except Exception as e:
        return f"<h3>Error al renombrar: {e}</h3>", 500 

@explorer.route("/move_items", methods=["POST"])
@login_required
@level_required(4)
def move_items():
    items = request.form.getlist("items[]")
    target_folder = request.form.get("target_folder", "").strip()
    
    if not items:
        return "<h3>❌ No se seleccionaron elementos.</h3>", 400
    
    if not target_folder:
        return "<h3>❌ No se especificó la carpeta destino.</h3>", 400
    
    target_path = os.path.join(BASE_DIR, target_folder.lstrip('/'))
    
    if not validate_path(target_path):
        return "<h3>❌ Ruta destino no válida.</h3>", 400
    
    os.makedirs(target_path, exist_ok=True)
    
    moved_count = 0
    errors = []
    
    for item_path in items:
        if not validate_path(item_path):
            errors.append(f"Ruta origen no válida: {item_path}")
            continue
        
        if not os.path.exists(item_path):
            errors.append(f"No existe: {item_path}")
            continue
        
        item_name = os.path.basename(item_path)
        target_item_path = os.path.join(target_path, item_name)
        
        try:
            shutil.move(item_path, target_item_path)
            moved_count += 1
        except Exception as e:
            errors.append(f"Error moviendo {item_name}: {str(e)}")
    
    if errors:
        return f"<h3>Movidos {moved_count} elementos, con errores:</h3><p>{'<br>'.join(errors)}</p>"
    
    return redirect("/")

@explorer.route("/api/folders", methods=["GET"])
@login_required
@level_required(4)
def api_folders():
    try:
        folders = get_all_folders()
        return jsonify(folders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@explorer.route("/api/check_folder", methods=["GET"])
@login_required
@level_required(4)
def api_check_folder():
    path = request.args.get("path")
    
    if not path or not validate_path(path):
        return jsonify({"error": "Ruta no válida"}), 400
    
    if not os.path.isdir(path):
        return jsonify({"error": "No es una carpeta"}), 400
    
    has_content = False
    
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            has_content = True
            break
        elif os.path.isdir(item_path):
            if not check_empty_folder(item_path):
                has_content = True
                break
    
    return jsonify({"has_content": has_content})

@explorer.route("/help", methods=["GET"])
def help_page():
    base_url = request.host_url.rstrip('/')
    help_text = f"# Guía de uso con CURL\n\n## Autenticación\nPrimero genera un token de autenticación:\ncurl \"{base_url}/auth?u=TU_USUARIO&p=TU_CONTRASEÑA\"\n\nO usa autenticación básica en cada request:\ncurl -u \"usuario:contraseña\" {base_url}/files\n\n## Listar archivos recursivamente\ncurl \"{base_url}/files?token=TU_TOKEN\"\n# o\ncurl -u \"usuario:contraseña\" {base_url}/files\n\n## Descargar archivo\ncurl \"{base_url}/download?path=ruta/archivo.jpg&token=TU_TOKEN\" \\\n  -o \"archivo.jpg\"\n\n## Descargar desde 3Hentai (descarga directa)\ncurl \"{base_url}/api/d3h/CODIGO?token=TU_TOKEN\" \\\n  -o \"archivo.cbz\"\n\n## Crear CBZ desde códigos\n\n### Un solo código (nhentai, hentai3, hitomi)\n# nhentai\ncurl \"{base_url}/crear_cbz?codigo=177013&tipo=nh&token=TU_TOKEN\"\n\n# hentai3\ncurl \"{base_url}/crear_cbz?codigo=12345&tipo=h3&token=TU_TOKEN\"\n\n# hitomi\ncurl \"{base_url}/crear_cbz?codigo=abc123&tipo=hito&token=TU_TOKEN\"\n\n### Múltiples códigos (solo nhentai y hentai3)\n# nhentai múltiple\ncurl \"{base_url}/crear_cbz?codigo=177013,228922,309437&tipo=nh&token=TU_TOKEN\"\n\n# hentai3 múltiple\ncurl \"{base_url}/crear_cbz?codigo=12345,67890,54321&tipo=h3&token=TU_TOKEN\"\n\n## Descargar desde magnet link\ncurl \"{base_url}/magnet?magnet=magnet:?xt=urn:btih:TU_HASH&token=TU_TOKEN\"\n\n## Descargar desde MEGA\ncurl \"{base_url}/mega?mega_link=https://mega.nz/...&token=TU_TOKEN\"\n\n## Renombrar archivo/directorio\ncurl \"{base_url}/rename?old_path=ruta/vieja/archivo.txt&new_name=archivo_nuevo.txt&token=TU_TOKEN\"\n\n## Eliminar archivo/directorio\ncurl \"{base_url}/delete?path=ruta/a/eliminar&token=TU_TOKEN\"\n\n## Subir archivo (requiere POST)\ncurl -X POST \"{base_url}/upload?token=TU_TOKEN\" \\\n  -F \"file=@archivo_local.jpg\"\n\n## Notas:\n- Reemplaza `TU_TOKEN` con el token obtenido del endpoint `/auth`\n- Reemplaza `TU_USUARIO` y `TU_CONTRASEÑA` con tus credenciales\n- Las rutas deben estar dentro del directorio base permitido\n- Para hitomi solo se permite un código a la vez"
    return help_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}


from command.manga_downloader import MangaDexDownloader

manga_downloader = MangaDexDownloader()

@explorer.route("/manga", methods=["GET"])
@login_required
@level_required(1)
def manga_page():
    return render_template_string(MANGA_TEMPLATE)

@explorer.route("/manga/download", methods=["POST"])
@login_required
@level_required(1)
def manga_download():
    try:
        url = request.form.get("url", "").strip()
        download_range = request.form.get("range", "all")
        format_type = request.form.get("format", "cbz-volume")
        start_value = request.form.get("start", "").strip()
        end_value = request.form.get("end", "").strip()
        
        if not url:
            return jsonify({"success": False, "message": "La URL está vacía"}), 400
        
        if not url.startswith("https://mangadex.org/"):
            return jsonify({"success": False, "message": "URL inválida. Debe comenzar con https://mangadex.org/"}), 400
        
        download_id = manga_downloader.start_download(
            url=url,
            download_range=download_range,
            format_type=format_type,
            start_value=start_value if start_value else None,
            end_value=end_value if end_value else None
        )
        
        with manga_lock:
            manga_downloads[download_id] = manga_downloader.get_download_progress(download_id)
        
        return jsonify({
            "success": True,
            "message": "Descarga iniciada correctamente",
            "download_id": download_id
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@explorer.route("/manga/status", methods=["GET"])
@login_required
@level_required(1)
def manga_status():
    download_id = request.args.get("id")
    
    if download_id:
        status = manga_downloader.get_download_progress(download_id)
        if download_id in manga_downloads:
            manga_downloads[download_id] = status
        return jsonify(status)
    else:
        all_downloads = manga_downloader.get_all_downloads()
        with manga_lock:
            for download_id, download_info in all_downloads.items():
                manga_downloads[download_id] = download_info
        return jsonify(all_downloads)

@explorer.route("/manga/cleanup", methods=["POST"])
@login_required
@level_required(4)
def manga_cleanup():
    try:
        manga_downloader.cleanup_old_downloads()
        return jsonify({"success": True, "message": "Limpieza completada"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@explorer.route("/create_cbz_from_folder", methods=["POST"])
@login_required
@level_required(4)
def create_cbz_from_folder():
    folder_path = request.form.get("folder_path")
    
    if not folder_path or not validate_path(folder_path):
        return "<h3>❌ Ruta no válida.</h3>", 400
    
    if not os.path.isdir(folder_path):
        return "<h3>❌ No es una carpeta.</h3>", 400
    
    folder_name = os.path.basename(folder_path)
    parent_dir = os.path.dirname(folder_path)
    
    if parent_dir == BASE_DIR:
        return "<h3>❌ No se puede crear CBZ en el directorio raíz.</h3>", 400
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    image_files = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(os.path.join(root, file))
    
    if not image_files:
        return f"<h3>❌ No se encontraron imágenes en la carpeta '{folder_name}'.</h3>", 400
    
    image_files.sort(key=natural_sort_key)
    
    cbz_path = os.path.join(parent_dir, f"{folder_name}.cbz")
    
    counter = 1
    while os.path.exists(cbz_path):
        cbz_path = os.path.join(parent_dir, f"{folder_name}_{counter}.cbz")
        counter += 1
    
    try:
        with zipfile.ZipFile(cbz_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            image_counter = 1
            for image_file in image_files:
                rel_path = os.path.relpath(image_file, folder_path)
                ext = os.path.splitext(image_file)[1].lower()
                zip_filename = f"{str(image_counter).zfill(3)}{ext}"
                zipf.write(image_file, zip_filename)
                image_counter += 1
        
        return f"<h3>✅ CBZ creado exitosamente: {os.path.basename(cbz_path)}</h3><p>Contiene {len(image_files)} imágenes.</p>"
    
    except Exception as e:
        return f"<h3>❌ Error al crear CBZ: {str(e)}</h3>", 500

@explorer.route("/merge_cbz", methods=["POST"])
@login_required
@level_required(4)
def merge_cbz():
    cbz_files = request.form.getlist("cbz_files[]")
    output_name = request.form.get("output_name", "").strip()
    
    if not cbz_files or len(cbz_files) < 2:
        return "<h3>❌ Selecciona al menos 2 archivos CBZ.</h3>", 400
    
    if not output_name or not output_name.endswith('.cbz'):
        return "<h3>❌ Nombre de salida inválido. Debe terminar en .cbz</h3>", 400
    
    for cbz_file in cbz_files:
        if not validate_path(cbz_file):
            return f"<h3>❌ Ruta no válida: {cbz_file}</h3>", 400
        if not os.path.isfile(cbz_file):
            return f"<h3>❌ Archivo no encontrado: {cbz_file}</h3>", 404
    
    parent_dir = os.path.dirname(cbz_files[0])
    output_path = os.path.join(parent_dir, output_name)
    
    counter = 1
    while os.path.exists(output_path):
        name, ext = os.path.splitext(output_name)
        output_path = os.path.join(parent_dir, f"{name}_{counter}{ext}")
        counter += 1
    
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as output_zip:
            image_counter = 1
            
            for cbz_file in cbz_files:
                try:
                    with zipfile.ZipFile(cbz_file, 'r') as input_zip:
                        for file_info in input_zip.infolist():
                            if file_info.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                                ext = os.path.splitext(file_info.filename)[1].lower()
                                if not ext:
                                    ext = '.jpg'
                                
                                new_filename = f"{str(image_counter).zfill(3)}{ext}"
                                
                                try:
                                    file_data = input_zip.read(file_info.filename)
                                    output_zip.writestr(new_filename, file_data)
                                    image_counter += 1
                                except:
                                    continue
                except:
                    continue
        
        return f"<h3>✅ CBZ combinado creado exitosamente: {os.path.basename(output_path)}</h3><p>Contiene {image_counter-1} imágenes de {len(cbz_files)} CBZs.</p>"
    
    except Exception as e:
        return f"<h3>❌ Error al combinar CBZs: {str(e)}</h3>", 500

@explorer.route("/api/list_cbz", methods=["GET"])
@login_required
@level_required(4)
def api_list_cbz():
    path_param = request.args.get("path", "")
    
    if not path_param:
        abs_path = os.path.abspath(BASE_DIR)
    else:
        abs_path = os.path.abspath(os.path.join(BASE_DIR, path_param.lstrip('/')))
    
    if not validate_path(abs_path):
        return jsonify({"error": "Ruta no válida"}), 400
    
    if not os.path.exists(abs_path):
        return jsonify([])
    
    if not os.path.isdir(abs_path):
        abs_path = os.path.dirname(abs_path)
    
    cbz_files = []
    
    try:
        for item in os.listdir(abs_path):
            item_path = os.path.join(abs_path, item)
            if os.path.isfile(item_path) and item.lower().endswith('.cbz'):
                cbz_files.append({
                    "name": item,
                    "path": item_path,
                    "size": os.path.getsize(item_path)
                })
    except FileNotFoundError:
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    cbz_files.sort(key=lambda x: natural_sort_key(x["name"]))
    return jsonify(cbz_files)

@explorer.route("/create", methods=["GET"], defaults={'folder_name': None, 'subfolder_name': None})
@explorer.route("/create/<folder_name>", methods=["GET"], defaults={'subfolder_name': None})
@explorer.route("/create/<folder_name>/<subfolder_name>", methods=["GET"])
@login_required
@level_required(4)
def create_folder(folder_name=None, subfolder_name=None):
    if folder_name is not None:
        parent_path = os.path.join(BASE_DIR, folder_name)
        if subfolder_name is not None:
            target_path = os.path.join(parent_path, subfolder_name)
        else:
            target_path = parent_path
        if not validate_path(target_path):
            return f"<h3>❌ Error: La ruta de creación '{target_path}' no es válida.</h3>", 403
        try:
            os.makedirs(target_path, exist_ok=True)
            created_name = f"{folder_name}/{subfolder_name}" if subfolder_name else folder_name
            return f"<h3>✅ Carpeta '{created_name}' creada exitosamente en vault_files.</h3>"
        except Exception as e:
            return f"<h3>❌ Error al crear la carpeta: {e}</h3>", 500

    CREATE_TEMPLATE = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crear Carpeta</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h2 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
            label { display: block; margin: 15px 0 5px; color: #555; font-weight: bold; }
            input[type="text"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #4CAF50; color: white; border: none; padding: 12px 20px; margin-top: 20px; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; }
            button:hover { background: #45a049; }
            .note { background: #e8f5e9; padding: 10px; border-radius: 5px; margin-top: 20px; font-size: 0.9em; color: #2e7d32; }
            .url-example { font-family: monospace; background: #f1f1f1; padding: 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📁 Crear Nueva Carpeta</h2>
            <form method="POST" action="/create">
                <label for="folder_name">Nombre de la carpeta:</label>
                <input type="text" id="folder_name" name="folder_name" placeholder="Ej: mis_documentos" required>
                <label for="folder_path">Ruta (opcional):</label>
                <input type="text" id="folder_path" name="folder_path" placeholder="Ej: proyectos/2024">
                <small>Dejar vacío para crear en la raíz de vault_files</small>
                <button type="submit">Crear Carpeta</button>
            </form>
            <div class="note">
                <p><strong>Nota:</strong> También puedes crear carpetas directamente mediante URL:</p>
                <ul>
                    <li>Crear <span class="url-example">example</span> en raíz: <br><span class="url-example">/create/example</span></li>
                    <li>Crear <span class="url-example">step2</span> dentro de <span class="url-example">example</span>: <br><span class="url-example">/create/example/step2</span></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(CREATE_TEMPLATE)

class TelegramSender:
    def __init__(self):
        self.token = None
        self.base_url = None
        self._initialize()
    
    def _initialize(self):
        try:
            from arg_parser import get_args
            args = get_args()
            self.token = args.bot_token
            if self.token:
                self.base_url = f"https://api.telegram.org/bot{self.token}"
            else:
                self.base_url = None
        except Exception as e:
            self.token = None
            self.base_url = None
    
    def is_available(self):
        return self.base_url is not None
    
    def _send_request(self, method, data=None, files=None):
        if not self.base_url:
            raise ValueError("Bot de Telegram no configurado")
        url = f"{self.base_url}/{method}"
        if files:
            return requests.post(url, data=data, files=files)
        return requests.post(url, json=data)
    
    def _prepare_file(self, file_value, field_name, data, files):
        if file_value.startswith(('http://', 'https://')):
            data[field_name] = file_value
            return False
        elif os.path.exists(file_value):
            files[field_name] = open(file_value, 'rb')
            return True
        else:
            data[field_name] = file_value
            return False
    
    def send_message(self, chat_id, text, parse_mode=None, 
                     disable_web_page_preview=False, disable_notification=False,
                     protect_content=False, reply_to_message_id=None, 
                     allow_sending_without_reply=False, reply_markup=None):
        
        if not self.is_available():
            raise ValueError("Bot de Telegram no configurado")
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
            "protect_content": protect_content
        }
        
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        return self._send_request("sendMessage", data)

telegram_sender = TelegramSender()

@explorer.route("/send_telegram/<file_id>")
@login_required
@level_required(1)
def send_to_telegram(file_id):
    try:
        if not file_id:
            return "<h3>❌ ID de archivo no proporcionado.</h3>", 400
        
        if not telegram_sender.is_available():
            return "<h3>❌ Bot de Telegram no configurado.</h3>", 500
        
        user_id = session.get("user_id")
        if not user_id:
            return "<h3>❌ Usuario no autenticado.</h3>", 401
        
        try:
            chat_id = int(user_id)
        except ValueError:
            return "<h3>❌ ID de usuario no válido.</h3>", 400
        
        message_text = f"/sendfile {file_id}"
        
        response = telegram_sender.send_message(
            chat_id=chat_id,
            text=message_text
        )
        
        if response.status_code == 200:
            return f"<h3>✅ Archivo {file_id} enviado a Telegram</h3><p><a href='/'>Volver al explorador</a></p>"
        else:
            error_data = response.json()
            error_msg = error_data.get('description', 'Error desconocido')
            return f"<h3>❌ Error al enviar a Telegram: {error_msg}</h3>", 500
        
    except Exception as e:
        return f"<h3>Error: {str(e)}</h3>", 500

@explorer.route("/api/json/snh", methods=["GET"])
@login_required
def search_nhentai_json():
    search_term = request.args.get("q", "").strip()
    page = request.args.get("p", "1")
    
    try:
        page = int(page)
    except:
        page = 1
    
    if not search_term:
        return jsonify({
            "success": False,
            "error": "Se requiere parámetro 'q' (término de búsqueda)"
        }), 400
    
    try:
        data = scrape_nhentai_with_selenium(search_term, page)
        results = data.get("results", [])
        total_pages = data.get("total_pages", 1)
        total_results = data.get("total_results", 0)
        
        json_results = []
        for result in results:
            json_results.append({
                "code": result.get("code", ""),
                "name": result.get("name", ""),
                "image_links": result.get("image_links", []),
                "total_pages": result.get("total_pages", 0)
            })
        
        return jsonify({
            "success": True,
            "search_term": search_term,
            "page": page,
            "total_pages": total_pages,
            "total_results": total_results,
            "results": json_results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@explorer.route("/api/json/s3h", methods=["GET"])
@login_required
def search_3hentai_json():
    search_term = request.args.get("q", "").strip()
    page = request.args.get("p", "1")
    
    try:
        page = int(page)
    except:
        page = 1
    
    if not search_term:
        return jsonify({
            "success": False,
            "error": "Se requiere parámetro 'q' (término de búsqueda)"
        }), 400
    
    try:
        data = scrape_3hentai_search(search_term, page)
        
        json_results = []
        if "resultados" in data and isinstance(data["resultados"], dict):
            for key, result in data["resultados"].items():
                json_results.append({
                    "code": result.get("codigo", ""),
                    "name": result.get("titulo", ""),
                    "image_links": [result.get("imagen", "")]
                })
        
        total_pages = data.get("total_paginas", 1)
        total_results = data.get("total_resultados", 0)
        
        return jsonify({
            "success": True,
            "search_term": search_term,
            "page": page,
            "total_pages": total_pages,
            "total_results": total_results,
            "results": json_results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@explorer.route("/api/json/vnh/<int:code>", methods=["GET"])
@login_required
def view_nhentai_json(code):
    try:
        from command.get_files.nh_selenium import scrape_nhentai
        result = scrape_nhentai(code)
        
        if not result.get("title") or not result.get("links"):
            return jsonify({
                "success": False,
                "error": "No se pudo obtener la información de la galería"
            }), 404
        
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', '', result["title"])[:100]
        
        return jsonify({
            "success": True,
            "code": code,
            "title": result["title"],
            "clean_title": clean_title,
            "tags": result.get("tags", {}),
            "image_links": result.get("links", []),
            "cover_image": result.get("links", [""])[0] if result.get("links") else ""
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error al cargar la galería: {str(e)}"
        }), 500

@explorer.route("/api/json/v3h/<code>", methods=["GET"])
@login_required
def view_3hentai_json(code):
    try:
        from command.get_files.h3_links import obtener_titulo_y_imagenes
        
        result = obtener_titulo_y_imagenes(code, cover=False)
        
        if not result.get("texto") or not result.get("imagenes"):
            return jsonify({
                "success": False,
                "error": "No se pudo obtener la información de la galería"
            }), 404
        
        import re
        clean_title = re.sub(r'[<>:"/\\|?*]', '', result["texto"])[:100]
        
        return jsonify({
            "success": True,
            "code": code,
            "title": result["texto"],
            "clean_title": clean_title,
            "tags": result.get("tags", {}),
            "image_links": result.get("imagenes", []),
            "cover_image": result.get("imagenes", [""])[0] if result.get("imagenes") else "",
            "total_pages": result.get("total_paginas", 0)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error al cargar la galería: {str(e)}"
        }), 500

def run_flask():
    explorer.run(host="0.0.0.0", port=10000)
