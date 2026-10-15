# Z.ai Usage Telegram Bot 🤖

Приватный Telegram-бот на Python (Aiogram 3) для мониторинга квот, кредитов и подписок в сервисе Z.ai (GLM Coding Plan) с поддержкой гибких алертов и фоновых уведомлений.

---

## 🚀 Возможности

- **Мониторинг лимитов Z.ai в реальном времени**:
  - Квоты 5-часовых и недельных кредитов (GLM Coding Plan / Credits).
  - Токены предыдущих форматов (Tokens).
  - Лимиты вызовов инструментов MCP Tools (Web Search, Web Reader, Zread).
  - Отображение статуса подписки, даты истечения и признака автопродления.
- **Интерактивные алерты и уведомления**:
  - Пороговые алерты (>50%, >80% или любой произвольный % от 1 до 99%).
  - Быстрый расход (Burn Rate): оповещение, если израсходовано >50% лимита за первую половину периода.
  - Антиспам-дедупликация: отправляет алерт ровно 1 раз за период сброса квоты (`nextResetTime`) и автоматически взводится снова при сбросе.
- **Безопасность**:
  - Встроенный `AuthMiddleware`: доступ разрешен исключительно владельцу (`OWNER_ID`).
- **Модульная архитектура**:
  - Чистое разделение на слои (`app.config`, `app.database`, `app.zai_client`, `app.formatters`, `app.keyboards`, `app.handlers`, `app.services.alerts`).
  - Полный набор тестов (unit, functional, integration) с покрытием **99%**.

---

## 📂 Структура проекта

```
.
├── app/
│   ├── config.py           # Конфигурация и переменные окружения
│   ├── database.py         # SQLite CRUD операции (аккаунты, алерты)
│   ├── zai_client.py       # Клиент к API Z.ai (квоты, подписки)
│   ├── formatters.py       # Форматирование времени (МСК) и сообщений
│   ├── keyboards.py        # Фабрики Inline-клавиатур
│   ├── middlewares.py      # AuthMiddleware (проверка OWNER_ID)
│   ├── states.py           # FSM-состояния (добавление аккаунта, свой %)
│   ├── handlers/           # Маршрутизаторы Aiogram 3
│   │   ├── common.py       # /start, /cancel, о проекте
│   │   ├── accounts.py     # Добавление, просмотр, удаление аккаунтов
│   │   └── alerts.py       # Меню алертов, пресеты, удаление
│   ├── services/
│   │   └── alerts.py       # Логика проверки алертов и фоновый воркер
│   └── main.py             # Точка входа приложения
├── tests/
│   ├── conftest.py         # Фикстуры pytest (SQLite, mock bot, FSM)
│   ├── unit/               # Модульные тесты
│   ├── functional/         # Функциональные тесты хендлеров и middleware
│   └── integration/        # Интеграционные тесты воркера и цикла бота
├── bot.py                  # Обратно-совместимый фасадный модуль
├── Dockerfile              # Docker-образ
├── docker-compose.yml      # Запуск сервиса
├── requirements.txt        # Продакшн-зависимости
└── requirements-dev.txt    # Зависимости для разработки и тестов
```

---

## 🛠 Установка и запуск

### 1. Переменные окружения (.env)

Создайте `.env` файл на основе `.env.example`:

```env
BOT_TOKEN=123456789:AAH...
OWNER_ID=123456789
```

### 2. Запуск через Docker Compose

```bash
docker-compose up -d --build
```

### 3. Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

---

## 🧪 Запуск тестов и покрытие

Установите dev-зависимости:

```bash
pip install -r requirements-dev.txt
```

Запустите тесты с генерацией отчета о покрытии:

```bash
pytest --cov=app --cov-report=term-missing
```

Текущее покрытие: **99%**.
