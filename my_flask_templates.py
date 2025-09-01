LOGIN_TEMPLATE = """
<!doctype html>
<html><head><title>Login</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body { font-family: Arial; background-color: #f0f0f0; padding: 2em; }
    form { max-width: 300px; margin: auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    input { width: 100%; padding: 0.5em; margin-bottom: 1em; border: 1px solid #ccc; border-radius: 4px; }
    input[type="submit"] { background-color: #007BFF; color: white; border: none; cursor: pointer; }
    input[type="submit"]:hover { background-color: #0056b3; }
</style></head>
<body><form method="post">
    <h2 style="text-align:center;">🔐 Iniciar sesión</h2>
    <input name="username" placeholder="Usuario" required>
    <input type="password" name="password" placeholder="Contraseña" required>
    <input type="submit" value="Ingresar">
</form></body></html>
"""

MAIN_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Explorador de Archivos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; margin: 0; padding: 0; box-sizing: border-box; }
        .header { background-color: #007BFF; color: white; padding: 1em; text-align: center; position: relative; }
        .header-title { font-size: 1.2em; margin-bottom: 10px; }
        .header a { color: white; text-decoration: underline; font-weight: bold; }
        .header-buttons { display: flex; justify-content: center; gap: 10px; opacity: 0; height: 0; overflow: hidden; transition: all 0.3s ease; }
        .header-buttons.show { opacity: 1; height: auto; }
        .utils-btn { 
            background-color: #28a745; 
            padding: 0.5em 1em; 
            border-radius: 4px; 
            color: white;
            text-decoration: none;
            font-size: 0.9em;
        }
        .utils-btn:hover {
            background-color: #218838;
        }
        .floating-btn { 
            position: absolute; 
            top: 10px; 
            right: 10px; 
            width: 12px; 
            height: 12px; 
            background: white; 
            border-radius: 50%; 
            cursor: pointer; 
            opacity: 0.7;
            animation: bounce 3s infinite, fadeOut 10s forwards;
            z-index: 1000;
        }
        .content { padding: 1em; }
        form { margin-bottom: 1em; display: flex; flex-direction: column; gap: 0.5em; }
        input[type="file"], input[type="text"], select { padding: 0.5em; font-size: 1em; }
        button { padding: 0.6em; font-size: 1em; background-color: #007BFF; color: white; border: none; border-radius: 4px; cursor: pointer; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 0.5em 0; word-break: break-word; }
        a { text-decoration: none; color: #007BFF; }
        a:hover { text-decoration: underline; }
        .delete-btn, .rename-btn { background-color: #dc3545; color: white; border: none; padding: 0.4em 0.8em; margin-left: 10px; border-radius: 4px; cursor: pointer; }
        .rename-btn { background-color: #ffc107; color: black; }
        .compress-toggle { margin-top: 1em; }
        
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-15px);}
            60% {transform: translateY(-7px);}
        }
        
        @keyframes fadeOut {
            0% { opacity: 0.7; }
            90% { opacity: 0.7; }
            100% { opacity: 0.2; }
        }
    </style>
    <script>
        function toggleCompress() {
            const section = document.getElementById("compress-section");
            section.style.display = section.style.display === "none" ? "block" : "none";
        }
        
        function toggleRename(id) {
            const input = document.getElementById("rename-" + id);
            input.style.display = input.style.display === "none" ? "inline" : "none";
        }
        
        function showUtilsButton() {
            const buttons = document.getElementById('header-buttons');
            buttons.classList.add('show');
            
            // Ocultar después de 3 segundos
            setTimeout(function() {
                buttons.classList.remove('show');
            }, 3000);
        }
        
        // Mostrar el botón flotante después de que la página cargue
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                document.getElementById('floating-btn').style.animation = 'bounce 3s infinite, fadeOut 10s forwards';
            }, 500);
        });
    </script>
