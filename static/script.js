let imagePreviewModal;
let iCloudLoginModal;
let currentQuery = '';
let currentPage = 1;
let isLoading = false;
let hasMore = true;

document.addEventListener('DOMContentLoaded', function() {
    const imagePreviewModalElement = document.getElementById('imagePreviewModal');
    const iCloudLoginModalElement = document.getElementById('iCloudLoginModal');
    
    if (imagePreviewModalElement) {
        imagePreviewModal = new bootstrap.Modal(imagePreviewModalElement);
    }
    
    if (iCloudLoginModalElement) {
        iCloudLoginModal = new bootstrap.Modal(iCloudLoginModalElement);
    }
    
    // Добавляем слушатель прокрутки
    window.addEventListener('scroll', function() {
        if ((window.innerHeight + window.scrollY) >= document.documentElement.scrollHeight - 500) {
            if (!isLoading && hasMore && currentQuery) {
                loadMore();
            }
        }
    });

    // Проверяем статус авторизации при загрузке
    checkICloudAuth();
});

function showLoading() {
    isLoading = true;
    document.getElementById('loading').classList.remove('d-none');
}

function hideLoading() {
    isLoading = false;
    document.getElementById('loading').classList.add('d-none');
}

function showImagePreview(imagePath, confidence, originalPath) {
    const previewImage = document.getElementById('previewImage');
    const imageInfo = document.getElementById('imageInfo');
    
    previewImage.src = imagePath;
    imageInfo.innerHTML = `
        <div><strong>Путь:</strong> ${originalPath}</div>
        <div><strong>Уверенность:</strong> ${confidence}%</div>
    `;
    
    imagePreviewModal.show();
}

async function search(event) {
    event.preventDefault();
    const query = document.getElementById('query').value;
    
    // Проверяем наличие индекса перед поиском
    try {
        const indexCheck = await fetch('/check_index');
        const indexData = await indexCheck.json();
        
        if (!indexData.exists) {
            showNotification('info', 'Изображения ещё не проиндексированы. Начинаем индексацию...');
            updateIndex();
            return;
        }
    } catch (error) {
        console.error('Ошибка при проверке индекса:', error);
    }
    
    // Сбрасываем состояние при новом поиске
    currentQuery = query;
    currentPage = 1;
    hasMore = true;
    
    showLoading();
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                query: query,
                page: currentPage,
                per_page: 30
            })
        });
        
        const data = await response.json();
        
        if (data.error === 'no_index') {
            showNotification('info', 'Изображения ещё не проиндексированы. Начинаем индексацию...');
            updateIndex();
            return;
        }
        
        hasMore = data.has_more;
        displayResults(data.results, true);
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification('error', 'Произошла ошибка при поиске');
    } finally {
        hideLoading();
    }
}

async function loadMore() {
    if (isLoading || !hasMore) return;
    
    currentPage++;
    showLoading();
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                query: currentQuery,
                page: currentPage,
                per_page: 30
            })
        });
        
        const data = await response.json();
        hasMore = data.has_more;
        displayResults(data.results, false);
    } catch (error) {
        console.error('Ошибка при загрузке дополнительных результатов:', error);
        currentPage--; // Откатываем страницу при ошибке
    } finally {
        hideLoading();
    }
}

function displayResults(results, clearExisting = true) {
    const resultsDiv = document.getElementById('results');
    
    if (clearExisting) {
        resultsDiv.innerHTML = '';
    }
    
    if (results.length === 0 && clearExisting) {
        resultsDiv.innerHTML = `
            <div class="col-12 text-center">
                <h3 class="text-muted">Изображений не найдено</h3>
            </div>
        `;
        return;
    }
    
    results.forEach((result, index) => {
        const confidence = (result.score * 100).toFixed(1);
        const imagePath = '/image/' + encodeURIComponent(result.path);
        
        const div = document.createElement('div');
        div.innerHTML = `
            <div class="image-card shadow" onclick="showImagePreview('${imagePath}', ${confidence}, '${result.path}')">
                <div class="confidence-badge">
                    <i class="fas fa-percentage me-1"></i>${confidence}%
                </div>
                <img src="${imagePath}" alt="Результат ${index + 1}" loading="lazy">
                <div class="image-info">
                    <p class="mb-0 text-truncate">${result.path}</p>
                </div>
            </div>
        `;
        
        resultsDiv.appendChild(div);
    });
    
    // Добавляем индикатор загрузки в конце, если есть ещё результаты
    if (hasMore) {
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'text-center mt-4 mb-4';
        loadingIndicator.innerHTML = `
            <div class="text-muted">Прокрутите вниз для загрузки дополнительных результатов</div>
        `;
        resultsDiv.appendChild(loadingIndicator);
    }
}

