from torf import Magnet
import asyncio
import os

async def descargar_torrent(magnet_link, download_folder="./downloads"):
    """
    Descarga un archivo desde un enlace magnet y guarda los archivos en un directorio especificado.

    Args:
        magnet_link (str): El enlace magnet del torrent.
        download_folder (str): El directorio donde se guardarán los archivos descargados.

    Returns:
        list: Lista de paths de los archivos descargados.
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Crear un objeto Magnet desde el enlace magnet
    magnet = Magnet(magnet_link)

    # Descargar los archivos
    print(f"Descargando torrent desde: {magnet_link}")
    magnet.download(download_folder)

    print("Descarga completada.")

    # Obtener los paths de los archivos descargados
    downloaded_files = [os.path.join(download_folder, file) for file in os.listdir(download_folder)]
    return downloaded_files

# Ejemplo de uso
async def main():
    magnet_link = "MAGNET_LINK_AQUI"
    archivos = await descargar_torrent(magnet_link)
    print(f"Archivos descargados: {archivos}")

# Para ejecutar el script
# asyncio.run(main())
