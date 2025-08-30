import os
import sqlite3
import base64
import json
import urllib.request
from datetime import datetime
import urllib.error

MAILDATA_FILE = "maildata.txt"
WEBACCESS_FILE = "data/web_access.json"

def guardar_datos_web(user_id: int, usuario: str, contraseña: str) -> None:
    datos = {}

    if os.path.exists(WEBACCESS_FILE):
        try:
            with open(WEBACCESS_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except:
            datos = {}

    datos[str(user_id)] = {
        "user": usuario,
        "pass": contraseña
    }

    try:
        with open(WEBACCESS_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
    except:
        return

    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    if not GIT_REPO or not GIT_API:
        return

    file_path = "data/web_access.json"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return

    with open(WEBACCESS_FILE, "rb") as f:
        encoded_content = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "message": "Actualización de datos web",
        "content": encoded_content,
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

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            return result.get("content", {}).get("download_url", "Subido sin URL")
    except:
        return
        
def guardar_datos_correo(correo: str, contraseña: str, servidor: str) -> None:
    if not os.path.exists(MAILDATA_FILE):
        with open(MAILDATA_FILE, "w", encoding="utf-8") as f:
            f.write("")

    try:
        with open(MAILDATA_FILE, "w", encoding="utf-8") as f:
            f.write(f"{correo}\n{contraseña}\n{servidor}\n")
    except:
        return

    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    if not GIT_REPO or not GIT_API:
        return

    file_path = "data/maildata.txt"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return

    with open(MAILDATA_FILE, "rb") as f:
        encoded_content = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "message": "Actualización de datos de correo",
        "content": encoded_content,
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

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            return result.get("content", {}).get("download_url", "Subido sin URL")
    except:
        return

def descargar_mail_config():
    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    if not GIT_REPO or not GIT_API:
        print("[!] Variables de entorno GIT_REPO o GIT_API no definidas")
        return

    file_path = "data/maildata.txt"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            content_b64 = data.get("content")
            if not content_b64:
                print("[!] No se encontró contenido en el archivo remoto")
                return

            decoded = base64.b64decode(content_b64)
            with open("maildata.txt", "wb") as f:
                f.write(decoded)

            print(f"[✓] Archivo descargado y guardado como maildata.txt")

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("[!] El archivo remoto no existe")
        else:
            raise RuntimeError(f"Error al descargar desde GitHub: {e.code} {e.reason}")

def cargar_datos_correo():
    archivo = "maildata.txt"
    if not os.path.exists(archivo):
        print("[!] El archivo maildata.txt no existe")
        return None

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            lineas = [line.strip() for line in f.readlines()]
    except Exception as e:
        print(f"[!] Error al leer maildata.txt: {e}")
        return None

    if len(lineas) < 3 or not all(lineas[:3]):
        print("[!] El archivo maildata.txt está incompleto o tiene datos faltantes")
        return None

    return lineas[0], lineas[1], lineas[2]
    
                                               
def subir_bot_config(bot_id: str):
    db_path = "bot_cmd.db"
    if not os.path.exists(db_path):
        print(f"[!] No existe el archivo: {db_path}")
        return

    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    if not GIT_REPO or not GIT_API:
        print("[!] Variables de entorno GIT_REPO o GIT_API no definidas")
        return

    file_name = f"{bot_id}.db"
    file_path = f"data/{file_name}"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    # Detectar si el archivo ya existe para obtener el SHA
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise RuntimeError(f"Error al consultar GitHub: {e.code} {e.reason}")
        # Si es 404, el archivo no existe aún → no se necesita SHA

    # Codificar el contenido del archivo local
    with open(db_path, "rb") as f:
        encoded_content = base64.b64encode(f.read()).decode("utf-8")

    # Preparar el payload para subir o sobrescribir
    payload = {
        "message": f"Subida de configuración bot {bot_id}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha  # Necesario para sobrescribir

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="PUT"
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        print(f"[✓] Subido como {file_name}")
        return result.get("content", {}).get("download_url", "Subido sin URL")

def descargar_bot_config(bot_id: str):
    GIT_REPO = os.getenv("GIT_REPO")
    GIT_API = os.getenv("GIT_API")
    if not GIT_REPO or not GIT_API:
        print("[!] Variables de entorno GIT_REPO o GIT_API no definidas")
        return

    file_name = f"{bot_id}.db"
    file_path = f"data/{file_name}"
    url = f"https://api.github.com/repos/{GIT_REPO}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            content_b64 = data.get("content")
            if not content_b64:
                print("[!] No se encontró contenido en el archivo remoto")
                return

            # Decodificar y guardar como bot_cmd.db
            decoded = base64.b64decode(content_b64)
            with open("bot_cmd.db", "wb") as f:
                f.write(decoded)

            print(f"[✓] Archivo descargado y guardado como bot_cmd.db")

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("[!] El archivo remoto no existe")
        else:
            raise RuntimeError(f"Error al descargar desde GitHub: {e.code} {e.reason}")
            
RESERVED_SQL = {"limit", "group", "order", "select"}

def escape_sql_key(key):
    return f'"{key}"' if key.lower() in RESERVED_SQL else key

def save_user_data_to_db(user_id, key, value):
    import urllib.request, json, base64, os, sqlite3
    from datetime import datetime

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

    with sqlite3.connect(db_path, timeout=5, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                user_id TEXT PRIMARY KEY,
                timestamp TEXT
            )
        """)
        cursor.execute("PRAGMA table_info(user_data)")
        columns = [col[1] for col in cursor.fetchall()]
        if key not in columns:
            cursor.execute(f'ALTER TABLE user_data ADD COLUMN "{key}" TEXT')

        cursor.execute(f'''
            INSERT INTO user_data (user_id, "{key}", timestamp)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET "{key}" = excluded."{key}", timestamp = excluded.timestamp
        ''', (str(user_id), str(value), datetime.utcnow().isoformat()))
        conn.commit()

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
    
def load_user_config(user_id, key):
    import os, json, base64, urllib.request, sqlite3

    RESERVED_SQL = {"limit", "group", "order", "select"}
    def escape_sql_key(k):
        return f'"{k}"' if k.lower() in RESERVED_SQL else k

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

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            content = base64.b64decode(existing["content"])
            with open(db_path, "wb") as f:
                f.write(content)
    except Exception as e:
        raise RuntimeError(f"No se pudo descargar la base de datos: {e}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(user_data)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if key not in existing_cols:
        cursor.execute(f'ALTER TABLE user_data ADD COLUMN {escape_sql_key(key)} TEXT')
    cursor.execute(f'SELECT {escape_sql_key(key)} FROM user_data WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    val = row[0] if row else None
    if row is None:
        return "1"
    elif key == "limit":
        return int(val) if val and val.isdigit() else 10
    elif key == "delay":
        return val if val else "manual"
    elif val is None:
        return "1"
    else:
        return val
