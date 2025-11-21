# Yandex Entrance Parser

Парсер для получения координат и азимутов подъездов из Яндекс.Карт по адресу или FIAS ID.

## Features

- Извлекает координаты подъездов из Yandex Maps
- Получает азимуты (направления) для каждого подъезда
- Поддержка поиска по текстовому адресу или FIAS ID
- Автоматическое сопоставление подъездов по координатам
- Точность координат <1 метра

## Quick Start

`python3 yandex_entrances.py`

Скрипт обрабатывает `test_data.csv` и создает `yandex_results.csv` с актуальными данными из Яндекс.Карт.

## Output Format

CSV с полями: `fias_id`, `address`, `porch`, `lat`, `lon`, `azimuth`, `source`, `error`

## Requirements

- Python 3.7+
- requests