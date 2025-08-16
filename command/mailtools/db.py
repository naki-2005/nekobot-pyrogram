import os
import sqlite3
import base64
import json
import urllib.request
from datetime import datetime

def save_user_data_to_db(user_id, key, value):
    db_path = "user_data.db"
    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    FILE_PATH = "data/user_data.db"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{FILE_PATH}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    # 📥 1. Descargar la base si existe
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            sha = existing.get("sha")
            content = base64.b64decode(existing["content"])
            with open(db_path, "wb") as f:
                f.write(content)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise RuntimeError(f"Error al descargar la base: {e.code} {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado al descargar: {e}")

    # 🧱 2. Crear base si no existe y asegurar columnas
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER PRIMARY KEY,
            timestamp TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(user_data)")
    columns = [col[1] for col in cursor.fetchall()]
    if key not in columns:
        cursor.execute(f"ALTER TABLE user_data ADD COLUMN {key} TEXT")

    # 🔁 3. Insertar o actualizar datos
    cursor.execute(f"""
        INSERT INTO user_data (user_id, {key}, timestamp)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET {key} = excluded.{key}, timestamp = excluded.timestamp
    """, (user_id, value, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    # 🚀 4. Subir la base modificada
    with open(db_path, "rb") as f:
        new_content = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "message": f"Actualización de datos para user_id {user_id}",
        "content": new_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="PUT"
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        return result.get("content", {}).get("download_url", "Subido sin URL")



def load_user_config(user_id):
    db_path = "user_data.db"
    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    FILE_PATH = "data/user_data.db"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{FILE_PATH}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    # 📥 Descargar la base
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            content = base64.b64decode(existing["content"])
            with open(db_path, "wb") as f:
                f.write(content)
    except Exception as e:
        raise RuntimeError(f"No se pudo descargar la base de datos: {e}")

    # 🔍 Leer datos del usuario
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT email, limit, delay FROM user_data WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        raise ValueError("Correo electrónico no registrado. Usa /setmail primero.")

    email = row[0]
    mail_mb = int(row[1]) if row[1] and row[1].isdigit() else 10
    mail_delay = row[2] if row[2] else "manual"

    return email, mail_mb, mail_delay
    
