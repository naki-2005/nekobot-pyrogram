GALLERY_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Galería de Imágenes</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            background-color: #1a1a1a;
            color: white;
        }
        
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 1em; 
            text-align: center; 
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .header a { 
            color: white; 
            text-decoration: none;
            font-weight: bold;
            margin: 0 10px;
            padding: 8px 15px;
            border-radius: 20px;
            background: rgba(255,255,255,0.2);
            transition: all 0.3s ease;
            display: inline-block;
        }
        
        .header a:hover { 
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
            text-decoration: none;
        }
        
        .view-selector {
            text-align: center;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            margin-bottom: 10px;
        }
        
        .view-btn {
            padding: 10px 20px;
            margin: 0 5px;
            background: rgba(255,255,255,0.1);
            color: white;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: bold;
        }
        
        .view-btn:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }
        
        .view-btn.active {
            background: #667eea;
            border-color: #667eea;
        }
        
        .gallery-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .gallery-item {
            position: relative;
            overflow: hidden;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            background: #2a2a2a;
            aspect-ratio: 2/3;
        }
        
        .gallery-item:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        
        .gallery-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: transform 0.5s ease;
        }
        
        .gallery-item:hover img {
            transform: scale(1.1);
        }
        
        .gallery-caption {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, rgba(0,0,0,0.8));
            padding: 15px 10px 10px;
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: center;
        }
        
        .image-counter {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .slideshow-container {
            display: none;
            position: relative;
            max-width: 100vw;
            min-height: 100vh;
            background: #000;
        }
        
        .slideshow-image {
            width: 100%;
            height: 100vh;
            object-fit: contain;
            display: block;
        }
        
        .slideshow-info {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 101;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .progress-bar {
            width: 200px;
            height: 4px;
            background: rgba(255,255,255,0.2);
            border-radius: 2px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: #667eea;
            transition: width 0.3s ease;
        }
        
        .nav-buttons {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 20px;
            z-index: 101;
        }
        
        .nav-btn {
            background: rgba(0,0,0,0.7);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .nav-btn:hover {
            background: rgba(102, 126, 234, 0.8);
            transform: translateY(-2px);
        }
        
        .close-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            z-index: 101;
            transition: all 0.3s ease;
        }
        
        .close-btn:hover {
            background: rgba(220, 53, 69, 0.8);
            transform: rotate(90deg);
        }
        
        .fullscreen-view {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            cursor: pointer;
        }
        
        .fullscreen-img {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
        }
        
        .image-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0,0,0,0.5);
            color: white;
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            transition: all 0.3s ease;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .image-nav:hover {
            background: rgba(102, 126, 234, 0.8);
        }
        
        .image-nav.prev {
            left: 20px;
        }
        
        .image-nav.next {
            right: 20px;
        }
        
        @media (max-width: 768px) {
            .gallery-container {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 10px;
                padding: 10px;
            }
            
            .header a {
                margin: 5px;
                padding: 6px 12px;
                font-size: 14px;
            }
            
            .nav-buttons {
                bottom: 20px;
                gap: 10px;
            }
            
            .nav-btn {
                padding: 10px 20px;
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <a href="/">🏠 Inicio</a>
        <a href="/manga">📖 Manga</a>
        <a href="/utils">🛠️ Utilidades</a>
        <a href="/downloads">📥 Descargas</a>
        <a href="/browse?path={{ current_path }}">📂 Volver al explorador</a>
    </div>

    <div class="view-selector">
        <button class="view-btn active" onclick="showGridView()">🖼️ Vista Cuadrícula</button>
        <button class="view-btn" onclick="showSlideshowView()">🎬 Vista Deslizante</button>
    </div>

    <div class="gallery-container" id="gridView">
        {% for image in image_files %}
        <div class="gallery-item" onclick="openFullscreen('{{ image.url_path }}', {{ loop.index0 }})">
            <div class="image-counter">{{ loop.index }}/{{ image_files|length }}</div>
            <img src="{{ image.url_path }}" 
                 alt="{{ image.name }}" 
                 loading="lazy"
                 onerror="this.src='https://via.placeholder.com/250x375/333/666?text=Error'">
            <div class="gallery-caption">{{ image.name }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="slideshow-container" id="slideshowView">
        <div class="slideshow-info">
            <span id="currentSlide">1</span>/<span id="totalSlides">{{ image_files|length }}</span>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
        </div>
        
        <button class="close-btn" onclick="hideSlideshow()">✕</button>
        
        <div class="nav-buttons">
            <button class="nav-btn" onclick="prevSlide()">
                ◀ Anterior
            </button>
            <button class="nav-btn" onclick="toggleAutoSlide()" id="autoSlideBtn">
                ⏸️ Pausar
            </button>
            <button class="nav-btn" onclick="nextSlide()">
                Siguiente ▶
            </button>
        </div>
        
        {% for image in image_files %}
        <img src="{{ image.url_path }}" 
             alt="{{ image.name }}"
             class="slideshow-image"
             style="display: none;"
             data-index="{{ loop.index0 }}"
             onerror="this.src='https://via.placeholder.com/1920x1080/333/666?text=Error'">
        {% endfor %}
    </div>

    <div class="fullscreen-view" id="fullscreenView" onclick="closeFullscreen()">
        <button class="close-btn" onclick="closeFullscreen()">✕</button>
        <button class="image-nav prev" onclick="navigateFullscreen(-1); event.stopPropagation()">◀</button>
        <img class="fullscreen-img" id="fullscreenImg" src="" onclick="event.stopPropagation()">
        <button class="image-nav next" onclick="navigateFullscreen(1); event.stopPropagation()">▶</button>
        <div class="slideshow-info" style="top: auto; bottom: 20px;">
            <span id="fullscreenCurrent">1</span>/<span id="fullscreenTotal">{{ image_files|length }}</span>
        </div>
    </div>

    <script>
        const imageFiles = {{ image_files|tojson }};
        let currentSlideIndex = 0;
        let autoSlideInterval;
        let isAutoSliding = true;
        let fullscreenIndex = 0;
        
        function showGridView() {
            document.getElementById('gridView').style.display = 'grid';
            document.getElementById('slideshowView').style.display = 'none';
            document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.view-btn')[0].classList.add('active');
            stopAutoSlide();
        }
        
        function showSlideshowView() {
            document.getElementById('gridView').style.display = 'none';
            document.getElementById('slideshowView').style.display = 'block';
            document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.view-btn')[1].classList.add('active');
            showSlide(0);
            startAutoSlide();
        }
        
        function hideSlideshow() {
            showGridView();
        }
        
        function showSlide(index) {
            if (index < 0) index = imageFiles.length - 1;
            if (index >= imageFiles.length) index = 0;
            
            currentSlideIndex = index;
            
            document.querySelectorAll('.slideshow-image').forEach(img => img.style.display = 'none');
            document.querySelectorAll(`.slideshow-image[data-index="${index}"]`).forEach(img => {
                img.style.display = 'block';
            });
            
            document.getElementById('currentSlide').textContent = index + 1;
            document.getElementById('totalSlides').textContent = imageFiles.length;
            
            const progress = ((index + 1) / imageFiles.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
        }
        
        function prevSlide() {
            showSlide(currentSlideIndex - 1);
            resetAutoSlide();
        }
        
        function nextSlide() {
            showSlide(currentSlideIndex + 1);
            resetAutoSlide();
        }
        
        function startAutoSlide() {
            if (autoSlideInterval) clearInterval(autoSlideInterval);
            isAutoSliding = true;
            document.getElementById('autoSlideBtn').innerHTML = '⏸️ Pausar';
            autoSlideInterval = setInterval(nextSlide, 3000);
        }
        
        function stopAutoSlide() {
            if (autoSlideInterval) clearInterval(autoSlideInterval);
            isAutoSliding = false;
            document.getElementById('autoSlideBtn').innerHTML = '▶️ Reanudar';
        }
        
        function toggleAutoSlide() {
            if (isAutoSliding) {
                stopAutoSlide();
            } else {
                startAutoSlide();
            }
        }
        
        function resetAutoSlide() {
            if (isAutoSliding) {
                clearInterval(autoSlideInterval);
                autoSlideInterval = setInterval(nextSlide, 3000);
            }
        }
        
        function openFullscreen(src, index) {
            fullscreenIndex = index;
            const fullscreenView = document.getElementById('fullscreenView');
            const fullscreenImg = document.getElementById('fullscreenImg');
            
            fullscreenImg.src = src;
            document.getElementById('fullscreenCurrent').textContent = index + 1;
            document.getElementById('fullscreenTotal').textContent = imageFiles.length;
            
            fullscreenView.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
        
        function closeFullscreen() {
            document.getElementById('fullscreenView').style.display = 'none';
            document.body.style.overflow = 'auto';
        }
        
        function navigateFullscreen(direction) {
            fullscreenIndex += direction;
            if (fullscreenIndex < 0) fullscreenIndex = imageFiles.length - 1;
            if (fullscreenIndex >= imageFiles.length) fullscreenIndex = 0;
            
            openFullscreen(imageFiles[fullscreenIndex].url_path, fullscreenIndex);
        }
        
        document.addEventListener('keydown', function(e) {
            if (document.getElementById('fullscreenView').style.display === 'flex') {
                if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    navigateFullscreen(-1);
                } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    navigateFullscreen(1);
                } else if (e.key === 'Escape') {
                    closeFullscreen();
                }
            }
            
            if (document.getElementById('slideshowView').style.display === 'block') {
                if (e.key === 'ArrowLeft') {
                    prevSlide();
                } else if (e.key === 'ArrowRight' || e.key === ' ') {
                    nextSlide();
                } else if (e.key === 'Escape') {
                    hideSlideshow();
                }
            }
        });
        
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('slideshowView').addEventListener('wheel', function(e) {
                e.preventDefault();
                if (e.deltaY < 0) {
                    prevSlide();
                } else {
                    nextSlide();
                }
            }, { passive: false });
            
            document.getElementById('slideshowView').addEventListener('click', function(e) {
                if (e.clientX < window.innerWidth / 2) {
                    prevSlide();
                } else {
                    nextSlide();
                }
            });
            
            document.getElementById('fullscreenView').addEventListener('wheel', function(e) {
                e.preventDefault();
                if (e.deltaY < 0) {
                    navigateFullscreen(-1);
                } else {
                    navigateFullscreen(1);
                }
            }, { passive: false });
        });
        
        function preloadImages() {
            imageFiles.forEach((image, index) => {
                if (index < 5) {
                    const img = new Image();
                    img.src = image.url_path;
                }
            });
        }
        
        document.addEventListener('DOMContentLoaded', preloadImages);
    </script>
</body>
</html>
"""
