import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from extract import extract_from_csv
from transform import clean_consumption, enrich_with_weather
from load import init_postgres

def test_extract():
    df = extract_from_csv(file_path="data/raw/london_households.csv")
    assert len(df) > 0
    assert 'household_id' in df.columns
    assert 'energy_kwh' in df.columns

def test_clean_consumption():
    df = pd.DataFrame({
        'household_id': [1, 1, 2],
        'timestamp': ['2025-01-01', '2025-01-01', '2025-01-01'],
        'energy_kwh': [10, 10, None],
        'water_liters': [100, 100, 200],
        'gas_kwh': [5, 5, 6]
    })
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    cleaned = clean_consumption(df)
    assert len(cleaned) == 2  # дубликат удалён, пропуск заполнен
    assert cleaned['energy_kwh'].isna().sum() == 0

def test_postgres_connection():
    try:
        engine = init_postgres()
        assert engine is not None
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")