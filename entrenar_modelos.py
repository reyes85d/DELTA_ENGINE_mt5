"""
Entrenar modelos de IA para DELTA ENGINE MT5 - VERSIÓN MEJORADA
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb
import joblib
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.logger import get_logger
from config import STOCKS, FOREX

logger = get_logger(__name__)


def prepare_data(symbol: str, period: int = 1000, timeframe=mt5.TIMEFRAME_H1):
    """
    Prepara datos históricos para entrenamiento
    
    Args:
        symbol: Símbolo a entrenar
        period: Número de velas
        timeframe: Timeframe (H1 por defecto)
    """
    try:
        if not mt5.initialize():
            logger.error("❌ Error inicializando MT5")
            return None
        
        # 🔥 VERIFICAR QUE EL SÍMBOLO EXISTE
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"⚠️ Símbolo {symbol} no encontrado en MT5")
            return None
        
        # 🔥 ACTIVAR SÍMBOLO SI ES NECESARIO
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)
        
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period)
        if rates is None or len(rates) < 100:
            logger.warning(f"⚠️ Datos insuficientes para {symbol}: {len(rates) if rates else 0}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # 🔥 CALCULAR FEATURES
        df['return_1'] = df['close'].pct_change()
        df['return_5'] = df['close'].pct_change(5)
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['rsi'] = calculate_rsi(df['close'])
        
        # 🔥 TARGET: Precio sube en las próximas 5 velas
        df['target'] = (df['close'].shift(-5) > df['close']).astype(int)
        
        # 🔥 ELIMINAR NaN
        df = df.dropna()
        
        if len(df) < 50:
            logger.warning(f"⚠️ Datos insuficientes después de limpieza para {symbol}: {len(df)}")
            return None
        
        return df
        
    except Exception as e:
        logger.error(f"Error preparando datos para {symbol}: {e}")
        return None


def calculate_rsi(prices, period=14):
    """Calcula RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def train_xgboost(symbol: str, test_size: float = 0.2, n_estimators: int = 150):
    """
    Entrena modelo XGBoost para un símbolo
    
    Args:
        symbol: Símbolo
        test_size: Proporción de datos de prueba
        n_estimators: Número de árboles
    """
    start_time = time.time()
    logger.info(f"🧠 Entrenando modelo para {symbol}...")
    
    df = prepare_data(symbol)
    if df is None or df.empty:
        logger.warning(f"⚠️ No se pudo entrenar {symbol}")
        return False
    
    features = ['return_1', 'return_5', 'sma_10', 'sma_20', 'rsi']
    X = df[features]
    y = df['target']
    
    n_0 = len(y[y == 0])
    n_1 = len(y[y == 1])
    total = n_0 + n_1
    
    if n_1 == 0 or n_0 == 0:
        logger.warning(f"⚠️ {symbol}: Datos desbalanceados extremos (0={n_0}, 1={n_1})")
        return False
    
    logger.info(f"   Clases: 0={n_0}, 1={n_1} ({n_1/total*100:.1f}% positivos)")
    
    # 🔥 DIVIDIR DATOS
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # 🔥 ESCALAR
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 🔥 PESO PARA CLASE POSITIVA (balanceo)
    scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1]) if len(y_train[y_train == 1]) > 0 else 1
    
    # 🔥 ENTRENAR MODELO
    model = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='logloss',
        n_jobs=-1,  # Usar todos los núcleos
        early_stopping_rounds=20
    )
    
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False
    )
    
    # 🔥 EVALUAR
    accuracy = model.score(X_test_scaled, y_test)
    y_pred = model.predict(X_test_scaled)
    report = classification_report(y_test, y_pred, output_dict=True)
    
    precision_1 = report.get('1', {}).get('precision', 0)
    recall_1 = report.get('1', {}).get('recall', 0)
    f1_1 = report.get('1', {}).get('f1-score', 0)
    
    # 🔥 MATRIZ DE CONFUSIÓN
    cm = confusion_matrix(y_test, y_pred)
    
    elapsed = time.time() - start_time
    
    logger.info(f"✅ {symbol}: Accuracy={accuracy:.2%} | Precision(1)={precision_1:.2%} | Recall(1)={recall_1:.2%} | F1={f1_1:.2%} | Tiempo={elapsed:.1f}s")
    logger.info(f"   Matriz: [[{cm[0][0]}, {cm[0][1]}], [{cm[1][0]}, {cm[1][1]}]]")
    
    # 🔥 GUARDAR MODELO
    Path("data/models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, f"data/models/{symbol}_model.joblib")
    joblib.dump(scaler, f"data/models/{symbol}_scaler.joblib")
    
    return True


def main():
    print("\n" + "="*70)
    print("🚀 ENTRENANDO MODELOS DE IA PARA MT5")
    print("="*70 + "\n")
    
    if not mt5.initialize():
        logger.error("❌ Error inicializando MT5")
        return
    
    logger.info("✅ Conectado a MT5")
    
    # 🔥 SÍMBOLOS A ENTRENAR (usando config)
    symbols = []
    
    # Acciones
    symbols.extend(STOCKS)
    
    # Forex
    symbols.extend(FOREX)
    
    # 🔥 FILTRAR SÍMBOLOS QUE EXISTEN EN MT5
    valid_symbols = []
    for symbol in symbols:
        info = mt5.symbol_info(symbol)
        if info is not None:
            valid_symbols.append(symbol)
        else:
            logger.warning(f"⚠️ Símbolo {symbol} no disponible en MT5, omitiendo...")
    
    logger.info(f"📊 Entrenando {len(valid_symbols)} símbolos válidos de {len(symbols)}...\n")
    
    start_time = time.time()
    entrenados = 0
    fallos = 0
    
    for i, symbol in enumerate(valid_symbols, 1):
        logger.info(f"📈 [{i}/{len(valid_symbols)}] {symbol}")
        if train_xgboost(symbol):
            entrenados += 1
        else:
            fallos += 1
    
    elapsed = time.time() - start_time
    
    # 🔥 RESUMEN
    print("\n" + "="*70)
    print("📊 RESUMEN DE ENTRENAMIENTO")
    print("="*70)
    print(f"✅ Modelos entrenados: {entrenados}")
    print(f"❌ Fallos: {fallos}")
    print(f"⏱️  Tiempo total: {elapsed:.1f}s")
    print(f"📁 Modelos guardados en: data/models/")
    print("="*70)
    
    # 🔥 LISTAR MODELOS CREADOS
    model_dir = Path("data/models")
    if model_dir.exists():
        models = list(model_dir.glob("*_model.joblib"))
        scalers = list(model_dir.glob("*_scaler.joblib"))
        print(f"\n📋 Modelos creados: {len(models)}")
        print(f"📋 Scalers creados: {len(scalers)}")
        
        if models:
            print("\n📂 Modelos disponibles:")
            for m in sorted(models):
                size = m.stat().st_size / 1024  # KB
                print(f"   - {m.name} ({size:.1f} KB)")
    
    mt5.shutdown()
    print("\n✅ Entrenamiento completado")


if __name__ == "__main__":
    main()