</head>
<body>
    <div class="header">
        <div id="floating-btn" class="floating-btn" onclick="showUtilsButton()"></div>
        <div class="header-title">
            Servidor Flask de Neko Bot creado por <a href="https://t.me/nakigeplayer" target="_blank">Naki</a>
        </div>
        <div id="header-buttons" class="header-buttons">
            <a href="/utils" class="utils-btn">⚙️ Utilidades</a>
        </div>
    </div>
    <div class="content">
        <h2>📁 Archivos guardados</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button type="submit">Subir archivo</button>
        </form>

        <button class="compress-toggle" onclick="toggleCompress()">Comprimir</button>
        <div id="compress-section" style="display:none;">
            <form action="/compress" method="post">
                <input type="text" name="archive_name" placeholder="Nombre del archivo .7z" required>
                <ul>
                {% for item in items %}
                    <li>
                        <input type="checkbox" name="selected" value="{{ item['full_path'] }}">
                        {% if item['is_dir'] %}
                            📂 {{ item['name'] }}/
                        {% else %}
                            📄 {{ item['name'] }} — {{ item['size_mb'] }} MB
                        {% endif %}
                    </li>
                {% endfor %}
                </ul>
                <button type="submit">Comprimir</button>
            </form>
        </div>

        <ul>
        {% for item in items %}
            <li>
                {% if item['is_dir'] %}
                    📂 <a href="/browse?path={{ item['full_path'] }}">{{ item['name'] }}/</a>
                {% else %}
                    📄 <a href="/download?path={{ item['full_path'] }}">{{ item['name'] }}</a> — {{ item['size_mb'] }} MB
                {% endif %}
                <form action="/delete" method="post" style="display:inline;">
                    <input type="hidden" name="path" value="{{ item['full_path'] }}">
                    <button class="delete-btn" onclick="return confirm('¿Eliminar {{ item['name'] }}?')">Eliminar</button>
                </form>
                <button class="rename-btn" onclick="toggleRename('{{ loop.index }}')">✏️</button>
                <form action="/rename" method="post" style="display:inline;">
                    <input type="hidden" name="old_path" value="{{ item['full_path'] }}">
                    <input type="text" name="new_name" id="rename-{{ loop.index }}" style="display:none;" placeholder="Nuevo nombre">
                    <button type="submit" style="display:none;" id="rename-{{ loop.index }}-btn">Renombrar</button>
                </form>
            </li>
        {% endfor %}
        </ul>
    </div>
</body>
</html>
"""

UTILS_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Utilidades</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; margin: 0; padding: 0; box-sizing: border-box; }
        .header { background-color: #007BFF; color: white; padding: 1em; text-align: center; position: relative; }
        .header-title { font-size: 1.2em; margin-bottom: 10px; }
        .header a { color: white; text-decoration: underline; font-weight: bold; }
        .header-buttons { display: flex; justify-content: center; gap: 10px; opacity: 0; height: 0; overflow: hidden; transition: all 0.3s ease; }
        .header-buttons.show { opacity: 1; height: auto; }
        .back-btn { 
            background-color: #6c757d; 
            padding: 0.5em 1em; 
            border-radius: 4px; 
            color: white;
            text-decoration: none;
            font-size: 0.9em;
        }
        .back-btn:hover {
            background-color: #5a6268;
        }
        .floating-btn { 
            position: absolute; 
            top: 10px; 
            left: 10px; 
            width: 12px; 
            height: 12px; 
            background: white; 
            border-radius: 50%; 
            cursor: pointer; 
            opacity: 0.7;
            animation: bounce 3s infinite, fadeOut 10s forwards;
            z-index: 1000;
        }
        .content { padding: 1em; }
        form { margin-bottom: 2em; display: flex; flex-direction: column; gap: 0.5em; max-width: 500px; }
        input[type="text"], select { padding: 0.5em; font-size: 1em; }
        button { padding: 0.6em; font-size: 1em; background-color: #007BFF; color: white; border: none; border-radius: 4px; cursor: pointer; }
        h2 { border-bottom: 2px solid #007BFF; padding-bottom: 0.5em; }
        
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-15px);}
            60% {transform: translateY(-7px);}
        }
        
        @keyframes fadeOut {
            0% { opacity: 0.7; }
            90% { opacity: 0.7; }
            100% { opacity: 0.2; }
        }
    </style>
    <script>
        function showBackButton() {
            const buttons = document.getElementById('header-buttons');
            buttons.classList.add('show');
            
            // Ocultar después de 3 segundos
            setTimeout(function() {
                buttons.classList.remove('show');
            }, 3000);
        }
        
        // Mostrar el botón flotante después de que la página cargue
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                document.getElementById('floating-btn').style.animation = 'bounce 3s infinite, fadeOut 10s forwards';
            }, 500);
        });
    </script>
</head>
<body>
    <div class="header">
        <div id="floating-btn" class="floating-btn" onclick="showBackButton()"></div>
        <div class="header-title">
            Utilidades - Servidor Flask de Neko Bot
        </div>
        <div id="header-buttons" class="header-buttons">
            <a href="/" class="back-btn">← Volver al Inicio</a>
        </div>
    </div>
    <div class="content">
        <h2>🔗 Descargar desde Magnet Link</h2>
        <form action="/magnet" method="post">
            <input type="text" name="magnet" placeholder="Magnet link o URL .torrent" required>
            <button type="submit">Descargar</button>
        </form>

        <h2>🔞 Descargar Doujin</h2>
        <form action="/crear_cbz" method="post">
            <input type="text" name="codigo" placeholder="Código o URL del doujin" required>
            <select name="tipo" required>
                <option value="nh">NHentai</option>
                <option value="h3">3Hentai</option>
                <option value="hito">Hitomi.la</option>
            </select>
            <button type="submit">Crear CBZ</button>
        </form>
    </div>
</body>
</html>
"""

