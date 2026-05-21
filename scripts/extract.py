#!/usr/bin/env python3
"""
Модуль извлечения (Extract) ETL-пайплайна.
Источники: CSV файл (синтетические данные потребления) + API погоды.
"""

import pandas as pd
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def extract_from_csv(file_path="data/raw/london_households.csv", date=None):
    """
    Извлечение данных потребления из CSV.
    Если указана дата, фильтруем по ней (для инкрементальной загрузки).
    """
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    if date:
        start = datetime.combine(date, datetime.min.time())
        end = start + timedelta(days=1)
        df = df[(df['timestamp'] >= start) & (df['timestamp'] < end)]
    
    return df

def extract_from_weather_api(city="London", api_key=None, date=None):
    """
    Извлечение погодных данных из OpenWeatherMap API.
    """
    if api_key is None:
        api_key = os.getenv("OPENWEATHER_API_KEY")
    
    if not api_key:
        print("API ключ не найден. Использую синтетические погодные данные.")
        # Синтетические данные для демонстрации
        df = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(hours=i) for i in range(24)],
            'temperature_c': [5 + i * 0.5 for i in range(24)],
            'humidity_pct': [75 + i * 0.2 for i in range(24)],
            'wind_speed': [3 + i * 0.1 for i in range(24)],
            'precipitation_mm': [0] * 24
        })
        return df
    
    # Реальный API-запрос
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        records = []
        for item in data['list']:
            records.append({
                'timestamp': datetime.fromtimestamp(item['dt']),
                'temperature_c': item['main']['temp'],
                'humidity_pct': item['main']['humidity'],
                'wind_speed': item['wind']['speed'],
                'precipitation_mm': item.get('rain', {}).get('3h', 0)
            })
        return pd.DataFrame(records)
    else:
        raise Exception(f"API error: {response.status_code}")

def extract_all(date=None):
    """
    Запуск всех источников извлечения.
    """
    print(f"[EXTRACT] Загрузка данных за {date if date else 'сегодня'}...")
    
    consumption_df = extract_from_csv(date=date)
    weather_df = extract_from_weather_api(date=date)
    
    print(f"  - Потребление: {len(consumption_df)} записей")
    print(f"  - Погода: {len(weather_df)} записей")
    
    return {
        'consumption': consumption_df,
        'weather': weather_df
    }

if __name__ == "__main__":
    data = extract_all()
    print(data['consumption'].head())