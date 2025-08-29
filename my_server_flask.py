import os
from flask import Flask, request, send_from_directory, render_template_string, redirect
from threading import Thread
from command.torrets_tools import download_from_magnet

explorer = Flask("file_explorer")
BASE_DIR = "vault_files"

TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Explorador de Archivos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        .header {
            background-color: #007BFF;
            color: white;
            padding: 1em;
            text-align: center;
            font-size: 1.2em;
        }
        .header a {
            color: white;
            text-decoration: underline;
            font-weight: bold;
        }
        .content {
            padding: 1em;
        }
        form {
            margin-bottom: 1em;
            display: flex;
            flex-direction: column;
            gap: 0.5em;
        }
        input[type="file"], input[type="text"] {
            max-width: 100%;
            padding: 0.5em;
            font-size: 1em;
        }
        button {
            padding: 0.6em;
            font-size: 1em;
            background-color: #007BFF;
            color: white;
            border: none;
            border-radius: 4px;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            margin: 0.5em 0;
            word-break: break-word;
        }
        a {
            text-decoration: none;
            color: #007BFF;
        }
        a:hover {
            text-decoration: underline;
        }
        .delete-btn {
            background-color: #dc3545;
            color: white;
            border: none;
            padding: 0.4em 0.8em;
            margin-left: 10px;
            border-radius: 4px;
            cursor: pointer;
        }
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
def browse():
    requested_path = request.args.get("path", BASE_DIR)
    abs_base = os.path.abspath(BASE_DIR)
    abs_requested = os.path.abspath(requested_path)

    # Verifica que el path solicitado esté dentro de BASE_DIR
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
