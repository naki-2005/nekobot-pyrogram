import os
from command.db.db import save_user_data_to_db, descargar_mail_config, descargar_bot_config
from arg_parser import get_args
from command.db.db import descargar_web_config

def start_data():
    admin_users = list(map(int, os.getenv('ADMINS', '').split(','))) if os.getenv('ADMINS') else []
    users = list(map(int, os.getenv('USERS', '').split(','))) if os.getenv('USERS') else []
    vip_users = list(map(int, os.getenv('VIP_USERS', '').split(','))) if os.getenv('VIP_USERS') else []
    ban_users = list(map(int, os.getenv('BAN_USERS', '').split(','))) if os.getenv('BAN_USERS') else []

    # 🧱 Guardar niveles
    for user_id in ban_users:
        save_user_data_to_db(user_id, "lvl", "0")

    for user_id in users:
        save_user_data_to_db(user_id, "lvl", "2")

    for user_id in vip_users:
        save_user_data_to_db(user_id, "lvl", "3")

    for i, user_id in enumerate(admin_users):
        lvl = "6" if i == 0 else "5"
        save_user_data_to_db(user_id, "lvl", lvl)

def start_data_2():
    args = get_args()
    os.makedirs("vault_files", exist_ok=True)

    if args.session_string:
        bot_id = args.id
        print(f"[↘] Descargando configuración para bot_id (por -id): {bot_id}")
    elif args.bot_token:
        if ":" not in args.bot_token:
            print("[!] Token inválido, formato incorrecto")
            return
        bot_id = args.bot_token.split(":")[0]
        print(f"[↘] Descargando configuración para bot_id (desde token): {bot_id}")
    else:
        print("[!] No se proporcionó ni -t ni -ss, abortando")
        return

    descargar_bot_config(bot_id)
    descargar_mail_config()
    descargar_web_config()  

    chrome_dir = "selenium/chrome-linux64"
    base_path = os.path.join(chrome_dir, "chrome")
    output_file = base_path
    total_parts = 11

    try:
        with open(output_file, 'wb') as output:
            for part_num in range(1, total_parts + 1):
                part_file = f"{base_path}.{part_num:03d}"
                if not os.path.exists(part_file):
                    print(f"[!] Parte faltante: {part_file}")
                    return
                with open(part_file, 'rb') as pf:
                    chunk = pf.read()
                    output.write(chunk)
                print(f"[✓] Añadida parte {part_num:03d} ({len(chunk)} bytes)")
    except Exception as e:
        print(f"[!] Error al reconstruir chrome: {e}")
        return

    for i in range(1, total_parts + 1):
        part_file = f"{base_path}.{i:03d}"
        try:
            os.remove(part_file)
            print(f"[🗑️] Eliminada parte: {part_file}")
        except Exception as e:
            print(f"[!] Error al eliminar {part_file}: {e}")

    print(f"[✅] Chrome reconstruido como: {output_file}")

    for path in [
        "selenium/chrome-linux64/chrome",
        "selenium/chromedriver-linux64/chromedriver"
        "7z/7zz"
    ]:
        try:
            os.chmod(path, 0o755)
            print(f"[🔓] Permisos ajustados: {path}")
        except Exception as e:
            print(f"[!] Error al ajustar permisos en {path}: {e}")
