import libtorrent as lt
import asyncio
import os

async def descargar_torrent(magnet_link, download_folder="./downloads"):
    """
    Descarga un archivo desde un enlace magnet y devuelve el path del archivo descargado.

    Args:
        magnet_link (str): El enlace magnet del torrent.
        download_folder (str): El directorio donde se guardarán los archivos descargados.

    Returns:
        list: Lista de paths de los archivos descargados.
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Inicializar sesión de libtorrent
    sesion = lt.session()
    sesion.listen_on(6881, 6891)

    # Agregar el enlace magnet
    params = {
        "save_path": download_folder,
        "storage_mode": lt.storage_mode_t.storage_mode_sparse,
    }
    handler = lt.add_magnet_uri(sesion, magnet_link, params)

    print("Descargando...")
    while not handler.is_seed():
        await asyncio.sleep(1)
        print(f"Progreso: {handler.status().progress * 100:.2f}%")

    print("Descarga completada.")

    # Obtener el path de los archivos descargados
    archivos = handler.get_torrent_info().files()
    paths = [os.path.join(download_folder, archivo.path) for archivo in archivos]
    
    return paths
  
