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
    parser.add_argument("-w", "--web", help="URL web opcional para configuración adicional")
    parser.add_argument("-g", "--group_id", nargs="*", type=int, help="IDs de grupos para moderación")
    parser.add_argument("-bw", "--black_words", nargs="*", help="Palabras prohibidas")
    parser.add_argument("-fu", "--free_users", type=str, help="Usuarios exentos del filtro (separados por comas)")
    parser.add_argument("-sb", "--safe_block", type=str, help="Dominios seguros que no se bloquean aunque contengan palabras prohibidas (separados por comas)")
    

    args = parser.parse_args()

    if args.bot_token and args.session_string:
        sys.exit("No puedes usar bot_token y session_string al mismo tiempo.")
    elif not args.bot_token and not args.session_string:
        sys.exit("Debes proporcionar bot_token o session_string.")

    if args.session_string and not args.id:
        sys.exit("Si usas session_string, debes proporcionar un ID personalizado.")

    return args
