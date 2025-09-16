## MappingData

Лёгкое веб‑приложение на FastAPI для извлечения и визуализации данных из Excel/PDF (таможенные декларации и инвойсы). Загружаете файл, выбираете отправителя — получаете структурированную таблицу и расчёты.

### Демо
Открыть: `https://data-mapping-tool-15n5.onrender.com`

### Возможности
- **Загрузка** Excel/PDF через веб‑интерфейс.
- **Обработка** данными алгоритмами для конкретных отправителей.
- **Просмотр** результатов в виде таблицы + агрегаты/итоги.
- **Расширяемость**: легко добавить нового отправителя и алгоритм сравнения.

### Стек
- **Backend**: FastAPI, Uvicorn
- **Шаблоны**: Jinja2 (`templates/`)
- **Docker**: запуск в режиме разработки через `docker-compose.yml`
- **Деплой**: Render (`render.yaml`)

### Структура проекта
```
mappingdata/
├── main.py                 # Точка входа (uvicorn main:app)
├── docker-compose.yml      # Docker dev‑запуск
├── requirements.txt        # Зависимости Python
├── render.yaml             # Конфигурация деплоя на Render
├── src/
│   ├── api.py              # FastAPI маршруты и HTML‑страницы
│   ├── models.py           # Pydantic‑модели запросов/данных
│   ├── services.py         # Логика обработки и сохранения данных
│   ├── gemini_api.py       # Интеграция с Gemini (если используется)
│   ├── processors/         # Алгоритмы парсинга по отправителям
│   │   ├── __init__.py     # Регистрация PROCESSORS
│   │   ├── xinjiang.py
│   │   ├── mtl.py
│   │   └── changan.py
│   └── compare/            # Логика сравнения инвойс/декларация
│       ├── __init__.py     # Доступ к COMPARE_HANDLERS
│       └── test_handler.py # Реестр COMPARE_HANDLERS
├── templates/              # HTML‑шаблоны (upload/table/compare)
└── static/                 # Статические файлы
```

### Установка и запуск

Вариант A — Docker (рекомендуется, один старт‑командой):
```bash
docker-compose up --build
```
Приложение будет доступно на `http://127.0.0.1:8000`.

Вариант B — Локально (без Docker):
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```
Откройте `http://127.0.0.1:8000`.

### Как пользоваться
1. Откройте главную страницу (`/`).
2. Выберите отправителя из списка (список формируется из `PROCESSORS` в `src/processors/__init__.py`).
3. Загрузите файл (Excel/PDF) и дождитесь обработки.
4. Перейдите на страницу таблицы (`/table`) для просмотра данных и итогов.
5. Для сравнения инвойса и декларации используйте `/compare`.

### Как добавить нового отправителя (парсер)
1. Создайте модуль в `src/processors/`, реализуйте функцию обработки: `bytes -> dict`.
2. Зарегистрируйте её в `src/processors/__init__.py` в словаре `PROCESSORS`.
3. Имя ключа в `PROCESSORS` появится в UI автоматически.

### Как добавить обработчик сравнения
1. Добавьте функцию в `src/compare/test_handler.py` и зарегистрируйте её в `COMPARE_HANDLERS`.
2. Хэндлер станет доступен на странице `/compare` (список формируется из `COMPARE_HANDLERS`).

### Деплой на Render
- Репозиторий собирается Docker‑ом автоматически. Конфигурация — `render.yaml`.
- Переменные окружения и команду запуска можно указать в панели Render, команда по умолчанию: `uvicorn main:app --host 0.0.0.0 --port 8000`.

### Лицензия
MIT