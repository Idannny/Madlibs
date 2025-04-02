document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const loadingScreen = document.getElementById('loading-screen');

    form.addEventListener('submit', function() {
        console.log("hey alert")
        loadingScreen.style.display = 'flex';
    });
});