#!/usr/bin/env python3
"""
Модуль трансформации (Transform) ETL-пайплайна.
Очистка, нормализация, агрегация, обогащение данных.
"""

import pandas as pd
import numpy as np

def clean_consumption(df):
    """
    Очистка данных о потреблении: удаление дубликатов, обработка пропусков.
    """
    df = df.copy()
    
    # Удаление дубликатов
    df = df.drop_duplicates(subset=['household_id', 'timestamp'])
    
    # Проверка пропусков
    numeric_cols = ['energy_kwh', 'water_liters', 'gas_kwh']
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())
    
    # Удаление выбросов (значения > 3 сигма)
    for col in numeric_cols:
        mean = df[col].mean()
        std = df[col].std()
        df = df[(df[col] >= mean - 3*std) & (df[col] <= mean + 3*std)]
    
    return df

def aggregate_daily(df):
    """
    Агрегация почасовых данных в дневные.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    
    daily = df.groupby(['household_id', 'date']).agg({
        'energy_kwh': 'sum',
        'water_liters': 'sum',
        'gas_kwh': 'sum'
    }).reset_index()
    
    return daily

def enrich_with_weather(consumption_df, weather_df):
    """
    Обогащение данных потребления погодными условиями.
    """
    consumption_df = consumption_df.copy()
    weather_df = weather_df.copy()
    
    # Приведение временных меток к часу
    consumption_df['hour'] = pd.to_datetime(consumption_df['timestamp']).dt.floor('H')
    weather_df['hour'] = pd.to_datetime(weather_df['timestamp']).dt.floor('H')
    
    # Merge
    enriched = pd.merge(
        consumption_df,
        weather_df[['hour', 'temperature_c', 'humidity_pct', 'wind_speed', 'precipitation_mm']],
        on='hour',
        how='left'
    )
    
    # Заполнение пропусков в погодных данных
    for col in ['temperature_c', 'humidity_pct']:
        enriched[col] = enriched[col].fillna(enriched[col].median())
    
    return enriched.drop('hour', axis=1)

def calculate_features(df):
    """
    Расчёт дополнительных признаков для анализа.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['month'] = pd.to_datetime(df['timestamp']).dt.month
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    
    # Признак "час пик"
    df['is_peak_hour'] = ((df['hour'] >= 18) & (df['hour'] <= 21)).astype(int)
    
    return df

def transform_all(extracted_data):
    """
    Запуск всех трансформаций.
    """
    print("[TRANSFORM] Начало трансформации данных...")
    
    consumption_df = extracted_data['consumption']
    weather_df = extracted_data['weather']
    
    # Очистка
    consumption_clean = clean_consumption(consumption_df)
    print(f"  - После очистки: {len(consumption_clean)} записей")
    
    # Обогащение погодой
    enriched = enrich_with_weather(consumption_clean, weather_df)
    print(f"  - После обогащения: {len(enriched)} записей")
    
    # Расчёт признаков
    final = calculate_features(enriched)
    print(f"  - Добавлено {len(final.columns)} признаков")
    
    # Дневная агрегация для аналитики
    daily_agg = aggregate_daily(consumption_clean)
    
    return {
        'raw_consumption': consumption_df,
        'weather': weather_df,
        'enriched_consumption': final,
        'daily_aggregates': daily_agg
    }

if __name__ == "__main__":
    from extract import extract_all
    extracted = extract_all()
    transformed = transform_all(extracted)
    print(transformed['enriched_consumption'].head())