class UserSettings {
    constructor() {
        this.settings = this.loadSettings();
    }

    loadSettings() {
        const defaultSettings = {
            theme: 'light',
            language: 'en',
            lastSearch: '',
            searchHistory: []
        };

        const savedSettings = localStorage.getItem('userSettings');
        return savedSettings ? { ...defaultSettings, ...JSON.parse(savedSettings) } : defaultSettings;
    }

    saveSettings() {
        localStorage.setItem('userSettings', JSON.stringify(this.settings));
    }

    getTheme() {
        return this.settings.theme;
    }

    setTheme(theme) {
        this.settings.theme = theme;
        this.saveSettings();
    }

    getLanguage() {
        return this.settings.language;
    }

    setLanguage(language) {
        this.settings.language = language;
        this.saveSettings();
    }

    addToSearchHistory(query) {
        this.settings.lastSearch = query;
        if (!this.settings.searchHistory.includes(query)) {
            this.settings.searchHistory.unshift(query);
            this.settings.searchHistory = this.settings.searchHistory.slice(0, 10); // Keep last 10 searches
        }
        this.saveSettings();
    }

    getSearchHistory() {
        return this.settings.searchHistory;
    }

    getLastSearch() {
        return this.settings.lastSearch;
    }
}

// Translations
const translations = {
    en: {
        title: 'Image Search',
        search: 'Search',
        searchPlaceholder: 'Enter your search query in English...',
        updateIndex: 'Update Index',
        totalImages: 'Total Images',
        lastUpdate: 'Last Update',
        syncStatus: 'Sync Status',
        syncWithICloud: 'Sync with iCloud Photos',
        stopSync: 'Stop Sync',
        about: 'About',
        aboutText: 'This project uses CLIP technology for semantic image search. You can search for photos by describing their content in natural language.',
        features: 'Features',
        heicSupport: 'HEIC format support',
        icloudSync: 'iCloud synchronization',
        semanticSearch: 'Semantic search',
        autoIndex: 'Automatic indexing',
        howToUse: 'How to Use',
        howToUseText: 'To search for images, simply enter a description of what you want to find. For example:',
        example1: 'sunset on the beach',
        example2: 'person in a red jacket',
        example3: 'mountain landscape',
        searchTip: 'The more specific the description, the better the search results will be.',
        noIndex: 'Images are not indexed yet. Index needs to be created for search.',
        indexNow: 'Index Now',
        loading: 'Loading...',
        error: 'Error',
        success: 'Success',
        preview: 'Preview',
        close: 'Close',
        path: 'Path',
        confidence: 'Confidence',
        language: 'Language',
        theme: 'Theme',
        never: 'Never',
        notSynced: 'Not synced'
    },
    ru: {
        title: 'Поиск по фотографиям',
        search: 'Найти',
        searchPlaceholder: 'Введите поисковый запрос на английском...',
        updateIndex: 'Обновить индекс',
        totalImages: 'Всего изображений',
        lastUpdate: 'Последнее обновление',
        syncStatus: 'Статус синхронизации',
        syncWithICloud: 'Синхронизировать с iCloud Photos',
        stopSync: 'Остановить синхронизацию',
        about: 'О проекте',
        aboutText: 'Этот проект использует технологию CLIP для семантического поиска изображений. Вы можете искать фотографии, описывая их содержимое на естественном языке.',
        features: 'Возможности',
        heicSupport: 'Поддержка HEIC формата',
        icloudSync: 'Синхронизация с iCloud',
        semanticSearch: 'Семантический поиск',
        autoIndex: 'Автоматическая индексация',
        howToUse: 'Как использовать',
        howToUseText: 'Для поиска изображений просто введите описание того, что хотите найти (на английском языке). Например:',
        example1: 'sunset on the beach',
        example2: 'person in a red jacket',
        example3: 'mountain landscape',
        searchTip: 'Чем точнее описание, тем лучше будут результаты поиска.',
        noIndex: 'Изображения ещё не проиндексированы. Необходимо создать индекс для поиска.',
        indexNow: 'Индексировать сейчас',
        loading: 'Загрузка...',
        error: 'Ошибка',
        success: 'Успешно',
        preview: 'Предпросмотр',
        close: 'Закрыть',
        path: 'Путь',
        confidence: 'Уверенность',
        language: 'Язык',
        theme: 'Тема',
        never: 'Никогда',
        notSynced: 'Не синхронизировано'
    }
};

const userSettings = new UserSettings();

// Export for use in other files
window.userSettings = userSettings;
window.translations = translations; 