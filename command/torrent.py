from torf import Torrent
import asyncio
import os
import aiohttp

async def descargar_torrent(magnet_link, download_folder="./downloads"):
    """
    Descarga un torrent desde un enlace magnet y guarda los archivos en un directorio especificado.

    Args:
        magnet_link (str): El enlace magnet del torrent.
        download_folder (str): El directorio donde se guardarán los archivos descargados.

    Returns:
        list: Lista de paths de los archivos descargados.
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Crear un cliente para manejar el enlace magnet
    async with aiohttp.ClientSession() as session:
        torrent = Torrent.from_magnet(magnet_link)
        torrent.download_to(download_folder, session=session)

        print(f"Descargando torrent desde: {magnet_link}")

        # Mantener el estado de descarga
        while not torrent.complete:
            await asyncio.sleep(1)
            print(f"Progreso: {torrent.progress:.2f}%")

        print("Descarga completada.")

        # Obtener los paths de los archivos descargados
        downloaded_files = [os.path.join(download_folder, file.name) for file in torrent.files]
        return downloaded_files

# Ejemplo de uso
async def main():
    magnet_link = "MAGNET_LINK_AQUI"
    archivos = await descargar_torrent(magnet_link)
    print(f"Archivos descargados: {archivos}")

# Para ejecutar el script
# asyncio.run(main())
