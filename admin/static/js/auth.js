// Функция для проверки авторизации
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Функция для добавления токена ко всем запросам
function setupTokenInterceptor() {
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        const token = localStorage.getItem('token');
        if (token) {
            options.headers = options.headers || {};
            options.headers['Authorization'] = `Bearer ${token}`;
        }
        return originalFetch(url, options);
    };
}

// Функция для выхода из системы
function setupLogout() {
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('token');
            window.location.href = '/login';
        });
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    setupTokenInterceptor();
    setupLogout();
    checkAuth();
    
    // Добавляем обработчик для всех ссылок в меню
    document.querySelectorAll('a.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            if (!checkAuth() && !this.href.includes('/login')) {
                e.preventDefault();
            }
        });
    });
});