// Основные функции для админ-панели

// Функция для получения токена из localStorage
function getToken() {
    return localStorage.getItem('token');
}

// Функция для установки токена в localStorage
function setToken(token) {
    localStorage.setItem('token', token);
}

// Функция для удаления токена из localStorage
function removeToken() {
    localStorage.removeItem('token');
}

// Функция для проверки авторизации
function checkAuth() {
    const token = getToken();
    if (!token && window.location.pathname !== '/login') {
        window.location.href = '/login';
    }
}

// Функция для выполнения API запросов с авторизацией
async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    
    // Если нет токена и это не запрос на авторизацию, перенаправляем на страницу входа
    if (!token && !url.includes('/token')) {
        window.location.href = '/login';
        return;
    }
    
    // Добавляем заголовок авторизации, если есть токен
    const headers = options.headers || {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Добавляем заголовок Content-Type, если его нет
    if (!headers['Content-Type'] && options.method && options.method !== 'GET') {
        headers['Content-Type'] = 'application/json';
    }
    
    // Выполняем запрос
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    // Если получили 401 (Unauthorized), перенаправляем на страницу входа
    if (response.status === 401) {
        removeToken();
        window.location.href = '/login';
        return;
    }
    
    return response;
}

// Функция для отображения уведомлений
function showToast(message, type = 'success') {
    // Создаем элемент toast
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    const toastContent = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastElement.innerHTML = toastContent;
    
    // Добавляем toast в контейнер
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toastElement);
    
    // Инициализируем и показываем toast
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 3000
    });
    toast.show();
}

// Функция для экспорта данных в CSV
function exportToCSV(data, filename) {
    // Проверяем, что данные не пустые
    if (!data || !data.length) {
        showToast('Нет данных для экспорта', 'warning');
        return;
    }
    
    // Получаем заголовки из первого объекта
    const headers = Object.keys(data[0]);
    
    // Создаем строки CSV
    const csvRows = [];
    
    // Добавляем заголовки
    csvRows.push(headers.join(','));
    
    // Добавляем данные
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            // Экранируем кавычки и оборачиваем значение в кавычки, если оно содержит запятую или перенос строки
            const escaped = String(value).replace(/"/g, '""');
            return `"${escaped}"`;
        });
        csvRows.push(values.join(','));
    }
    
    // Объединяем все строки с переносами строки
    const csvString = csvRows.join('\n');
    
    // Создаем Blob с данными CSV
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    
    // Создаем ссылку для скачивания
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Функция для форматирования даты
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Функция для создания пагинации
function createPagination(currentPage, totalPages, onPageChange) {
    const paginationElement = document.createElement('nav');
    paginationElement.setAttribute('aria-label', 'Навигация по страницам');
    
    const ulElement = document.createElement('ul');
    ulElement.className = 'pagination';
    
    // Кнопка "Предыдущая"
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.textContent = 'Предыдущая';
    
    if (currentPage > 1) {
        prevLink.addEventListener('click', (e) => {
            e.preventDefault();
            onPageChange(currentPage - 1);
        });
    }
    
    prevLi.appendChild(prevLink);
    ulElement.appendChild(prevLi);
    
    // Номера страниц
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
        
        const pageLink = document.createElement('a');
        pageLink.className = 'page-link';
        pageLink.href = '#';
        pageLink.textContent = i;
        
        pageLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (i !== currentPage) {
                onPageChange(i);
            }
        });
        
        pageLi.appendChild(pageLink);
        ulElement.appendChild(pageLi);
    }
    
    // Кнопка "Следующая"
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.textContent = 'Следующая';
    
    if (currentPage < totalPages) {
        nextLink.addEventListener('click', (e) => {
            e.preventDefault();
            onPageChange(currentPage + 1);
        });
    }
    
    nextLi.appendChild(nextLink);
    ulElement.appendChild(nextLi);
    
    paginationElement.appendChild(ulElement);
    return paginationElement;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем авторизацию на всех страницах, кроме страницы входа
    if (window.location.pathname !== '/login') {
        checkAuth();
    }
    
    // Обработчик формы входа
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);
                
                const response = await fetch('/token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    setToken(data.access_token);
                    window.location.href = '/';
                } else {
                    const error = await response.json();
                    showToast(error.detail || 'Ошибка входа', 'danger');
                }
            } catch (error) {
                showToast('Ошибка при выполнении запроса', 'danger');
                console.error('Ошибка:', error);
            }
        });
    }
    
    // Обработчик кнопки выхода
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            removeToken();
            window.location.href = '/logout';
        });
    }
});