import os
import json
import asyncio
from flask import Flask, request, send_from_directory, render_template_string, redirect, session
from threading import Thread
from command.torrets_tools import download_from_magnet
from command.htools import crear_cbz_desde_fuente

explorer = Flask("file_explorer")
explorer.secret_key = os.getenv("FLASK_SECRET", "supersecretkey")
BASE_DIR = "vault_files"
WEBACCESS_FILE = "data/web_access.json"

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

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <title>Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #f0f0f0; padding: 2em; }
            form { max-width: 300px; margin: auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            input { width: 100%; padding: 0.5em; margin-bottom: 1em; border: 1px solid #ccc; border-radius: 4px; }
            input[type="submit"] { background-color: #007BFF; color: white; border: none; cursor: pointer; }
            input[type="submit"]:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <form method="post">
            <h2 style="text-align:center;">🔐 Iniciar sesión</h2>
            <input name="username" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <input type="submit" value="Ingresar">
        </form>
    </body>
    </html>
    """)
    
TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Explorador de Archivos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; box-sizing: border-box; }
        .header { background-color: #007BFF; color: white; padding: 1em; text-align: center; font-size: 1.2em; }
        .header a { color: white; text-decoration: underline; font-weight: bold; }
        .content { padding: 1em; }
        form { margin-bottom: 1em; display: flex; flex-direction: column; gap: 0.5em; }
        input[type="file"], input[type="text"], select { max-width: 100%; padding: 0.5em; font-size: 1em; }
        button { padding: 0.6em; font-size: 1em; background-color: #007BFF; color: white; border: none; border-radius: 4px; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 0.5em 0; word-break: break-word; }
        a { text-decoration: none; color: #007BFF; }
        a:hover { text-decoration: underline; }
        .delete-btn { background-color: #dc3545; color: white; border: none; padding: 0.4em 0.8em; margin-left: 10px; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="header">
        Servidor Flask de Neko Bot creado por <a href="https://t.me/nakigeplayer" target="_blank">Naki</a>
    </div>
    <div class="content">
        <h2>📁 Archivos guardados</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button type="submit">Subir archivo</button>
        </form>

        <h2>🔗 Descargar desde Magnet Link</h2>
        <form action="/magnet" method="post">
            <input type="text" name="magnet" placeholder="Pega aquí el magnet link o URL .torrent" required>
            <button type="submit">Descargar</button>
        </form>

        <h2>🔞 Descargar Doujin</h2>
        <form action="/crear_cbz" method="post">
            <input type="text" name="codigo" placeholder="Código o URL del doujin" required>
            <select name="tipo" required>
                <option value="nh">NHentai</option>
                <option value="h3">3Hentai</option>
                <option value="hito">Hitomi.la</option>
            </select>
            <button type="submit">Crear CBZ</button>
        </form>

        <ul>
        {% for item in items %}
            <li>
                {% if item['is_dir'] %}
                    📂 <a href="/browse?path={{ item['full_path'] }}">{{ item['name'] }}/</a>
                {% else %}
                    📄 <a href="/download?path={{ item['full_path'] }}">{{ item['name'] }}</a> — {{ item['size_mb'] }} MB
                    <form action="/delete" method="post" style="display:inline;">
                        <input type="hidden" name="path" value="{{ item['full_path'] }}">
                        <button class="delete-btn" onclick="return confirm('¿Eliminar {{ item['name'] }}?')">Eliminar</button>
                    </form>
                {% endif %}
            </li>
        {% endfor %}
        </ul>
    </div>
</body>
</html>
"""

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
        return render_template_string(TEMPLATE, items=items)
    except Exception as e:
        return f"<h3>Error al acceder a los archivos: {e}</h3>", 500

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
        return redirect("/")
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

def run_flask():
    explorer.run(host="0.0.0.0", port=10000)
