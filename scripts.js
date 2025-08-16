// Alternar entre modo claro y oscuro
function toggleMode() {
    const body = document.body;
    const button = document.querySelector('.mode-toggle');

    // Alternar la clase de modo claro en el cuerpo
    body.classList.toggle('modo-claro');

    // Cambiar el texto del botón dinámicamente
    button.textContent = body.classList.contains('modo-claro') ? 'Modo Oscuro' : 'Modo Claro';
}

// Alternar la visibilidad de la lista
function toggleList() {
    const tutorialList = document.getElementById('tutorial-list');

    // Alternar la clase "visible" en la lista
    tutorialList.classList.toggle('visible');
}
