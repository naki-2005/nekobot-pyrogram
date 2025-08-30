import os
import json
import asyncio
import subprocess
from flask import Flask, request, send_from_directory, render_template_string, redirect, session
from threading import Thread
from command.torrets_tools import download_from_magnet
from command.htools import crear_cbz_desde_fuente
from my_flask_templates import LOGIN_TEMPLATE, MAIN_TEMPLATE, UTILS_TEMPLATE

explorer = Flask("file_explorer")
explorer.secret_key = os.getenv("FLASK_SECRET", "supersecretkey")
BASE_DIR = "vault_files"
WEBACCESS_FILE = "web_access.json"

def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

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

@explorer.route("/")
@explorer.route("/browse")
@login_required
def browse():
    requested_path = request.args.get("path", BASE_DIR)
    abs_base = os.path.abspath(BASE_DIR)
    abs_requested = os.path.abspath(requested_path)

    if not abs_requested.startswith(abs_base):
        return "<h3>❌ Acceso denegado: ruta fuera de 'vault_files'.</h3>", 403

    try:
        items = []
        for name in sorted(os.listdir(abs_requested)):
            full_path = os.path.join(abs_requested, name)
            is_dir = os.path.isdir(full_path)
            size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2) if not is_dir else "-"
            items.append({
                "name": name,
                "full_path": full_path,
                "is_dir": is_dir,
                "size_mb": size_mb
            })
        return render_template_string(MAIN_TEMPLATE, items=items)
    except Exception as e:
        return f"<h3>Error al acceder a los archivos: {e}</h3>", 500

@explorer.route("/utils")
@login_required
def utils_page():
    return render_template_string(UTILS_TEMPLATE)

@explorer.route("/download")
def download():
    path = request.args.get("path")
    if os.path.isfile(path):
        return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True)
    return "<h3>Archivo no válido para descarga.</h3>"

@explorer.route("/crear_cbz", methods=["POST"])
def crear_cbz():
    codigo = request.form.get("codigo", "").strip()
    tipo = request.form.get("tipo", "").strip()

    if not codigo or tipo not in ["nh", "h3", "hito"]:
        return "<h3>❌ Código o tipo inválido.</h3>", 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        cbz_path = loop.run_until_complete(crear_cbz_desde_fuente(codigo, tipo))
        return f"<h3>✅ CBZ creado: <a href='/download?path={cbz_path}'>{os.path.basename(cbz_path)}</a></h3>"
    except Exception as e:
        return f"<h3>❌ Error al crear CBZ: {e}</h3>", 500

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
        Thread(target=download_from_magnet, args=(link, BASE_DIR)).start()
        return redirect("/utils")
    except Exception as e:
        return f"<h3>Error al iniciar descarga: {e}</h3>", 500

@explorer.route("/delete", methods=["POST"])
@login_required
def delete_file():
    path = request.form.get("path")
    if not path or not os.path.isfile(path):
        return "<h3>❌ Archivo no válido para eliminar.</h3>", 400
    try:
        os.remove(path)
        return redirect("/")
    except Exception as e:
        return f"<h3>Error al eliminar archivo: {e}</h3>", 500

@explorer.route("/rename", methods=["POST"])
@login_required
def rename_item():
    old_path = request.form.get("old_path")
    new_name = request.form.get("new_name")
    if not old_path or not new_name:
        return "<h3>❌ Datos inválidos para renombrar.</h3>", 400
    try:
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        os.rename(old_path, new_path)
        return redirect("/")
    except Exception as e:
        return f"<h3>Error al renombrar: {e}</h3>", 500

@explorer.route("/compress", methods=["POST"])
@login_required
def compress_items():
    archive_name = request.form.get("archive_name", "").strip()
    selected = request.form.getlist("selected")
    if not archive_name or not selected:
        return "<h3>❌ Debes proporcionar un nombre y seleccionar archivos.</h3>", 400

    archive_path = os.path.join(BASE_DIR, f"{archive_name}.7z")
    try:
        cmd_args = [
            os.path.join("7z", "7zz"),
            'a',
            '-mx=0',
            '-v2000m',
            archive_path
        ] + selected
        subprocess.run(cmd_args, check=True)

        for path in selected:
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)

        return redirect("/")
    except Exception as e:
        return f"<h3>❌ Error al comprimir: {e}</h3>", 500

def run_flask():
    explorer.run(host="0.0.0.0", port=10000)