DOWNLOADS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Descargas Activas</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .download-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; background: #fafafa; }
        .progress-bar { background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-fill { background: #4CAF50; height: 100%; transition: width 0.3s; }
        .stats { display: flex; justify-content: space-between; flex-wrap: wrap; }
        .stat-item { margin: 5px 10px; }
        .completed { background: #d4edda; border-color: #c3e6cb; }
        .error { background: #f8d7da; border-color: #f5c6cb; }
        .nav { margin-bottom: 20px; text-align: center; }
        .nav a { margin: 0 10px; text-decoration: none; color: #007bff; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; }
        .auto-refresh { margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">🏠 Inicio</a>
            <a href="/utils">🛠️ Utilidades</a>
            <a href="/downloads">📥 Descargas</a>
        </div>
        
        <h1>📥 Descargas Activas</h1>
        
        <div class="auto-refresh">
            <button class="refresh-btn" onclick="location.reload()">🔄 Actualizar</button>
            <label><input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()"> Auto-actualizar cada 10 segundos</label>
        </div>
        
        {% if downloads %}
            {% for id, download in downloads.items() %}
                <div class="download-card {% if download.state == 'completed' %}completed{% elif download.state == 'error' %}error{% endif %}">
                    <h3>{{ download.filename }}</h3>
                    <p><strong>Estado:</strong> {{ download.state }}</p>
                    <p><strong>Enlace:</strong> <a href="{{ download.link }}" target="_blank">{{ download.link[:50] }}...</a></p>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ download.percent }}%"></div>
                    </div>
                    <p><strong>Progreso:</strong> {{ download.percent }}%</p>
                    
                    <div class="stats">
                        <div class="stat-item"><strong>📦 Descargado:</strong> {{ (download.downloaded / (1024*1024)) | round(2) }} MB</div>
                        <div class="stat-item"><strong>📊 Total:</strong> {{ (download.total_size / (1024*1024)) | round(2) if download.total_size > 0 else 'Calculando...' }} MB</div>
                        <div class="stat-item"><strong>🚀 Velocidad:</strong> {{ (download.speed / (1024*1024)) | round(2) }} MB/s</div>
                        <div class="stat-item"><strong>⏰ Iniciado:</strong> {{ download.start_time[:19] }}</div>
                        {% if download.end_time %}
                        <div class="stat-item"><strong>✅ Completado:</strong> {{ download.end_time[:19] }}</div>
                        {% endif %}
                    </div>
                    
                    {% if download.error %}
                    <p style="color: red;"><strong>Error:</strong> {{ download.error }}</p>
                    {% endif %}
                </div>
            {% endfor %}
        {% else %}
            <p>No hay descargas activas.</p>
        {% endif %}
    </div>

    <script>
        let autoRefreshInterval;
        
        function toggleAutoRefresh() {
            if (document.getElementById('autoRefresh').checked) {
                autoRefreshInterval = setInterval(() => {
                    location.reload();
                }, 10000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }
        
        // Opcional: actualizar automáticamente si hay descargas activas
        {% if downloads %}
        document.addEventListener('DOMContentLoaded', function() {
            const hasActiveDownloads = Object.values({{ downloads|tojson }}).some(d => 
                d.state !== 'completed' && d.state !== 'error'
            );
            if (hasActiveDownloads) {
                document.getElementById('autoRefresh').checked = true;
                toggleAutoRefresh();
            }
        });
        {% endif %}
    </script>
</body>
</html>
"""


