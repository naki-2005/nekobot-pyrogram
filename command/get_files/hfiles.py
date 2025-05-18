import os
import re
import requests
import zipfile
from bs4 import BeautifulSoup
from fpdf import FPDF

def clean_string(s):
    return re.sub(r'[^a-zA-Z0-9\[\] ]', '', s)

def no_crear_pdf(folder_name, pdf_filename):
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=0)

        for file in sorted(os.listdir(folder_name)):
            file_path = os.path.join(folder_name, file)
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                pdf.add_page()
                pdf.image(file_path, x=0, y=0, w=210)

        pdf.output(pdf_filename)
        #print(f"PDF creado: {pdf_filename}")
        return pdf_filename
    except Exception as e:
        #print(f"Error al crear PDF: {e}")
        return None

def descargar_hentai(url, code, base_url, operation_type, protect_content, user_default_selection, folder_name):
    results = {}
    first_img_filename = None  # Para guardar la primera imagen
    last_page_number = None  # Para almacenar el número de la última página válida
    print(user_default_selection)

    try:
        # Asegurar que el directorio base existe
        os.makedirs(folder_name, exist_ok=True)

        # Descargar la portada y obtener el título para usarlo como nombre de archivo
        page_url = f"https://{base_url}/{code}/1/"
        response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraer el título
        title_tag = soup.find('title')
        page_title = clean_string(title_tag.text.strip()) if title_tag else f"Contenido_{code}"

        # Extraer la imagen
        img_tag = soup.find('img', {'src': re.compile(r'.*\.(png|jpg|jpeg|gif|bmp|webp)$')})
        img_filename = None
        if img_tag:
            img_url = img_tag['src']
            img_extension = os.path.splitext(img_url)[1]
            img_filename = os.path.join(folder_name, f"1{img_extension}")
            first_img_filename = img_filename

            with open(img_filename, 'wb') as img_file:
                img_data = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}).content
                img_file.write(img_data)

        last_page_number = 1

        # Acceder al directorio principal donde están todas las imágenes
        page_url = f"https://{base_url}/{code}/"
        response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            # Buscar todas las imágenes en el directorio
            img_tags = soup.find_all("img", {"src": True})

            if img_tags:
                # Extraer números de las imágenes y encontrar el mayor
                page_numbers = [
                    int(re.search(r"(\d+)t\.(png|webp|jpg)", img_tag["src"]).group(1))
                    for img_tag in img_tags if re.search(r"(\d+)t\.(png|webp|jpg)", img_tag["src"])
                ]

                if page_numbers:
                    last_page_number = max(page_numbers)

        results = {
            "last_page_number": last_page_number
        }


        if operation_type == "cover":
            page_title = f"{page_title} \n{last_page_number} Páginas\n\n https://{base_url}/{code}/"
            page_title = re.sub("Page 1  nhentai hentai doujinshi and manga|Page 1  3Hentai", "", page_title)
            
            results = {
                "caption": page_title,
                "img_file": first_img_filename,
                "last_page_number": last_page_number
            }
            
        if operation_type == "download":
            main_page_url = f"https://{base_url}/{code}/"
            response = requests.get(main_page_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(response.content, 'html.parser')
            
            img_links = [re.sub(r'(?<=/)\d+t\.', r'\1.', img['src']) for img in soup.find_all('img', {'src': re.compile(r'\d+t\..*\.(png|jpg|jpeg|gif|bmp|webp)$')})]
            print(img_links)
            
            for img_tag in img_tags:
                original_url = img_tag['src'].replace('t.', '', 1)
                img_name = original_url.split('/')[-1]
                img_filename = os.path.join(folder_name, img_name)
                
                with requests.get(original_url, headers={"User-Agent": "Mozilla/5.0"}) as r:
                    with open(img_filename, 'wb') as f:
                        f.write(r.content)
                
            page_title = f"{page_title}"
            page_title = re.sub("Page 1  nhentai hentai doujinshi and manga|Page 1  3Hentai", "", page_title)
            
            # Usar el título como nombre de archivo
            zip_filename = f"{page_title}.cbz"
            #pdf_filename = f"{page_title}.pdf"

            # Crear CBZ
            if user_default_selection in ["cbz", "both", None]:
                with zipfile.ZipFile(zip_filename, 'w') as zipf:
                    for root, _, files in os.walk(folder_name):
                        for file in files:
                            zipf.write(os.path.join(root, file), arcname=file)

            # Crear PDF
            #pdf_result = crear_pdf(folder_name, pdf_filename)
            file_name = page_title

            page_title = f"{page_title}\n {last_page_number} Páginas \n\n https://{base_url}/{code}/"
            
            results = {
                "caption": page_title,
                "img_file": first_img_filename, 
                "cbz_file": zip_filename,
                "last_page_number": last_page_number,
                "file_name": file_name
            }
            return results
    except Exception as e:
        results = {"error": str(e)}

    return results

def borrar_carpeta(folder_name, cbz_file):
    try:
        # Borrar archivos en la carpeta temporal
        if os.path.exists(folder_name):
            for file in os.listdir(folder_name):
                os.remove(os.path.join(folder_name, file))
            os.rmdir(folder_name)

        # Borrar archivo CBZ
        if cbz_file and os.path.exists(cbz_file):
            os.remove(cbz_file)
    except Exception as e:
        print(f"Error al borrar: {e}")
