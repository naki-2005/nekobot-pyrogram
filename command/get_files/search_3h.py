import requests
from bs4 import BeautifulSoup
import argparse
import math
import sys
import re

def scrape_3hentai_search(search_term, page=1):
    encoded_search = requests.utils.quote(search_term)
    url = f"https://es.3hentai.net/search?q={encoded_search}&page={page}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        resultados = {}

        total_resultados_texto = soup.find('div', class_='search-result-nb-result')
        if total_resultados_texto:
            total_resultados = int(total_resultados_texto.text.strip().replace(' resultados', '').replace(' ', '').replace('\xa0', ''))
        else:
            total_resultados = 0

        total_paginas = math.ceil(total_resultados / 25)

        doujin_cols = soup.find_all('div', class_='doujin-col')

        for i, col in enumerate(doujin_cols[:25], 1):
            doujin = col.find('div', class_='doujin')
            if doujin:
                cover = doujin.find('a', class_='cover')
                if cover:
                    title_div = cover.find('div', class_='title')
                    if title_div:
                        titulo = title_div.text.strip()
                    else:
                        titulo = "Título no disponible"

                    img = cover.find('img')
                    if img and 'data-src' in img.attrs:
                        imagen_url = img['data-src'].replace('thumb.jpg', '1.jpg')
                    elif img and 'src' in img.attrs:
                        imagen_url = img['src'].replace('thumb.jpg', '1.jpg')
                    else:
                        imagen_url = "Imagen no disponible"

                    href = cover.get('href', '')
                    codigo_match = re.search(r'/d/(\d+)', href)
                    codigo = codigo_match.group(1) if codigo_match else "Código no disponible"

                    resultados[f"resultado_{i}"] = {
                        "titulo": titulo,
                        "imagen": imagen_url,
                        "codigo": codigo
                    }

        return {
            "busqueda": search_term,
            "pagina_actual": page,
            "total_resultados": total_resultados,
            "total_paginas": total_paginas,
            "resultados": resultados
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error al acceder a la página: {e}"}
    except Exception as e:
        return {"error": f"Error inesperado: {e}"}

def main():
    parser = argparse.ArgumentParser(description='Scraper de 3Hentai')
    parser.add_argument('--search', '-S', required=True, help='Término de búsqueda')
    parser.add_argument('--page', '-P', type=int, default=1, help='Número de página (por defecto: 1)')

    args = parser.parse_args()

    resultado = scrape_3hentai_search(args.search, args.page)

    import json
    print(json.dumps(resultado, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
