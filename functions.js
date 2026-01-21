function toggleCompress() {
    const section = document.getElementById("compress-section");
    section.style.display = section.style.display === "none" ? "block" : "none";
}

function toggleRename(id) {
    const input = document.getElementById("rename-" + id);
    const btn = document.getElementById("rename-" + id + "-btn");
    input.style.display = input.style.display === "none" ? "inline" : "none";
    btn.style.display = btn.style.display === "none" ? "inline" : "none";
}

function selectAllFiles(selectAll) {
    const checkboxes = document.querySelectorAll('input[name="selected"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
}

function submitForm(form, event) {
    event.preventDefault();
    if (confirm('¿Estás seguro de que quieres realizar esta acción?')) {
        form.submit();
    }
}

let autoRefreshInterval;

function toggleAutoRefresh() {
    if (document.getElementById('autoRefresh').checked) {
        autoRefreshInterval = setInterval(() => {
            location.reload();
        }, 5000);
    } else {
        clearInterval(autoRefreshInterval);
    }
}

function openFullscreen(src) {
    document.getElementById('fullscreen-img').src = src;
    document.getElementById('fullscreen-view').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeFullscreen() {
    document.getElementById('fullscreen-view').style.display = 'none';
    document.body.style.overflow = 'auto';
}

let currentImageIndex = 0;
let totalImages = 0;

function openCascadeModal(index) {
    currentImageIndex = index;
    const modal = document.getElementById('cascadeModal');
    const imageCounter = document.getElementById('imageCounter');
    
    if (imageCounter) {
        imageCounter.textContent = `${index + 1} / ${totalImages}`;
    }
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    const targetImage = document.querySelectorAll('.cascade-modal-image')[index];
    if (targetImage) {
        targetImage.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function closeCascadeModal() {
    const modal = document.getElementById('cascadeModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

function navigateImage(direction) {
    let newIndex = currentImageIndex + direction;
    
    if (newIndex < 0) {
        newIndex = totalImages - 1;
    } else if (newIndex >= totalImages) {
        newIndex = 0;
    }
    
    openCascadeModal(newIndex);
}

function initCascadeGallery(imagesCount) {
    totalImages = imagesCount;
    
    const modal = document.getElementById('cascadeModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this || e.target.classList.contains('cascade-modal-image')) {
                closeCascadeModal();
            }
        });
    }
    
    const modalContent = document.getElementById('cascadeModalContent');
    if (modalContent) {
        modalContent.addEventListener('wheel', function(e) {
            e.preventDefault();
            if (e.deltaY > 0) {
                navigateImage(1);
            } else {
                navigateImage(-1);
            }
        });
    }
    
    document.addEventListener('keydown', function(e) {
        const modal = document.getElementById('cascadeModal');
        if (modal && modal.style.display === 'block') {
            if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                navigateImage(-1);
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                navigateImage(1);
            } else if (e.key === 'Escape') {
                closeCascadeModal();
            }
        }
        
        if (e.key === 'Escape') {
            const fullscreenView = document.getElementById('fullscreen-view');
            if (fullscreenView && fullscreenView.style.display === 'flex') {
                closeFullscreen();
            }
        }
    });
}

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
    const convertButtons = document.querySelectorAll('.convert-btn');
    const convertAllBtn = document.querySelector('.convert-all-btn');
    
    convertAllBtn.disabled = true;
    convertAllBtn.textContent = 'Convirtiendo todas...';
    
    for (let i = 0; i < convertButtons.length; i++) {
        const btn = convertButtons[i];
        const galleryElement = btn.closest('.gallery-item');
        const code = galleryElement.id.replace('gallery-', '');
        const imgElement = document.getElementById(`img-${code}`);
        const originalSrc = imgElement.dataset.originalSrc;
        
        if (originalSrc && !originalSrc.includes('base64') && !originalSrc.includes('via.placeholder.com')) {
            btn.click();
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    convertAllBtn.disabled = false;
    convertAllBtn.textContent = 'Convertir Todas las Imágenes a Base64';
}

async function downloadCBZ(imageLinks, cleanTitle, code) {
    const btn = document.querySelector('.download-btn');
    const progressInfo = document.getElementById('progressInfo');
    
    btn.disabled = true;
    btn.textContent = '⏳ Preparando...';
    
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
        
        progressInfo.textContent = '✅ Descarga completada!';
        btn.textContent = '📥 Descargar CBZ';
        
    } catch (error) {
        console.error('Error en la descarga:', error);
        progressInfo.textContent = '❌ Error en la descarga: ' + error.message;
        btn.textContent = '📥 Reintentar Descarga';
    } finally {
        btn.disabled = false;
        
        setTimeout(() => {
            progressInfo.textContent = '';
        }, 5000);
    }
}

function preloadImages(imageLinks) {
    imageLinks.forEach((url, index) => {
        if (index < 10) {
            const img = new Image();
            img.src = url;
        }
    });
}

function initImageErrorHandling() {
    const images = document.querySelectorAll('img[data-original-src]');
    images.forEach(img => {
        img.addEventListener('error', function() {
            if (this.src && !this.src.includes('via.placeholder.com')) {
                this.src = 'https://via.placeholder.com/200x300?text=Error+cargando+imagen';
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initImageErrorHandling();
    
    const autoRefreshCheckbox = document.getElementById('autoRefresh');
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', toggleAutoRefresh);
    }
});
