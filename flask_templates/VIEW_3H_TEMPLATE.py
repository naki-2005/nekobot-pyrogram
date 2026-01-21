VIEW_3H_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }} - 3Hentai</title>
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
            max-width: 1200px;
            margin: 0 auto;
        }
        .gallery-header {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        @media (min-width: 768px) {
            .gallery-header {
                flex-direction: row;
                align-items: flex-start;
            }
        }
        .cover-container {
            flex-shrink: 0;
            width: 100%;
            max-width: 300px;
            margin: 0 auto;
        }
        @media (min-width: 768px) {
            .cover-container {
                width: 300px;
                margin: 0;
            }
        }
        .cover-image {
            width: 100%;
            height: 400px;
            object-fit: cover;
            border-radius: 8px;
            cursor: pointer;
        }
        .info-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .gallery-title {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            line-height: 1.3;
        }
        .gallery-code {
            color: #666;
            font-size: 16px;
            margin-bottom: 10px;
        }
        .tags-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .tag-category {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: flex-start;
        }
        .tag-category strong {
            min-width: 80px;
            color: #333;
            font-size: 14px;
        }
        .tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            flex: 1;
        }
        .tag {
            background: #e9ecef;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            color: #495057;
        }
        .download-section {
            margin-top: 10px;
        }
        .download-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .download-btn:hover {
            background: #218838;
        }
        .download-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .progress-info {
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
        .gallery-section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .gallery-title-section {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        @media (min-width: 768px) {
            .gallery-grid {
                grid-template-columns: repeat(5, 1fr);
                gap: 15px;
            }
        }
        .gallery-item {
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .gallery-item:hover {
            transform: scale(1.05);
        }
        .gallery-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            position: relative;
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .modal-image {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            transition: transform 0.3s ease;
        }
        .image-counter {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: white;
            background: rgba(0,0,0,0.7);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 1001;
        }
        .modal-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        .loading {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="gallery-header">
        <div class="cover-container">
            <img src="{{ cover_image }}" 
                 alt="{{ title }}" 
                 class="cover-image"
                 onclick="openModal(0)"
                 onerror="this.src='https://via.placeholder.com/300x400?text=Cover+no+disponible'">
        </div>
        <div class="info-container">
            <div>
                <div class="gallery-code">Código: {{ code }}</div>
                <h1 class="gallery-title">{{ title }}</h1>
                <div class="gallery-code">Total de páginas: {{ total_pages }}</div>
            </div>
            <div class="tags-section">
                {% for category, tags in tags.items() %}
                <div class="tag-category">
                    <strong>{{ category }}:</strong>
                    <div class="tag-list">
                        {% for tag in tags %}
                        <span class="tag">{{ tag }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
            <div class="download-section">
                <button class="download-btn" onclick="downloadCBZ()">
                    Descargar CBZ
                </button>
                <div class="progress-info" id="progressInfo"></div>
            </div>
        </div>
    </div>
    <div class="gallery-section">
        <h2 class="gallery-title-section">Galería de Imágenes ({{ image_links|length }})</h2>
        <div class="gallery-grid">
            {% for image_url in image_links %}
            <div class="gallery-item" onclick="openModal({{ loop.index0 }})">
                <img src="{{ image_url }}" 
                     alt="Imagen {{ loop.index }}" 
                     class="gallery-image"
                     onerror="this.src='https://via.placeholder.com/200x300?text=Error+cargando'"
                     loading="lazy">
            </div>
            {% endfor %}
        </div>
    </div>
    <div class="modal" id="imageModal">
        <div class="image-counter" id="imageCounter"></div>
        <div class="modal-content">
            <div class="modal-overlay" onclick="closeModal()"></div>
            <img class="modal-image" id="modalImage" src="" onclick="closeModal()">
        </div>
    </div>
    <script>
        let currentImageIndex = 0;
        const totalImages = {{ image_links|length }};
        const imageLinks = {{ image_links|tojson }};
        const cleanTitle = "{{ clean_title }}";
        const code = "{{ code }}";
        let touchStartY = 0;
        let touchEndY = 0;
        
        function openModal(index) {
            currentImageIndex = index;
            const modal = document.getElementById('imageModal');
            const modalImage = document.getElementById('modalImage');
            const imageCounter = document.getElementById('imageCounter');
            
            modalImage.src = imageLinks[index];
            imageCounter.textContent = `${index + 1} / ${totalImages}`;
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            
            modalImage.addEventListener('touchstart', handleTouchStart, false);
            modalImage.addEventListener('touchend', handleTouchEnd, false);
        }
        
        function closeModal() {
            const modal = document.getElementById('imageModal');
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
        
        function handleTouchStart(event) {
            touchStartY = event.changedTouches[0].screenY;
        }
        
        function handleTouchEnd(event) {
            touchEndY = event.changedTouches[0].screenY;
            handleSwipe();
        }
        
        function handleSwipe() {
            const swipeDistance = touchStartY - touchEndY;
            const swipeThreshold = 50;
            
            if (Math.abs(swipeDistance) > swipeThreshold) {
                if (swipeDistance > 0) {
                    navigateImage(1);
                } else {
                    navigateImage(-1);
                }
            }
        }
        
        function navigateImage(direction) {
            let newIndex = currentImageIndex + direction;
            if (newIndex < 0) {
                newIndex = totalImages - 1;
            } else if (newIndex >= totalImages) {
                newIndex = 0;
            }
            openModal(newIndex);
        }
        
        document.addEventListener('keydown', function(e) {
            const modal = document.getElementById('imageModal');
            if (modal.style.display === 'flex') {
                if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                    navigateImage(-1);
                } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                    navigateImage(1);
                } else if (e.key === 'Escape') {
                    closeModal();
                }
            }
        });
        
        document.getElementById('imageModal').addEventListener('wheel', function(e) {
            e.preventDefault();
            if (e.deltaY < 0) {
                navigateImage(-1);
            } else {
                navigateImage(1);
            }
        }, { passive: false });
        
        async function downloadCBZ() {
            const btn = document.querySelector('.download-btn');
            const progressInfo = document.getElementById('progressInfo');
            
            btn.disabled = true;
            btn.textContent = 'Preparando...';
            
            try {
                const formData = new FormData();
                formData.append('title', cleanTitle);
                formData.append('code', code);
                
                let downloadedCount = 0;
                
                for (let i = 0; i < imageLinks.length; i++) {
                    progressInfo.textContent = `Descargando ${i + 1}/${imageLinks.length}`;
                    
                    try {
                        const response = await fetch('/api/proxy-image?url=' + encodeURIComponent(imageLinks[i]));
                        if (!response.ok) throw new Error('HTTP error ' + response.status);
                        
                        const blob = await response.blob();
                        const contentType = response.headers.get('content-type');
                        let ext = '.jpg';
                        
                        if (contentType) {
                            if (contentType.includes('jpeg') || contentType.includes('jpg')) {
                                ext = '.jpg';
                            } else if (contentType.includes('png')) {
                                ext = '.png';
                            } else if (contentType.includes('webp')) {
                                ext = '.webp';
                            } else if (contentType.includes('gif')) {
                                ext = '.gif';
                            }
                        }
                        
                        const filename = `image_${i + 1}${ext}`;
                        formData.append(`file_${i}`, blob, filename);
                        downloadedCount++;
                        
                    } catch (error) {
                        console.error(`Error descargando imagen ${i + 1}:`, error);
                        progressInfo.textContent = `Error en imagen ${i + 1}, continuando...`;
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                }
                
                progressInfo.textContent = 'Creando CBZ...';
                
                const response = await fetch('/api/create-cbz', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Error al crear CBZ');
                }
                
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${cleanTitle}_${code}.cbz`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                progressInfo.textContent = 'Descarga completada!';
                btn.textContent = 'Descargar CBZ';
                
            } catch (error) {
                console.error('Error en la descarga:', error);
                progressInfo.textContent = 'Error en la descarga: ' + error.message;
                btn.textContent = 'Reintentar Descarga';
            } finally {
                btn.disabled = false;
                setTimeout(() => {
                    progressInfo.textContent = '';
                }, 5000);
            }
        }
        
        function preloadImages() {
            imageLinks.forEach((url, index) => {
                if (index < 10) {
                    const img = new Image();
                    img.src = url;
                }
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            preloadImages();
        });
    </script>
</body>
</html>
'''
