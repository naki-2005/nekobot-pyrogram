import os
import shutil
import requests
import re
from bs4 import BeautifulSoup
from pyrogram import Client, filters

async def handle_scan(client, message):
    try:
        url = message.text.split(' ', 1)[1]
    except IndexError:
        await message.reply("Envié el link a escanear")
        return
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        results = []
        for link in links:
            href = link['href']
            if not href.endswith(('.pdf', '.jpg', '.png', '.doc', '.docx', '.xls', '.xlsx')):
                page_name = link.get_text(strip=True)
                if page_name:
                    results.append(f"{page_name}\n{href}\n")
        final_results = []
        for result in results:
            lines = result.split('\n')
            if len(lines) > 1:
                href = lines[1]
                if not href.startswith('http'):
                    base_url = '/'.join(url.split('/')[:3])
                    href = f"{base_url}{href}"
                final_results.append(f"{lines[0]}\n{href}\n")
        if final_results:
            with open('results.txt', 'w') as f:
                f.write("\n".join(final_results))
            await message.reply_document('results.txt')
            os.remove('results.txt')
        else:
            await message.reply("No se encontraron enlaces de páginas web.")
    except Exception as e:
        await message.reply(f"Error al escanear la página: {e}")
        
async def handle_multiscan(client, message):
    try:
        parts = message.text.split(' ')
        base_url = parts[1]
        numbers = []
        for part in parts[2:]:
            if '-' in part:
                start, end = part.split('-')
                numbers.extend(range(int(start), int(end) + 1))
            else:
                numbers.append(int(part))
    except IndexError:
        await message.reply("Envié el link base seguido de los números de páginas a escanear.")
        return
    except ValueError:
        await message.reply("Asegúrese de que los números de páginas sean válidos.")
        return
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    final_results = []
    for number in numbers:
        url = f"{base_url}{number}"
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            results = []
            for link in links:
                href = link['href']
                if not href.endswith(('.pdf', '.jpg', '.png', '.doc', '.docx', '.xls', '.xlsx')):
                    page_name = link.get_text(strip=True)
                    if page_name:
                        results.append(f"{page_name}\n{href}\n")
            for result in results:
                lines = result.split('\n')
                if len(lines) > 1:
                    href = lines[1]
                    if not href.startswith('http'):
                        base_url_origin = '/'.join(url.split('/')[:3])
                        href = f"{base_url_origin}{href}"
                    final_results.append(f"{lines[0]}\n{href}\n")
        except Exception as e:
            await message.reply(f"Error al escanear la página {url}: {e}")
    if final_results:
        with open('results.txt', 'w') as f:
            f.write("\n".join(final_results))
        await message.reply_document('results.txt')
        os.remove('results.txt')
    else:
        await message.reply("No se encontraron enlaces de páginas web.")


import re

def get_input():
    print("Introduce líneas de texto. Escribe 'End imput' para finalizar.")
    user_lines = []

    while True:
        line = input()  # Leer una línea de texto
        if line.strip().lower() == "end imput":  # Verificar si es el comando de cierre
            break
        user_lines.append(line)

    return user_lines

async def summarize_lines(lines):
    numbers = []
    for line in lines:
        matches = re.findall(r'/(?:g|d)/(\d+)', line)
        if matches:
            numbers.extend(matches)

    if numbers:
        codes = ",".join(numbers)
    else:
        codes = None

    return codes
        
