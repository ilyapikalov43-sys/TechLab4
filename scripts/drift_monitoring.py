#!/usr/bin/env python3
"""
Модуль мониторинга дрейфа данных с Evidently AI.
Сравнение распределений между референсным и текущим периодами.
"""

import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently import ColumnMapping
import json
from datetime import datetime, timedelta

def load_reference_data(path="data/raw/london_households.csv"):
    """Загрузка референсных данных (исторические)."""
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def load_current_data(path="data/raw/london_households.csv", days_back=7):
    """Загрузка текущих данных (последние N дней)."""
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    cutoff = datetime.now() - timedelta(days=days_back)
    current = df[df['timestamp'] >= cutoff]
    
    if len(current) == 0:
        # Если нет новых данных, используем последние 20% записей как "текущие"
        current = df.tail(int(len(df) * 0.2))
    
    return current

def run_drift_analysis():
    """
    Запуск анализа дрейфа данных.
    """
    print("[DRIFT] Запуск мониторинга дрейфа данных...")
    
    # Загрузка данных
    reference = load_reference_data()
    current = load_current_data()
    
    print(f"  - Референсный период: {len(reference)} записей")
    print(f"  - Текущий период: {len(current)} записей")
    
    # Настройка колонок
    numeric_features = ['energy_kwh', 'water_liters', 'gas_kwh', 'temperature_c', 'humidity_pct']
    categorical_features = ['household_id']
    
    column_mapping = ColumnMapping(
        numerical_features=numeric_features,
        categorical_features=categorical_features,
        datetime_features=['timestamp']
    )
    
    # Отчёт о дрейфе данных
    data_drift_report = Report(metrics=[DataDriftPreset()])
    data_drift_report.run(reference_data=reference, current_data=current, column_mapping=column_mapping)
    
    # Сохранение отчёта
    report_path = "data/processed/drift_report.html"
    data_drift_report.save_html(report_path)
    print(f"  - Отчёт о дрейфе сохранён в {report_path}")
    
    # Вывод статистики дрейфа
    result = data_drift_report.as_dict()
    
    if 'data_drift' in result:
        drift_summary = result['data_drift']
        print("\n[DRIFT] Результаты по колонкам:")
        for col, metrics in drift_summary.items():
            if isinstance(metrics, dict) and 'drift_score' in metrics:
                drift_status = "ДРЕЙФ" if metrics.get('drifted', False) else "стабильна"
                print(f"  - {col}: score={metrics['drift_score']:.3f} ({drift_status})")
    
    # Анализ дрейфа целевой переменной (если есть)
    if 'energy_kwh' in reference.columns:
        target_report = Report(metrics=[TargetDriftPreset()])
        target_report.run(reference_data=reference, current_data=current, column_mapping=column_mapping)
        target_report.save_html("data/processed/target_drift_report.html")
        print("  - Отчёт о дрейфе целевой переменной сохранён")
    
    return data_drift_report

def send_alert_if_drift(drift_report, threshold=0.3):
    """
    Отправка уведомления при обнаружении значительного дрейфа.
    (Демонстрационная версия)
    """
    try:
        result = drift_report.as_dict()
        drifted_columns = []
        
        if 'data_drift' in result:
            for col, metrics in result['data_drift'].items():
                if isinstance(metrics, dict) and metrics.get('drift_score', 0) > threshold:
                    drifted_columns.append(col)
        
        if drifted_columns:
            print(f"\n[ALERT] Обнаружен дрейф в колонках: {drifted_columns}")
            # Здесь можно добавить реальную отправку уведомлений (email, Telegram, Slack)
            # send_telegram_message(f"Дрейф данных: {drifted_columns}")
        else:
            print("\n[ALERT] Значительный дрейф не обнаружен")
    except Exception as e:
        print(f"Ошибка при анализе дрейфа: {e}")

if __name__ == "__main__":
    report = run_drift_analysis()
    send_alert_if_drift(report)