import os
import sqlite3
import base64
import json
import urllib.request

GIT_REPO = os.getenv("GIT_REPO")
GIT_API = os.getenv("GIT_API")
FILE_PATH = "access_data.db"
url = f"https://api.github.com/repos/{GIT_REPO}/contents/data/{FILE_PATH}"

def modify_db(query, params=()):
    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    # 📥 Descargar base
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            sha = existing.get("sha")
            content = base64.b64decode(existing["content"])
            with open(FILE_PATH, "wb") as f:
                f.write(content)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise RuntimeError(f"Error al descargar la base: {e.code} {e.reason}")
        sha = None
    except Exception as e:
        raise RuntimeError(f"Error inesperado al descargar: {e}")

    # 🧱 Ejecutar operación
    conn = sqlite3.connect(FILE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ban_users (user_id INTEGER PRIMARY KEY);
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_users (user_id INTEGER PRIMARY KEY);
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_chats (chat_id INTEGER PRIMARY KEY);
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY);
    """)
    cursor.execute(query, params)
    conn.commit()
    conn.close()

    # 🚀 Subir base modificada
    with open(FILE_PATH, "rb") as f:
        new_content = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "message": "Actualización de access_data.db",
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
          
