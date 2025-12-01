# Yandex Entrance Parser

Парсер для получения координат и азимутов подъездов из Яндекс.Карт по адресам.

## Features

- Извлекает координаты подъездов из Yandex Maps
- Получает азимуты для каждого подъезда
- Фильтрация дубликатов подъездов
- Случайные User-Agent заголовки
- Ротация прокси-серверов при обнаружении CAPTCHA или ошибок (настраивается в `config.py`)
- Автоматическая ротация прокси и User-Agent при CAPTCHA и сообщениях об устаревшем браузере

## Установка и запуск

### Linux-сервер (Ubuntu/Debian)

```bash
# 1. Клонируйте репозиторий
cd ~
git clone https://github.com/LeonidDecart/yandex-entrance-parser.git
cd yandex-entrance-parser

# 2. Установите системные зависимости
sudo apt-get update
sudo apt-get install -y git python3-venv python3-pip

# 3. Создайте виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 4. Установите Python-зависимости
pip install --upgrade pip
pip install requests
```

**Важно:**
- Убедитесь, что версия Python >= 3.7: `python3 --version`

### Настройка конфигурации

Настройте прокси в `config.py` (или оставьте `[None]` для работы без прокси):

```python
PROXIES = [
    None,
    {"host": "proxy.example.com", "port": 8080, "user": "username", "pass": "password"},
]
```

### Подготовка данных

Создайте файл `data.csv`. Первые два столбца обязательно должны иметь названия: `fias_id`, `address`. Остальные столбцы игнорируются. Адреса могут повторяться — скрипт обрабатывает уникальные адреса и записывает результат для всех соответствующих fias_id.

```csv
fias_id,address
379cb922-0149-4a63-abc9-c28faf25eeba,"Челябинск, пр-кт. Комсомольский, д. 41 Б"
eb981c9a-ea31-4209-8b08-249570c77c3a,"Челябинск, ул. 40-летия Победы, д. 33 Б"
```

### Запуск скрипта

```bash
python3 yandex_entrances.py
```

Скрипт обрабатывает `data.csv` и сохраняет результаты в `results/`:
- `YYYY-MM-DD_HH-MM-SS_results.csv` — данные подъездов
- `YYYY-MM-DD_HH-MM-SS_failures.json` — адреса с ошибками

## Output Format

CSV с полями: `fias_id`, `address`, `porch`, `lat`, `lon`, `azimuth`

Для домов без подъездов сохраняется одна запись с `porch=0` и координатами дома.

## Requirements

- Python 3.7+
- requests