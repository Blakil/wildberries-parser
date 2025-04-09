# Парсер позиций товаров Wildberries

Телеграм-бот для определения позиций товара Wildberries в поисковой выдаче на основе ключевых запросов, выделенных из описания товара с помощью LLM.

## Технические особенности

- 🔍 Извлечение ключевых запросов из данных о товаре с помощью LLM (поддержка DeepSeek и OpenRouter)
- 🔢 Анализ позиций в поисковой выдаче с настраиваемым лимитом страниц
- 🖼️ Отображение информации о товаре с изображением
- 🌐 Интеграция HTTP прокси с аутентификацией
- 🔄 Сессионная ротация прокси и управление таймаутами

## Настройка окружения

```bash
# Создание виртуального окружения
python -m venv venv

# Активация виртуального окружения
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env, указав свои учетные данные
```

## Конфигурация

### Основные настройки

```
# Телеграм-бот
BOT_TOKEN=ваш_токен_телеграм_бота

# Настройки LLM
LLM_PROVIDER=deepseek  # или openrouter
DEEPSEEK_API_KEY=ваш_ключ_deepseek_api
DEEPSEEK_MODEL=deepseek-chat
OPENROUTER_API_KEY=ваш_ключ_openrouter_api
OPENROUTER_MODEL=deepseek/deepseek-v3-base:free

# Настройки Wildberries
WB_REGION=ru
WB_USE_PROXY=False  # Установите True для включения прокси для запросов к WB
SEARCH_KEYWORDS_COUNT=5
MAX_SEARCH_PAGES=5
MAX_POSITION_LIMIT=500
```

### Настройки прокси

```
# Основные настройки прокси
PROXY_ENABLED=False  # Главный переключатель функциональности прокси
PROXY_TIMEOUT_MINUTES=2  # Интервал ротации

# Учетные данные PIA Proxy
PIA_BASE_HOST=your_host.proxy.piaproxy.co
PIA_PORT=5000
PIA_USERNAME=your_username
PIA_PASSWORD=your_password
```

## Использование

Запустить с активированным виртуальным окружением:

```bash
python main.py
```

Отправьте боту в Telegram ссылки на товары Wildberries для анализа позиций в поиске.
