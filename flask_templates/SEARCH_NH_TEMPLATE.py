SEARCH_NH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Búsqueda nHentai</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .search-form {
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .search-form input {
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            margin: 5px;
            min-width: 200px;
        }
        
        .search-form button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
        }
        
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            padding: 20px 0;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        @media (min-width: 768px) {
            .gallery-grid {
                grid-template-columns: repeat(5, 1fr);
                gap: 20px;
            }
        }
        
        .gallery-item {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        
        .gallery-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .image-container {
            position: relative;
            width: 100%;
            padding-bottom: 140%;
            overflow: hidden;
        }
        
        .gallery-item img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }
        
        .gallery-item:hover img {
            transform: scale(1.05);
        }
        
        .gallery-info {
            padding: 15px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .gallery-name {
            font-weight: 600;
            color: #333;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex: 1;
            min-height: 60px;
        }
        
        .gallery-code {
            color: #666;
            font-size: 14px;
            font-weight: 500;
        }
        
        .gallery-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
        }
        
        .details-link {
            background: #28a745;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 12px;
            text-align: center;
            transition: background 0.3s;
        }
        
        .details-link:hover {
            background: #218838;
            text-decoration: none;
        }
        
        .convert-btn {
            background: #ffc107;
            color: black;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s;
        }
        
        .convert-btn:hover {
            background: #e0a800;
        }
        
        .convert-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            padding: 30px 0;
            flex-wrap: wrap;
        }
        
        .pagination a {
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            transition: transform 0.2s;
        }
        
        .pagination a:hover {
            transform: translateY(-2px);
            text-decoration: none;
        }
        
        .pagination span {
            font-weight: 600;
            color: #333;
            font-size: 16px;
        }
        
        .convert-all-btn {
            background: #17a2b8;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin: 10px;
            transition: background 0.3s;
        }
        
        .convert-all-btn:hover {
            background: #138496;
        }
        
        .convert-all-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .total-results {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        
        .no-results h3 {
            margin-bottom: 10px;
            font-size: 20px;
        }
    </style>
</head>
<body>
    <div class="search-form">
        <form method="GET" action="/api/snh/">
            <input type="text" name="q" value="{{ search_term }}" placeholder="Término de búsqueda" required>
            <input type="number" name="p" value="{{ current_page }}" min="1" placeholder="Página">
            <button type="submit">Buscar</button>
        </form>
        <button class="convert-all-btn" onclick="convertAllImages()">Convertir Todas las Imágenes a Base64</button>
    </div>

    {% if results %}
    <div class="total-results">
        <strong>{{ total_results }}</strong> resultados encontrados - Página {{ current_page }} de {{ total_pages }}
    </div>
    
    <div class="gallery-grid">
        {% for result in results %}
        <div class="gallery-item" id="gallery-{{ result.code }}">
            <div class="image-container">
                {% if result.image_links %}
                <img src="{{ result.image_links[0] }}" 
                     alt="{{ result.name }}" 
                     id="img-{{ result.code }}"
                     data-original-src="{{ result.image_links[0] }}"
                     onerror="this.src='https://via.placeholder.com/300x420/667eea/ffffff?text=Imagen+no+disponible'">
                {% else %}
                <img src="https://via.placeholder.com/300x420/cccccc/ffffff?text=Sin+imagen" 
                     alt="Sin imagen" 
                     id="img-{{ result.code }}" 
                     data-original-src="">
                {% endif %}
            </div>
            
            <div class="gallery-info">
                <div class="gallery-code">Código: {{ result.code }}</div>
                <div class="gallery-name">{{ result.name }}</div>
                
                <div class="gallery-actions">
                    <a href="/api/vnh/{{ result.code }}" class="details-link" target="_blank">
                        Ver Detalles
                    </a>
                    <button class="convert-btn" onclick="convertToBase64('{{ result.code }}')">
                        Convertir a Base64
                    </button>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <div class="pagination">
        {% if current_page > 1 %}
        <a href="/api/snh/{{ search_term }}?p={{ current_page - 1 }}">‹ Página Anterior</a>
        {% endif %}
        
        <span>Página {{ current_page }} de {{ total_pages }}</span>
        
        {% if current_page < total_pages %}
        <a href="/api/snh/{{ search_term }}?p={{ current_page + 1 }}">Página Siguiente ›</a>
        {% endif %}
    </div>
    
    {% else %}
    <div class="no-results">
        <h3>No se encontraron resultados para "{{ search_term }}"</h3>
        <p>Intenta con otros términos de búsqueda</p>
    </div>
    {% endif %}

    <script>
        async function convertToBase64(code) {
            const imgElement = document.getElementById(`img-${code}`);
            const galleryElement = document.getElementById(`gallery-${code}`);
            const btnElement = event.target;
            const originalSrc = imgElement.dataset.originalSrc;
            
            if (!originalSrc || originalSrc.includes('base64') || originalSrc.includes('via.placeholder.com')) {
                return;
            }
            
            btnElement.disabled = true;
            btnElement.textContent = 'Convirtiendo...';
            galleryElement.classList.add('loading');
            
            try {
                const response = await fetch('/api/proxy-image?url=' + encodeURIComponent(originalSrc));
                if (!response.ok) throw new Error('Error en la respuesta');
                
                const blob = await response.blob();
                
                const reader = new FileReader();
                reader.onload = function() {
                    const base64 = reader.result;
                    imgElement.src = base64;
                    btnElement.textContent = '¡Convertida!';
                    galleryElement.classList.remove('loading');
                    
                    setTimeout(() => {
                        btnElement.disabled = false;
                        btnElement.textContent = 'Convertir a Base64';
                    }, 2000);
                };
                reader.readAsDataURL(blob);
                
            } catch (error) {
                console.error('Error convirtiendo imagen:', error);
                btnElement.textContent = 'Error';
                galleryElement.classList.remove('loading');
                
                setTimeout(() => {
                    btnElement.disabled = false;
                    btnElement.textContent = 'Convertir a Base64';
                }, 2000);
            }
        }

        async function convertAllImages() {
            const convertButtons = document.querySelectorAll('.convert-btn:not(:disabled)');
            const convertAllBtn = document.querySelector('.convert-all-btn');
            
            if (convertButtons.length === 0) return;
            
            convertAllBtn.disabled = true;
            convertAllBtn.textContent = 'Convirtiendo todas...';
            
            for (let i = 0; i < convertButtons.length; i++) {
                const btn = convertButtons[i];
                const galleryElement = btn.closest('.gallery-item');
                const code = galleryElement.id.replace('gallery-', '');
                const imgElement = document.getElementById(`img-${code}`);
                const originalSrc = imgElement.dataset.originalSrc;
                
                if (originalSrc && !originalSrc.includes('base64') && !originalSrc.includes('via.placeholder.com')) {
                    const event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    btn.dispatchEvent(event);
                    
                    await new Promise(resolve => setTimeout(resolve, 1500));
                }
            }
            
            convertAllBtn.disabled = false;
            convertAllBtn.textContent = 'Convertir Todas las Imágenes a Base64';
        }

        document.addEventListener('DOMContentLoaded', function() {
            const images = document.querySelectorAll('img[data-original-src]');
            images.forEach(img => {
                img.addEventListener('error', function() {
                    if (this.src && !this.src.includes('via.placeholder.com')) {
                        this.src = 'https://via.placeholder.com/300x420/dc3545/ffffff?text=Error+cargando';
                    }
                });
            });
        });

        function preloadVisibleImages() {
            const images = document.querySelectorAll('img[data-original-src]');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.loaded !== 'true') {
                            img.src = img.dataset.originalSrc;
                            img.dataset.loaded = 'true';
                        }
                        observer.unobserve(img);
                    }
                });
            }, { rootMargin: '50px' });

            images.forEach(img => observer.observe(img));
        }

        document.addEventListener('DOMContentLoaded', preloadVisibleImages);
    </script>
</body>
</html>
'''
