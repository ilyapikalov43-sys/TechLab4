#!/usr/bin/env python3
"""
Модуль загрузки (Load) ETL-пайплайна.
Целевые хранилища: PostgreSQL, MongoDB, FAISS (векторная БД).
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from pymongo import MongoClient
import faiss
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# ============ PostgreSQL ============

def init_postgres():
    """Инициализация таблиц в PostgreSQL."""
    engine = create_engine(
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'energy')}"
    )
    
    with engine.connect() as conn:
        # Таблица buildings
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS buildings (
                household_id INTEGER PRIMARY KEY,
                area_sq_m FLOAT,
                year_built INTEGER,
                building_type VARCHAR(50)
            )
        """))
        
        # Таблица consumption
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consumption (
                id SERIAL PRIMARY KEY,
                household_id INTEGER,
                timestamp TIMESTAMP,
                energy_kwh FLOAT,
                water_liters FLOAT,
                gas_kwh FLOAT,
                temperature_c FLOAT,
                humidity_pct FLOAT,
                day_of_week INTEGER,
                is_weekend INTEGER,
                is_peak_hour INTEGER,
                FOREIGN KEY (household_id) REFERENCES buildings(household_id)
            )
        """))
        
        # Таблица weather
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                temperature_c FLOAT,
                humidity_pct FLOAT,
                wind_speed FLOAT,
                precipitation_mm FLOAT
            )
        """))
        
        conn.commit()
    
    return engine

def load_to_postgres(transformed_data, engine):
    """Загрузка данных в PostgreSQL."""
    print("[LOAD] Загрузка в PostgreSQL...")
    
    # Загрузка данных о потреблении
    consumption_df = transformed_data['enriched_consumption']
    consumption_to_db = consumption_df[['household_id', 'timestamp', 'energy_kwh', 'water_liters', 
                                         'gas_kwh', 'temperature_c', 'humidity_pct', 
                                         'day_of_week', 'is_weekend', 'is_peak_hour']]
    
    consumption_to_db.to_sql('consumption', engine, if_exists='append', index=False)
    print(f"  - Загружено {len(consumption_to_db)} записей в consumption")
    
    # Загрузка погодных данных
    weather_df = transformed_data['weather']
    weather_df.to_sql('weather', engine, if_exists='append', index=False)
    print(f"  - Загружено {len(weather_df)} записей в weather")
    
    return engine

# ============ MongoDB ============

def init_mongodb():
    """Подключение к MongoDB."""
    uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    client = MongoClient(uri)
    db = client['energy']
    return db

def load_to_mongodb(transformed_data, db):
    """Загрузка сырых данных в MongoDB."""
    print("[LOAD] Загрузка в MongoDB...")
    
    collection = db['raw_consumption']
    
    # Конвертация DataFrame в список словарей
    raw_df = transformed_data['raw_consumption']
    records = raw_df.to_dict('records')
    
    if len(records) > 0:
        collection.insert_many(records)
        print(f"  - Загружено {len(records)} записей в коллекцию raw_consumption")
    
    return db

# ============ FAISS (Vector DB) ============

def build_faiss_index(transformed_data, index_path="data/processed/faiss_index.bin"):
    """Построение векторного индекса для поиска аномальных профилей потребления."""
    print("[LOAD] Построение FAISS индекса...")
    
    consumption_df = transformed_data['enriched_consumption']
    
    # Агрегация профилей потребления по домохозяйствам
    profiles = consumption_df.groupby('household_id').agg({
        'energy_kwh': ['mean', 'std'],
        'water_liters': ['mean', 'std'],
        'gas_kwh': ['mean', 'std']
    })
    
    # Создание признаков для векторизации
    profile_features = []
    for idx, row in profiles.iterrows():
        features = [
            row[('energy_kwh', 'mean')],
            row[('energy_kwh', 'std')],
            row[('water_liters', 'mean')],
            row[('water_liters', 'std')],
            row[('gas_kwh', 'mean')],
            row[('gas_kwh', 'std')]
        ]
        profile_features.append(features)
    
    profile_features = np.array(profile_features, dtype=np.float32)
    
    # Нормализация и создание индекса
    faiss.normalize_L2(profile_features)
    dimension = profile_features.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(profile_features)
    
    # Сохранение индекса
    os.makedirs("data/processed", exist_ok=True)
    faiss.write_index(index, index_path)
    
    print(f"  - Индекс сохранён: {index_path}")
    print(f"  - Векторов: {index.ntotal}, размерность: {dimension}")
    
    return index

def search_similar_profiles(query_features, index, top_k=5):
    """Поиск похожих профилей потребления."""
    query = np.array([query_features], dtype=np.float32)
    faiss.normalize_L2(query)
    distances, indices = index.search(query, top_k)
    return distances, indices

# ============ Основная функция ============

def load_all(transformed_data):
    """Загрузка во все хранилища."""
    # PostgreSQL
    pg_engine = init_postgres()
    load_to_postgres(transformed_data, pg_engine)
    
    # MongoDB
    mongo_db = init_mongodb()
    load_to_mongodb(transformed_data, mongo_db)
    
    # FAISS
    faiss_index = build_faiss_index(transformed_data)
    
    print("[LOAD] Загрузка завершена!")
    
    return {
        'postgres': pg_engine,
        'mongodb': mongo_db,
        'faiss': faiss_index
    }

if __name__ == "__main__":
    from extract import extract_all
    from transform import transform_all
    
    extracted = extract_all()
    transformed = transform_all(extracted)
    load_all(transformed)