import os
from flask import Flask, request, send_from_directory, render_template_string

explorer = Flask("file_explorer")
BASE_DIR = "/opt/render/project/src/vault_files"

TEMPLATE = """
<!doctype html>
<html>
<head><title>Explorador de Archivos</title></head>
<body>
    <h2>Archivos guardados</h2>
    <ul>
    {% for item in items %}
        <li>
            {% if item['is_dir'] %}
                <a href="/browse?path={{ item['full_path'] }}">{{ item['name'] }}/</a>
            {% else %}
                <a href="/download?path={{ item['full_path'] }}">{{ item['name'] }}</a> — {{ item['size_mb'] }} MB
            {% endif %}
        </li>
    {% endfor %}
    </ul>
</body>
</html>
"""

@explorer.route("/")
@explorer.route("/browse")
def browse():
    path = request.args.get("path", BASE_DIR)
    try:
        items = []
        for name in sorted(os.listdir(path)):
            full_path = os.path.join(path, name)
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
        return f"<h3>Error al acceder a los archivos: {e}</h3>"

@explorer.route("/download")
def download():
    path = request.args.get("path")
    if os.path.isfile(path):
        return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True)
    return "<h3>Archivo no válido para descarga.</h3>"

def run_flask():
    explorer.run(host="0.0.0.0", port=10000)
