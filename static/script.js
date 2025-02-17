let imagePreviewModal;
let iCloudLoginModal;
let currentQuery = '';
let currentPage = 1;
let isLoading = false;
let hasMore = true;

// Добавляем переменные для отслеживания времени
let progressStartTime = null;
let lastProgressUpdate = null;
let lastProgressPercent = 0;

document.addEventListener('DOMContentLoaded', function() {
    const imagePreviewModalElement = document.getElementById('imagePreviewModal');
    const iCloudLoginModalElement = document.getElementById('iCloudLoginModal');
    
    if (imagePreviewModalElement) {
        imagePreviewModal = new bootstrap.Modal(imagePreviewModalElement);
        
        // Добавляем обработчик закрытия модального окна
        imagePreviewModalElement.addEventListener('hidden.bs.modal', function () {
            const videoElement = document.getElementById('previewVideo');
            if (videoElement) {
                videoElement.pause();
                videoElement.currentTime = 0;
            }
        });
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

    // Загружаем сохраненные настройки
    loadSavedTheme();
    loadSavedLanguage();
});

function showLoading() {
    isLoading = true;
    document.getElementById('loading').classList.remove('d-none');
}

function hideLoading() {
    isLoading = false;
    document.getElementById('loading').classList.add('d-none');
}

function showImagePreview(mediaPath, confidence, originalPath) {
    const previewContainer = document.getElementById('previewImage').parentElement;
    const previewImage = document.getElementById('previewImage');
    const imageInfo = document.getElementById('imageInfo');
    
    // Определяем тип файла по расширению
    const fileExt = mediaPath.toLowerCase().split('.').pop();
    const videoExtensions = ['mp4', 'mov', 'avi', 'mkv'];
    
    if (videoExtensions.includes(fileExt)) {
        // Если это видео, создаем и показываем видео элемент
        previewImage.style.display = 'none';
        let videoElement = document.getElementById('previewVideo');
        if (!videoElement) {
            videoElement = document.createElement('video');
            videoElement.id = 'previewVideo';
            videoElement.className = 'img-fluid';
            videoElement.controls = true;
            previewContainer.insertBefore(videoElement, previewImage);
        } else {
            videoElement.style.display = 'block';
        }
        videoElement.src = mediaPath;
    } else {
        // Если это изображение, показываем img элемент
        const videoElement = document.getElementById('previewVideo');
        if (videoElement) {
            videoElement.style.display = 'none';
            videoElement.src = '';
        }
        previewImage.style.display = 'block';
        previewImage.src = mediaPath;
    }
    
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
                <h3 class="text-muted">Медиафайлов не найдено</h3>
            </div>
        `;
        return;
    }
    
    results.forEach((result, index) => {
        const confidence = (result.score * 100).toFixed(1);
        const mediaPath = '/media/' + encodeURIComponent(result.path);
        
        // Определяем тип файла
        const fileExt = result.path.toLowerCase().split('.').pop();
        const videoExtensions = ['mp4', 'mov', 'avi', 'mkv'];
        const isVideo = videoExtensions.includes(fileExt);
        
        const div = document.createElement('div');
        div.innerHTML = `
            <div class="image-card shadow" onclick="showImagePreview('${mediaPath}', ${confidence}, '${result.path}')">
                <div class="confidence-badge">
                    <i class="fas fa-percentage me-1"></i>${confidence}%
                </div>
                ${isVideo ? `
                    <video class="preview-video" preload="metadata">
                        <source src="${mediaPath}" type="video/${fileExt}">
                    </video>
                    <div class="video-overlay">
                        <i class="fas fa-play-circle"></i>
                    </div>
                ` : `
                    <img src="${mediaPath}" alt="Результат ${index + 1}" loading="lazy">
                `}
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

// Функции для управления прогресс-баром
function showProgress(show = true) {
    const progressContainer = document.getElementById('progressContainer');
    progressContainer.style.display = show ? 'block' : 'none';
}

function updateProgress(percent, status) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressStatus = document.getElementById('progressStatus');
    const progressInfo = document.querySelector('.progress-info .progress-text:last-child');
    
    if (!progressBar || !progressText || !progressStatus) {
        return;
    }
    
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
    progressText.textContent = `${percent}%`;
    
    if (status) {
        progressStatus.textContent = status;
        // Обновляем информацию о загрузке
        if (progressInfo) {
            progressInfo.textContent = status;
        }
        // Обновляем информацию в поле поиска
        const searchInfo = document.querySelector('.search-info');
        if (searchInfo) {
            searchInfo.textContent = status;
        }
    }
}

// Функции для управления состоянием кнопок
function setButtonsState(action, isProcessing) {
    const indexButton = document.getElementById('indexButton');
    const stopIndexButton = document.getElementById('stopIndexButton');
    const syncButton = document.getElementById('syncButton');
    const stopSyncButton = document.getElementById('stopSyncButton');
    
    if (action === 'index') {
        indexButton.disabled = isProcessing;
        syncButton.disabled = isProcessing;
        stopIndexButton.classList.toggle('d-none', !isProcessing);
        indexButton.querySelector('i').classList.toggle('fa-spin', isProcessing);
    } else if (action === 'sync') {
        syncButton.disabled = isProcessing;
        indexButton.disabled = isProcessing;
        stopSyncButton.classList.toggle('d-none', !isProcessing);
        syncButton.querySelector('i').classList.toggle('fa-spin', isProcessing);
    }
}

// Обновляем функцию updateIndex
async function updateIndex() {
    try {
        setButtonsState('index', true);
        showProgress(true);
        updateProgress(0, 'Начало индексации...');
        
        const response = await fetch('/update_index', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const eventSource = new EventSource('/indexing_progress');
        
        eventSource.onmessage = async function(event) {
            const data = JSON.parse(event.data);
            updateProgress(data.progress, data.status);
            
            if (data.progress >= 100) {
                eventSource.close();
                setButtonsState('index', false);
                showProgress(false);
                
                // Если статус содержит сообщение о том, что новых файлов нет
                if (data.status && data.status.includes('Новых файлов для индексации не найдено')) {
                    showNotification('info', translations[userSettings.getLanguage()].allFilesIndexed);
                    return; // Прерываем выполнение, не перезапускаем сервер
                }
                
                // Если были проиндексированы новые файлы, перезапускаем сервер
                showNotification('success', 'Индексация завершена. Перезапуск сервера...');
                
                try {
                    // Перезапускаем сервер
                    await fetch('/restart_server', { method: 'POST' });
                    
                    // Ждем пока сервер перезапустится
                    setTimeout(async function checkServer() {
                        try {
                            const response = await fetch('/');
                            if (response.ok) {
                                // Сервер снова доступен, перезагружаем страницу
                                window.location.reload();
                            } else {
                                // Пробуем снова через секунду
                                setTimeout(checkServer, 1000);
                            }
                        } catch {
                            // Если сервер еще не доступен, пробуем снова
                            setTimeout(checkServer, 1000);
                        }
                    }, 2000); // Даем серверу 2 секунды на начальный перезапуск
                } catch (error) {
                    console.error('Ошибка при перезапуске сервера:', error);
                    showNotification('error', 'Ошибка при перезапуске сервера');
                }
            }
        };

        eventSource.onerror = function() {
            eventSource.close();
            showProgress(false);
            setButtonsState('index', false);
            showError('Ошибка при получении прогресса индексации');
        };

    } catch (error) {
        showProgress(false);
        setButtonsState('index', false);
        showError('Ошибка при обновлении индекса: ' + error.message);
    }
}

// Функция остановки индексации
async function stopIndexing() {
    try {
        const response = await fetch('/stop_indexing', {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('success', 'Индексация остановлена');
            setButtonsState('index', false);
            showProgress(false);
        } else {
            showNotification('error', data.error || 'Не удалось остановить индексацию');
        }
    } catch (error) {
        showNotification('error', 'Ошибка при остановке индексации');
    }
}

// Обновляем функцию для синхронизации с iCloud
document.getElementById('syncButton').addEventListener('click', async function() {
    try {
        setButtonsState('sync', true);
        showProgress(true);
        updateProgress(0, 'Начало синхронизации с iCloud...');
        
        const response = await fetch('/sync_icloud', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const eventSource = new EventSource('/sync_progress');
        
        eventSource.onmessage = async function(event) {
            const data = JSON.parse(event.data);
            updateProgress(data.progress, data.status);
            
            if (data.progress >= 100) {
                eventSource.close();
                showNotification('success', 'Синхронизация завершена. Перезапуск сервера...');
                
                try {
                    // Перезапускаем сервер
                    await fetch('/restart_server', { method: 'POST' });
                    
                    // Ждем пока сервер перезапустится
                    setTimeout(async function checkServer() {
                        try {
                            const response = await fetch('/');
                            if (response.ok) {
                                // Сервер снова доступен, перезагружаем страницу
                                window.location.reload();
                            } else {
                                // Пробуем снова через секунду
                                setTimeout(checkServer, 1000);
                            }
                        } catch {
                            // Если сервер еще не доступен, пробуем снова
                            setTimeout(checkServer, 1000);
                        }
                    }, 2000); // Даем серверу 2 секунды на начальный перезапуск
                } catch (error) {
                    console.error('Ошибка при перезапуске сервера:', error);
                    showNotification('error', 'Ошибка при перезапуске сервера');
                    showProgress(false);
                    setButtonsState('sync', false);
                }
            }
        };

        eventSource.onerror = function() {
            eventSource.close();
            showProgress(false);
            setButtonsState('sync', false);
            showError('Ошибка при получении прогресса синхронизации');
        };

    } catch (error) {
        showProgress(false);
        setButtonsState('sync', false);
        showError('Ошибка при синхронизации с iCloud: ' + error.message);
    }
});

// Обновляем функцию остановки синхронизации
async function stopSync() {
    try {
        const response = await fetch('/icloud/stop_sync', {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('success', 'Синхронизация остановлена');
            setButtonsState('sync', false);
            showProgress(false);
        } else {
            showNotification('error', data.error || 'Не удалось остановить синхронизацию');
        }
    } catch (error) {
        showNotification('error', 'Ошибка при остановке синхронизации');
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
        
        // Показываем прогресс-бар и меняем состояние кнопок
        setButtonsState('sync', true);
        showProgress(true);
        updateProgress(0, 'Начало синхронизации с iCloud...');
        
        // Запускаем отслеживание прогресса синхронизации
        const eventSource = new EventSource('/sync_progress');
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateProgress(data.progress, data.status);
            
            if (data.progress >= 100) {
                eventSource.close();
                showNotification('success', 'Синхронизация завершена. Перезапуск сервера...');
                
                // Перезапускаем сервер после завершения
                fetch('/restart_server', { method: 'POST' })
                    .then(() => {
                        setTimeout(function checkServer() {
                            fetch('/')
                                .then(response => {
                                    if (response.ok) {
                                        window.location.reload();
                                    } else {
                                        setTimeout(checkServer, 1000);
                                    }
                                })
                                .catch(() => setTimeout(checkServer, 1000));
                        }, 2000);
                    });
            }
        };
        
        eventSource.onerror = function() {
            eventSource.close();
            showProgress(false);
            setButtonsState('sync', false);
            showError('Ошибка при получении прогресса синхронизации');
        };

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

// Функция для переключения темы
function toggleTheme() {
    const root = document.documentElement;
    const currentTheme = root.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', newTheme);
    
    // Сохраняем выбранную тему в localStorage
    localStorage.setItem('theme', newTheme);
    
    // Обновляем иконку
    const themeIcon = document.querySelector('#themeToggle i');
    themeIcon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

// Функция для загрузки сохраненной темы
function loadSavedTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    const root = document.documentElement;
    root.setAttribute('data-theme', savedTheme);
    
    // Обновляем иконку
    const themeIcon = document.querySelector('#themeToggle i');
    if (themeIcon) {
        themeIcon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Функция для переключения языка
function toggleLanguage() {
    const langButton = document.querySelector('#languageToggle span');
    const currentLang = localStorage.getItem('language') || 'en';
    const newLang = currentLang === 'en' ? 'ru' : 'en';
    
    // Сохраняем выбранный язык
    localStorage.setItem('language', newLang);
    
    // Обновляем текст кнопки
    if (langButton) {
        langButton.textContent = newLang.toUpperCase();
    }
    
    // Обновляем все тексты на странице
    updateTexts();
}

// Функция для загрузки сохраненного языка
function loadSavedLanguage() {
    const savedLang = localStorage.getItem('language') || 'en';
    const langButton = document.querySelector('#languageToggle span');
    
    if (langButton) {
        langButton.textContent = savedLang.toUpperCase();
    }
    
    // Обновляем все тексты на странице
    updateTexts();
}

// Обновляем функцию updateTexts для поддержки обоих языков
function updateTexts() {
    const currentLang = localStorage.getItem('language') || 'en';
    const translations = {
        en: {
            title: 'Image Search',
            updateIndex: 'Update Index',
            syncWithICloud: 'Sync with iCloud',
            search: 'Search',
            searchPlaceholder: 'Enter your search query in English...',
            totalFiles: 'Total Files',
            totalImages: 'Total Images',
            totalVideos: 'Total Videos',
            lastUpdate: 'Last Update',
            syncStatus: 'Sync Status',
            stopIndexing: 'Stop Indexing',
            stopSync: 'Stop Sync'
        },
        ru: {
            title: 'Поиск изображений',
            updateIndex: 'Обновить индекс',
            syncWithICloud: 'Синхронизация с iCloud',
            search: 'Поиск',
            searchPlaceholder: 'Введите поисковый запрос на английском...',
            totalFiles: 'Всего файлов',
            totalImages: 'Всего изображений',
            totalVideos: 'Всего видео',
            lastUpdate: 'Последнее обновление',
            syncStatus: 'Статус синхронизации',
            stopIndexing: 'Остановить индексацию',
            stopSync: 'Остановить синхронизацию'
        }
    };

    // Обновляем все элементы с атрибутом data-translate
    document.querySelectorAll('[data-translate]').forEach(element => {
        const key = element.getAttribute('data-translate');
        if (translations[currentLang][key]) {
            if (element.tagName === 'INPUT') {
                element.placeholder = translations[currentLang][key];
            } else {
                element.textContent = translations[currentLang][key];
            }
        }
    });
}

// Функция для проверки текущего статуса операций
async function checkOperationsStatus() {
    try {
        // Проверяем статус индексации
        const indexingResponse = await fetch('/indexing_status');
        const indexingData = await indexingResponse.json();
        
        if (indexingData.status === "running") {
            setButtonsState('index', true);
            showProgress(true);
            
            // Запускаем отслеживание прогресса индексации
            const eventSource = new EventSource('/indexing_progress');
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateProgress(data.progress, data.status);
                
                if (data.progress >= 100) {
                    eventSource.close();
                    setButtonsState('index', false);
                    showProgress(false);
                }
            };
        }
        
        // Проверяем статус синхронизации
        const syncResponse = await fetch('/icloud/sync_status');
        const syncData = await syncResponse.json();
        
        if (syncData.status === "syncing") {
            setButtonsState('sync', true);
            showProgress(true);
            
            // Запускаем отслеживание прогресса синхронизации
            const eventSource = new EventSource('/sync_progress');
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateProgress(data.progress, data.status);
                
                if (data.progress >= 100) {
                    eventSource.close();
                    setButtonsState('sync', false);
                    showProgress(false);
                }
            };
        }
    } catch (error) {
        console.error('Ошибка при проверке статуса операций:', error);
    }
}

// Добавляем функцию для обновления статистики
async function updateStatistics() {
    try {
        const response = await fetch('/stats');
        const data = await response.json();
        const texts = translations[userSettings.getLanguage()];
        
        document.getElementById('totalFiles').textContent = data.total_files;
        document.getElementById('totalImages').textContent = data.total_images;
        document.getElementById('totalVideos').textContent = data.total_videos;
        document.getElementById('lastUpdate').textContent = data.last_update;
        document.getElementById('syncStatus').textContent = data.sync_status;
        
        // Обновляем время последнего обновления
        const lastUpdateElement = document.getElementById('lastUpdate');
        if (lastUpdateElement) {
            const lastUpdate = data.last_update || texts.never;
            lastUpdateElement.textContent = lastUpdate;
            
            // Добавляем тултип с точным временем, если есть
            if (lastUpdate !== texts.never && lastUpdate !== "только что") {
                lastUpdateElement.title = `Обновлено ${lastUpdate}`;
            }
        }
    } catch (error) {
        console.error('Ошибка при обновлении статистики:', error);
    }
}

// Обновляем функцию проверки индекса
async function checkIndex() {
    try {
        const response = await fetch('/check_index');
        const data = await response.json();
        
        if (!data.exists) {
            const infoPanel = document.getElementById('infoPanel');
            const infoPanelText = document.getElementById('infoPanelText');
            const texts = translations[userSettings.getLanguage()];
            
            if (infoPanel && infoPanelText) {
                infoPanelText.textContent = texts.noIndex;
                infoPanel.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error checking index:', error);
    }
}

function startIndexing() {
    const indexButton = document.getElementById('indexButton');
    const progressIndicator = document.getElementById('progressIndicator');
    
    console.log('Начало индексации');
    indexButton.disabled = true;
    progressIndicator.style.display = 'block';
    
    fetch('/update_index', {
        method: 'POST'
    }).then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Ошибка при запуске индексации:', data.error);
            showNotification('error', 'Ошибка при запуске индексации');
            indexButton.disabled = false;
            progressIndicator.style.display = 'none';
            return;
        }
        
        console.log('Индексация запущена успешно, подключаемся к потоку событий');
        const eventSource = new EventSource('/indexing_progress');
        
        eventSource.onmessage = function(e) {
            const data = JSON.parse(e.data);
            console.log('Получено событие индексации:', data);
            updateProgress(data.progress, data.status);
            
            // Проверяем статус индексации
            if (data.state === "no_new_files") {
                console.log('Нет новых файлов для индексации');
                showNotification('info', translations[userSettings.getLanguage()].allFilesIndexed);
                eventSource.close();
                indexButton.disabled = false;
                progressIndicator.style.display = 'none';
                return;
            }
            
            if (data.state === "error") {
                console.error('Ошибка при индексации:', data.status);
                showNotification('error', data.status);
                eventSource.close();
                indexButton.disabled = false;
                progressIndicator.style.display = 'none';
                return;
            }
            
            if (data.progress >= 100 || data.state === "completed") {
                console.log('Индексация завершена, статус:', data.state);
                eventSource.close();
                indexButton.disabled = false;
                progressIndicator.style.display = 'none';
                
                // Перезапускаем сервер только если были проиндексированы новые файлы
                if (data.state === "completed") {
                    console.log('Перезапуск сервера после успешной индексации');
                    showNotification('success', 'Индексация завершена. Перезапуск сервера...');
                    fetch('/restart_server', { method: 'POST' })
                        .then(() => {
                            setTimeout(function checkServer() {
                                fetch('/')
                                    .then(response => {
                                        if (response.ok) {
                                            console.log('Сервер перезапущен успешно, перезагружаем страницу');
                                            window.location.reload();
                                        } else {
                                            console.log('Сервер ещё не готов, ждём...');
                                            setTimeout(checkServer, 1000);
                                        }
                                    })
                                    .catch(() => {
                                        console.log('Ошибка подключения к серверу, пробуем снова...');
                                        setTimeout(checkServer, 1000);
                                    });
                            }, 2000);
                        });
                }
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('Ошибка в потоке событий индексации:', error);
            eventSource.close();
            showNotification('error', 'Ошибка при получении статуса индексации');
            indexButton.disabled = false;
            progressIndicator.style.display = 'none';
        };
    })
    .catch(error => {
        console.error('Ошибка при запуске индексации:', error);
        showNotification('error', 'Ошибка при запуске индексации');
        indexButton.disabled = false;
        progressIndicator.style.display = 'none';
    });
}

// Функция для загрузки сохраненных учетных данных
async function loadSavedCredentials() {
    try {
        const response = await fetch('/icloud/load_credentials');
        const data = await response.json();
        if (data.success && data.credentials) {
            document.getElementById('username').value = data.credentials.username;
            // Устанавливаем чекбокс "Запомнить"
            document.getElementById('remember-credentials').checked = true;
        }
    } catch (error) {
        console.error('Ошибка при загрузке учетных данных:', error);
    }
}

// Функция для удаления сохраненных учетных данных
async function deleteSavedCredentials() {
    try {
        const response = await fetch('/icloud/delete_credentials', {
            method: 'POST'
        });
        const data = await response.json();
        if (data.success) {
            // Очищаем поля
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
            document.getElementById('remember-credentials').checked = false;
        }
    } catch (error) {
        console.error('Ошибка при удалении учетных данных:', error);
    }
}

// Функция для подключения к iCloud
async function connectToiCloud() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const remember = document.getElementById('remember-credentials').checked;

    if (!username || !password) {
        showError('Пожалуйста, введите логин и пароль');
        return;
    }

    showLoading('Подключение к iCloud...');

    try {
        const response = await fetch('/icloud/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                remember
            })
        });

        const data = await response.json();

        if (data.success) {
            if (data.message && data.message.startsWith('2fa')) {
                // Показываем форму двухфакторной аутентификации
                showTwoFactorAuth();
            } else {
                // Успешное подключение
                hideLoginForm();
                startSync();
            }
        } else {
            showError(data.error || 'Ошибка подключения');
        }
    } catch (error) {
        showError('Ошибка подключения к серверу');
        console.error(error);
    } finally {
        hideLoading();
    }
} 