# Лабораторная работа №4 — Инженерия данных для систем искусственного интеллекта
## Кейс 5: Прогнозирование потребления ресурсов в жилых кварталах

### Автор
Илья Пикалов

### Описание проекта
Сквозной пайплайн для сбора, обработки и загрузки данных о потреблении электроэнергии, воды и тепла в жилых кварталах. Реализованы:
- Сбор из CSV-файлов (открытые датасеты) и API погоды (OpenWeatherMap)
- Хранение в PostgreSQL, MongoDB и векторной БД (FAISS)
- ETL-пайплайн в Apache Airflow
- Контроль качества с Great Expectations
- Мониторинг дрейфа данных с Evidently AI

### Структура проекта
```

LR4_Case5/
├── airflow/
│   ├── dags/
│   │   └── energy_consumption_etl.py
│   └── requirements.txt
├── data/
│   ├── raw/
│   │   └── london_households.csv    # Синтетические данные о потреблении
│   └── processed/
├── scripts/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   ├── quality_checks.py
│   └── drift_monitoring.py
├── notebooks/
│   └── 01_eda.ipynb
├── tests/
│   └── test_etl.py
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md

```

### Требования
- Python 3.9+
- Docker и Docker Compose
- 8+ GB RAM

### Быстрый запуск

#### 1. Клонирование и установка
```bash
git clone <your-repo-url>
cd LR4_Case5
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Запуск инфраструктуры (PostgreSQL, MongoDB, Airflow)

```
docker-compose up -d
```

#### 3. Инициализация Airflow

```
airflow db init
airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com
```

#### 4. Запуск ETL-пайплайна

```
airflow dags trigger energy_consumption_etl
```

#### 5. Запуск проверок качества и дрейфа

```
python scripts/quality_checks.py
python scripts/drift_monitoring.py
```

### Компоненты

#### Модуль 1: Сбор данных

- **Источники**: Синтетический датасет потребления (London Households style) + OpenWeatherMap API
- **Формат**: CSV + JSON через API
- **Сохранение**: `data/raw/`

#### Модуль 2: Хранилища

- **PostgreSQL**: Таблицы `buildings`, `consumption`, `weather`
- **MongoDB**: Сырые записи со счётчиков
- **FAISS**: Векторный поиск аномальных профилей потребления

#### Модуль 3: ETL в Airflow

- **DAG**: `energy_consumption_etl`
- **Задачи**: extract → transform → load_postgres → load_mongodb → build_vectors
- **Расписание**: Ежедневно в 08:00

#### Модуль 4: Качество данных

- **Great Expectations**: Ожидания на наличие пропусков, диапазоны значений, типы
- **Evidently AI**: Дрейф распределений потребления по дням

### Переменные окружения (.env)

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=energy
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=energy

OPENWEATHER_API_KEY=your_key_here

AIRFLOW_UID=50000
```

### Результаты

- Ежедневное обновление данных о потреблении
- 10 000+ записей в PostgreSQL
- Мониторинг дрейфа с автоматическими отчётами
- Векторный индекс для поиска аномалий

### Лицензия

MIT