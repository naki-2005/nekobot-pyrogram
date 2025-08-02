import os
import json
import requests
admin_users = list(map(int, os.getenv('ADMINS', '').split(','))) if os.getenv('ADMINS') else []
async def save_mail(client, message):
    user_id = str(message.from_user.id)
    if user_id not in admin_users:
        return

    try:
        payload = message.text.split(',', 3)
        if len(payload) != 4:
            await message.reply("Formato inválido. Usa: user_id,email,delay,limit_mb")
            return

        user_data = {
            "email": payload[1].strip(),
            "delay": int(payload[2].strip()),
            "limit_mb": int(payload[3].strip())
        }

        GIT_REPO = os.getenv("GIT_REPO")  # ej. nakigeplayer/data-base
        GIT_API = os.getenv("GIT_API")    # token de acceso
        FILE_PATH = "config.json"        # nombre del archivo dentro del repo

        # Construye la URL para obtener el contenido del archivo
        url = f"https://api.github.com/repos/{GIT_REPO}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"token {GIT_API}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Revisa si el archivo ya existe
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            content = response.json()
            sha = content['sha']
            existing_data = json.loads(
                requests.get(content['download_url'], headers=headers).text
            )
        else:
            existing_data = {}
            sha = None

        # Actualiza el JSON
        existing_data[user_id] = user_data
        updated_content = json.dumps(existing_data, indent=4)

        commit_data = {
            "message": f"Update config for user {user_id}",
            "content": updated_content.encode("utf-8").decode("utf-8"),
            "branch": "main"
        }
        if sha:
            commit_data["sha"] = sha

        put_response = requests.put(url, headers=headers, json=commit_data)

        if put_response.status_code in [200, 201]:
            await message.reply("✅ Configuración guardada exitosamente en GitHub.")
        else:
            await message.reply(f"❌ Error al guardar: {put_response.status_code}")
    except Exception as e:
        await message.reply(f"Error inesperado: {str(e)}")

def load_mail():
    try:
        GIT_REPO = os.getenv("GIT_REPO")
        GIT_API = os.getenv("GIT_API")
        FILE_PATH = "config.json"

        url = f"https://api.github.com/repos/{GIT_REPO}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"token {GIT_API}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            config = json.loads(
                requests.get(content['download_url'], headers=headers).text
            )
            for uid, data in config.items():
                uid = int(uid)
                user_emails[uid] = data['email']
                user_delays[uid] = data['delay']
                user_limits[uid] = data['limit_mb']
        else:
            print("No se encontró configuración previa.")
    except Exception as e:
        print(f"Error al cargar configuración: {str(e)}")