async function updateIndex() {
    const indexingStatus = document.getElementById('indexing-status');
    const progressBar = indexingStatus.querySelector('.progress-bar');
    const progressText = indexingStatus.querySelector('.progress-text');
    const infoPanel = document.getElementById('infoPanel');
    
    // Скрываем информационную панель
    infoPanel.style.display = 'none';
    
    // Показываем статус
    indexingStatus.style.display = 'block';
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    progressText.textContent = 'Обновление индекса...';
    
    try {
        const response = await fetch('/update_index', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Запускаем опрос статуса
            checkIndexingStatus();
        } else {
            progressText.textContent = 'Ошибка при обновлении индекса: ' + (result.error || 'Неизвестная ошибка');
            progressBar.style.width = '0%';
            
            setTimeout(() => {
                indexingStatus.style.display = 'none';
            }, 5000);
        }
    } catch (error) {
        progressText.textContent = 'Ошибка при обновлении индекса: ' + error.message;
        progressBar.style.width = '0%';
        
        setTimeout(() => {
            indexingStatus.style.display = 'none';
        }, 5000);
    }
}

async function checkIndexingStatus() {
    const indexingStatus = document.getElementById('indexing-status');
    const progressBar = indexingStatus.querySelector('.progress-bar');
    const progressText = indexingStatus.querySelector('.progress-text');
    
    try {
        const response = await fetch('/indexing_status');
        const data = await response.json();
        
        if (data.status === 'running') {
            const progress = data.total > 0 ? (data.current / data.total) * 100 : 0;
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${Math.round(progress)}%`;
            progressText.textContent = data.message;
            
            // Продолжаем опрос каждые 500мс
            setTimeout(checkIndexingStatus, 500);
        } else if (data.status === 'completed') {
            progressBar.style.width = '100%';
            progressBar.textContent = '100%';
            progressText.textContent = 'Индексация завершена!';
            
            // Обновляем статистику
            updateStatistics();
            
            // Скрываем через 3 секунды
            setTimeout(() => {
                indexingStatus.style.display = 'none';
            }, 3000);
        } else if (data.status === 'error') {
            progressText.textContent = 'Ошибка: ' + data.message;
            
            setTimeout(() => {
                indexingStatus.style.display = 'none';
            }, 5000);
        }
    } catch (error) {
        progressText.textContent = 'Ошибка при получении статуса: ' + error.message;
        
        setTimeout(() => {
            indexingStatus.style.display = 'none';
        }, 5000);
    }
}

async function checkICloudAuth() {
    try {
        const response = await fetch('/icloud/check_auth');
        const data = await response.json();
        
        const syncButton = document.getElementById('syncButton');
        if (syncButton && !data.authenticated) {
            syncButton.onclick = showICloudLogin;
        }
    } catch (error) {
        console.error('Ошибка при проверке авторизации:', error);
    }
}

function showICloudLogin() {
    if (iCloudLoginModal) {
        iCloudLoginModal.show();
    }
}

function showNotification(type, messageKey, duration = 5000) {
    const texts = translations[userSettings.getLanguage()];
    const message = texts[messageKey] || messageKey;
    
    const notificationId = type === 'error' ? 'errorNotification' : 'successNotification';
    const notification = document.getElementById(notificationId);
    
    if (notification) {
        notification.textContent = message;
        notification.style.display = 'block';
        
        setTimeout(() => {
            notification.style.display = 'none';
        }, duration);
    }
}

async function stopSync() {
    try {
        const response = await fetch('/icloud/stop_sync', {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('success', 'Синхронизация остановлена');
        } else {
            showNotification('error', data.error || 'Не удалось остановить синхронизацию');
        }
    } catch (error) {
        showNotification('error', 'Ошибка при остановке синхронизации');
    }
}

async function submitICloudLogin() {
    const emailInput = document.getElementById('icloud-email');
    const passwordInput = document.getElementById('icloud-password');
    const rememberCheckbox = document.getElementById('remember-credentials');
    const syncButton = document.getElementById('syncButton');
    
    if (!emailInput || !passwordInput || !rememberCheckbox || !syncButton) {
        showNotification('error', 'Ошибка: не найдены элементы формы');
        return;
    }

    const email = emailInput.value;
    const password = passwordInput.value;
    const remember = rememberCheckbox.checked;

    if (!email || !password) {
        showNotification('error', 'Пожалуйста, введите email и пароль');
        return;
    }

    try {
        console.log('Отправка запроса на подключение к iCloud...');
        syncButton.disabled = true;
        showNotification('success', 'Подключение к iCloud...');

        const connectResponse = await fetch('/icloud/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: email,
                password: password,
                remember: remember
            })
        });

        const connectData = await connectResponse.json();
        console.log('Ответ сервера:', connectData);
        
        if (!connectData.success) {
            if (connectData.message.includes('двухфакторная аутентификация')) {
                console.log('Требуется двухфакторная аутентификация');
                const code = prompt('Введите код подтверждения из iCloud:');
                if (!code) {
                    throw new Error('Код подтверждения не введен');
                }
                
                console.log('Отправка кода подтверждения...');
                const verifyResponse = await fetch('/icloud/verify_2fa', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ code })
                });
                
                const verifyData = await verifyResponse.json();
                console.log('Ответ сервера (2FA):', verifyData);
                if (!verifyData.success) {
                    throw new Error('Неверный код подтверждения');
                }
            } else {
                throw new Error(connectData.message);
            }
        }

        // Закрываем модальное окно
        if (iCloudLoginModal) {
            iCloudLoginModal.hide();
        }
        
        // Привязываем функции к кнопкам
        const syncButtonElement = document.getElementById('syncButton');
        const stopSyncButtonElement = document.getElementById('stopSyncButton');
        
        if (syncButtonElement) {
            syncButtonElement.onclick = syncWithICloud;
        }
        if (stopSyncButtonElement) {
            stopSyncButtonElement.onclick = stopSync;
        }
        
        console.log('Начинаем синхронизацию...');
        // Начинаем синхронизацию
        await syncWithICloud();

    } catch (error) {
        console.error('Ошибка при подключении:', error);
        showNotification('error', `Ошибка: ${error.message}`);
    } finally {
        if (syncButton) {
            syncButton.disabled = false;
        }
    }
}

function syncWithICloud() {
    const syncButton = document.getElementById('syncButton');
    const stopSyncButton = document.getElementById('stopSyncButton');
    const syncStatus = document.getElementById('syncStatus');
    
    if (!syncButton || !stopSyncButton || !syncStatus) {
        console.error('Не найдены необходимые элементы интерфейса');
        showNotification('error', 'Ошибка инициализации интерфейса');
        return;
    }

    syncButton.disabled = true;
    stopSyncButton.style.display = 'inline-block';
    syncStatus.style.display = 'block';
    
    fetch('/icloud/sync', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSyncProgress();
            } else {
                showNotification('error', data.error || 'Ошибка при запуске синхронизации');
                if (syncStatus) syncStatus.style.display = 'none';
                if (stopSyncButton) stopSyncButton.style.display = 'none';
                if (syncButton) syncButton.disabled = false;
            }
        })
        .catch(error => {
            console.error('Ошибка при запуске синхронизации:', error);
            showNotification('error', 'Ошибка при запуске синхронизации');
            if (syncStatus) syncStatus.style.display = 'none';
            if (stopSyncButton) stopSyncButton.style.display = 'none';
            if (syncButton) syncButton.disabled = false;
        });
}

function updateSyncProgress() {
    fetch('/icloud/sync_status')
        .then(response => response.json())
        .then(data => {
            const syncStatus = document.getElementById('syncStatus');
            if (!syncStatus) return;

            const progressBar = syncStatus.querySelector('.progress-bar');
            const progressText = syncStatus.querySelector('.progress-text');
            const newPhotosText = syncStatus.querySelector('.new-photos-text');
            const errorList = syncStatus.querySelector('.error-list');
            const stopSyncButton = document.getElementById('stopSyncButton');
            const syncButton = document.getElementById('syncButton');
            
            // Показываем статус синхронизации
            syncStatus.style.display = 'block';
            
            if (data.status === 'syncing') {
                const progress = data.total > 0 ? (data.downloaded / data.total) * 100 : 0;
                
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                    progressBar.textContent = `${Math.round(progress)}%`;
                    progressBar.setAttribute('aria-valuenow', progress);
                }
                
                if (progressText) {
                    progressText.textContent = `Загружено ${data.downloaded} из ${data.total} фотографий`;
                }
                
                if (newPhotosText) {
                    newPhotosText.textContent = `Новых фотографий: ${data.new_photos}`;
                }
                
                if (errorList && data.failed_photos && data.failed_photos.length > 0) {
                    errorList.style.display = 'block';
                    const ul = errorList.querySelector('ul');
                    if (ul) {
                        ul.innerHTML = data.failed_photos
                            .map(file => `<li>${file}</li>`)
                            .join('');
                    }
                }
                
                // Продолжаем опрос каждую секунду
                setTimeout(updateSyncProgress, 1000);
            } else if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
                if (data.status === 'completed') {
                    showNotification('success', 'Синхронизация завершена успешно!');
                } else if (data.status === 'error') {
                    showNotification('error', data.message || 'Произошла ошибка при синхронизации');
                }
                
                if (stopSyncButton) {
                    stopSyncButton.style.display = 'none';
                }
                
                if (syncButton) {
                    syncButton.disabled = false;
                }
                
                // Показываем финальный результат еще некоторое время
                setTimeout(() => {
                    syncStatus.style.display = 'none';
                }, 5000);
            }
        })
        .catch(error => {
            console.error('Ошибка при получении статуса синхронизации:', error);
            showNotification('error', 'Ошибка при получении статуса синхронизации');
        });
}

// Добавляем обработчик события для кнопки синхронизации
document.getElementById('syncButton').addEventListener('click', syncWithICloud);

// Функция для переключения темы
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Обновляем иконку
    const themeIcon = document.querySelector('#themeToggle i');
    themeIcon.className = newTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
}

// Функция для обновления текстов на странице
function updateTexts() {
    const currentLang = userSettings.getLanguage();
    const texts = translations[currentLang];
    
    // Обновляем все элементы с атрибутом data-translate
    document.querySelectorAll('[data-translate]').forEach(element => {
        const key = element.getAttribute('data-translate');
        if (element.tagName === 'INPUT' && element.getAttribute('placeholder')) {
            element.placeholder = texts[key];
        } else {
            element.textContent = texts[key];
        }
    });
    
    // Обновляем заголовок страницы
    document.title = texts.title;
    
    // Обновляем текст кнопки языка
    const langButton = document.getElementById('languageToggle');
    langButton.innerHTML = `<i class="fas fa-globe me-1"></i>${currentLang.toUpperCase()}`;
}

// Функция для переключения языка
function toggleLanguage() {
    const currentLang = userSettings.getLanguage();
    const newLang = currentLang === 'en' ? 'ru' : 'en';
    userSettings.setLanguage(newLang);
    document.documentElement.setAttribute('lang', newLang);
    updateTexts();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Инициализация темы
    const savedTheme = userSettings.getTheme();
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const themeIcon = document.querySelector('#themeToggle i');
    themeIcon.className = savedTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    
    // Добавляем обработчики для кнопок
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('languageToggle').addEventListener('click', toggleLanguage);
    
    // Устанавливаем язык
    const savedLang = userSettings.getLanguage();
    document.documentElement.setAttribute('lang', savedLang);
    updateTexts();
    
    // Проверяем индекс и загружаем статистику
    checkIndex();
    updateStatistics();
    
    // Обновляем статистику каждые 30 секунд
    setInterval(updateStatistics, 30000);
});

// Добавляем функцию для обновления статистики
async function updateStatistics() {
    try {
        const response = await fetch('/stats');
        const data = await response.json();
        const texts = translations[userSettings.getLanguage()];
        
        document.getElementById('totalImages').textContent = data.total_images || '0';
        document.getElementById('lastUpdate').textContent = data.last_update || texts.never;
        document.getElementById('syncStatus').textContent = data.sync_status || texts.notSynced;
    } catch (error) {
        console.error('Error updating statistics:', error);
    }
}

// Функция для проверки наличия индекса
async function checkIndex() {
    try {
        const response = await fetch('/check_index');
        const data = await response.json();
        
        if (!data.exists) {
            const infoPanel = document.getElementById('infoPanel');
            const infoPanelText = document.getElementById('infoPanelText');
            const texts = translations[userSettings.getLanguage()];
            
            infoPanelText.textContent = texts.noIndex;
            infoPanel.style.display = 'block';
            
            updateIndex();
        }
    } catch (error) {
        console.error('Error checking index:', error);
    }
} 