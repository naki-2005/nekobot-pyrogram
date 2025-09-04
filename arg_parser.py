import argparse
import sys

def get_args():
    parser = argparse.ArgumentParser(description="Inicializa el bot con credenciales")

    parser.add_argument("-a", "--api_id", required=True, help="API ID de Telegram")
    parser.add_argument("-H", "--api_hash", required=True, help="API Hash de Telegram")
    parser.add_argument("-t", "--bot_token", help="Token del bot")
    parser.add_argument("-ss", "--session_string", help="Session string del usuario")
    parser.add_argument("-id", help="ID personalizado requerido si se usa -ss")
    parser.add_argument("-b", "--barer", required=True, help="Token de autenticación Bearer")
    parser.add_argument("-r", "--repo", required=True, help="Repositorio o URL del repositorio")
    parser.add_argument("-owner", help="Owner o propietario (opcional)")

    args = parser.parse_args()

    if args.bot_token and args.session_string:
        print("❌ No puedes usar -t y -ss al mismo tiempo. Usa solo uno.")
        sys.exit(1)
    elif not args.bot_token and not args.session_string:
        print("❌ Debes proporcionar -t o -ss. Uno de los dos es obligatorio.")
        sys.exit(1)

    if args.session_string and not args.id:
        print("❌ Si usas -ss también debes proporcionar -id.")
        sys.exit(1)

    return args
