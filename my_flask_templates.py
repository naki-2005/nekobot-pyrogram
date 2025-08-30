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
        .header { background-color: #007BFF; color: white; padding: 1em; text-align: center; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center; position: relative; }
        .header a { color: white; text-decoration: underline; font-weight: bold; }
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
        .utils-btn { 
            display: none;
            background-color: #28a745; 
            padding: 0.5em 1em; 
            border-radius: 4px; 
            color: white;
            text-decoration: none;
        }
        .utils-btn.show {
            display: block;
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
            document.getElementById('utils-btn').classList.add('show');
            document.getElementById('floating-btn').style.display = 'none';
            
            // Ocultar después de 3 segundos si no se interactúa
            setTimeout(function() {
                if (!document.getElementById('utils-btn').matches(':hover')) {
                    document.getElementById('utils-btn').classList.remove('show');
                    document.getElementById('floating-btn').style.display = 'block';
                }
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
        <span>Servidor Flask de Neko Bot creado por <a href="https://t.me/nakigeplayer" target="_blank">Naki</a></span>
        <div id="floating-btn" class="floating-btn" onclick="showUtilsButton()"></div>
        <a href="/utils" id="utils-btn" class="utils-btn">⚙️ Utilidades</a>
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
        .header { background-color: #007BFF; color: white; padding: 1em; text-align: center; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center; position: relative; }
        .header a { color: white; text-decoration: underline; font-weight: bold; }
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
        .back-btn { 
            display: none;
            background-color: #6c757d; 
            padding: 0.5em 1em; 
            border-radius: 4px; 
            color: white;
            text-decoration: none;
        }
        .back-btn.show {
            display: block;
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
            document.getElementById('back-btn').classList.add('show');
            document.getElementById('floating-btn').style.display = 'none';
            
            // Ocultar después de 3 segundos si no se interactúa
            setTimeout(function() {
                if (!document.getElementById('back-btn').matches(':hover')) {
                    document.getElementById('back-btn').classList.remove('show');
                    document.getElementById('floating-btn').style.display = 'block';
                }
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
        <a href="/" id="back-btn" class="back-btn">← Volver</a>
        <span>Utilidades - Servidor Flask de Neko Bot</span>
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
