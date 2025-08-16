import os
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib.error
import urllib.request

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('TOKEN')
admin_users = list(map(int, os.getenv('ADMINS').split(','))) if os.getenv('ADMINS') else []
users = list(map(int, os.getenv('USERS').split(','))) if os.getenv('USERS') else []
vip_users = list(map(int, os.getenv('VIP_USERS', '').split(','))) if os.getenv('VIP_USERS') else []
temp_users, temp_chats, ban_users = [], [], []
video_limit = os.getenv('VIDEO_LIMIT')
video_limit = int(video_limit) if video_limit else None

GIT_REPO = os.getenv("GIT_REPO")
GIT_API = os.getenv("GIT_API")
FILE_PATH = "access_data.db"
url = f"https://api.github.com/repos/{GIT_REPO}/data/{FILE_PATH}"

def read_db(query, params=()):
    headers = {
        "Authorization": f"Bearer {GIT_API}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }

    # 📥 Intentar descargar base remota
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json.loads(response.read())
            content = base64.b64decode(existing["content"])
            with open(FILE_PATH, "wb") as f:
                f.write(content)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("[WARN] Base remota no encontrada. Usando base local vacía.")
            # Crear base vacía si no existe
            if not os.path.exists(FILE_PATH):
                conn = sqlite3.connect(FILE_PATH)
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
                cursor.execute("CREATE TABLE IF NOT EXISTS temp_users (user_id INTEGER PRIMARY KEY)")
                cursor.execute("CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY)")
                conn.commit()
                conn.close()
        else:
            raise RuntimeError(f"Error al leer la base: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado: {e}")

    # 📤 Leer datos
    conn = sqlite3.connect(FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[ERROR] Consulta fallida: {e}")
        rows = []
    conn.close()
    return [row[0] for row in rows]

def start_data():
    global admin_users
    global users

    admin_users = read_db("SELECT user_id FROM admins") or []
    users = read_db("SELECT user_id FROM temp_users") or []

    if not admin_users and os.getenv('ADMINS'):
        admin_users = list(map(int, os.getenv('ADMINS').split(',')))
    if not users and os.getenv('USERS'):
        users = list(map(int, os.getenv('USERS').split(',')))

    for uid in admin_users:
        modify_db("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
        modify_db("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (uid,))

    for uid in users:
        modify_db("INSERT OR IGNORE INTO temp_users (user_id) VALUES (?)", (uid,))
        modify_db("INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)", (uid,))
                                     
MAIN_ADMIN = os.getenv("MAIN_ADMIN")
CODEWORD = os.getenv('CODEWORD', '')
BOT_IS_PUBLIC = os.getenv('BOT_IS_PUBLIC', 'false').strip().lower() == "true"
PROTECT_CONTENT = os.getenv('PROTECT_CONTENT', '').strip().lower() == "true"

allowed_users = admin_users + users + temp_users + temp_chats
allowed_ids = set(admin_users).union(set(vip_users))

# Inicializamos video_settings con un ID base como 'default'
video_settings = {
    'default': {
        'resolution': '640x400',
        'crf': '28',
        'audio_bitrate': '80k',
        'fps': '18',
        'preset': 'veryfast',
        'codec': 'libx265'
    }
}


# Botones definidos globalmente
correo_manual = InlineKeyboardMarkup([
    [InlineKeyboardButton("Enviar siguiente parte", callback_data="send_next_part")],
    [
        InlineKeyboardButton("Enviar 5 partes", callback_data="send_5_parts"),
        InlineKeyboardButton("Enviar 10 partes", callback_data="send_10_parts")
    ],
    [InlineKeyboardButton("Enviar automáticamente", callback_data="no_action")],
    [
        InlineKeyboardButton("10 seg", callback_data="auto_delay_10"),
        InlineKeyboardButton("30 seg", callback_data="auto_delay_30"),
        InlineKeyboardButton("60 seg", callback_data="auto_delay_60")
    ],
    [
        InlineKeyboardButton("90 seg", callback_data="auto_delay_90"),
        InlineKeyboardButton("180 seg", callback_data="auto_delay_180")
    ],
    [InlineKeyboardButton("Cancelar envío", callback_data="cancel_send")]
])
