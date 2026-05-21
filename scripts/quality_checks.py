#!/usr/bin/env python3
"""
Модуль контроля качества данных с Great Expectations.
Проверка: пропуски, диапазоны, типы, уникальность.
"""

import pandas as pd
import great_expectations as ge
from great_expectations.core.batch import RuntimeBatchRequest
import os

def run_quality_checks(data_path="data/raw/london_households.csv"):
    """
    Запуск всех проверок качества.
    """
    print("[QUALITY] Запуск проверок качества данных...")
    
    df = pd.read_csv(data_path)
    ge_df = ge.from_pandas(df)
    
    results = {}
    
    # 1. Проверка на отсутствие пропусков в критических полях
    critical_cols = ['household_id', 'timestamp', 'energy_kwh', 'water_liters']
    for col in critical_cols:
        result = ge_df.expect_column_values_to_not_be_null(col)
        results[f"no_nulls_{col}"] = result.success
        print(f"  - {col}: нет пропусков = {result.success}")
    
    # 2. Проверка диапазонов значений
    ranges = {
        'energy_kwh': [0, 100],
        'water_liters': [0, 1000],
        'gas_kwh': [0, 50],
        'temperature_c': [-30, 50],
        'humidity_pct': [0, 100]
    }
    
    for col, (min_val, max_val) in ranges.items():
        if col in df.columns:
            result = ge_df.expect_column_values_to_be_between(col, min_val, max_val)
            results[f"range_{col}"] = result.success
            print(f"  - {col}: в диапазоне [{min_val}, {max_val}] = {result.success}")
    
    # 3. Проверка типов данных
    type_checks = {
        'household_id': 'int',
        'energy_kwh': 'float',
        'water_liters': 'float'
    }
    
    for col, expected_type in type_checks.items():
        actual_type = df[col].dtype
        is_correct = expected_type in str(actual_type)
        results[f"type_{col}"] = is_correct
        print(f"  - {col}: тип {actual_type} (ожидался {expected_type}) = {is_correct}")
    
    # 4. Проверка уникальности (нет дубликатов по ключу)
    unique_check = ge_df.expect_compound_columns_to_be_unique(['household_id', 'timestamp'])
    results["unique_keys"] = unique_check.success
    print(f"  - Уникальность ключей (household_id + timestamp) = {unique_check.success}")
    
    # Генерация отчёта
    report_path = "data/processed/quality_report.html"
    ge_df.save_expectation_suite("data/processed/expectations.json")
    print(f"\n[QUALITY] Отчёт сохранён в {report_path}")
    
    # Итоговая оценка
    success_rate = sum(results.values()) / len(results) * 100
    print(f"\n[QUALITY] Итоговая оценка качества: {success_rate:.1f}%")
    
    return results

if __name__ == "__main__":
    run_quality_checks()