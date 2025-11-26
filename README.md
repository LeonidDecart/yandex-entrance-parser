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

### Подготовка списка адресов

Создайте файл `addresses.txt` с адресами, каждый на новой строке. 

**Важно:** Указывайте полные адреса (как в примере ниже). Это необходимо для корректного поиска домов на Яндекс.Картах и получения данных о подъездах.

```
Челябинск, ул. Татьяничевой, д. 9 А
Челябинск, ул. Сони Кривой, д. 49 А
Челябинск, ул. Солнечная, д. 56
```

### Запуск скрипта

```bash
python3 yandex_entrances.py
```

Скрипт сохраняет результаты в папку `results/` по ходу обработки:
- `YYYY-MM-DD_HH-MM-SS_results.csv` — данные подъездов (координаты, азимуты)
- `YYYY-MM-DD_HH-MM-SS_failures.json` — адреса с ошибками

## Output Format

CSV с полями: `address`, `porch`, `lat`, `lon`, `azimuth`, `entrances_raw_json`

## Requirements

- Python 3.7+
- requests