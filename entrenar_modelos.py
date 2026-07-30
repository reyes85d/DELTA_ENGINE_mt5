"""
Entrenar modelos de IA para DELTA ENGINE MT5
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import xgboost as xgb
import joblib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.logger import get_logger

logger = get_logger(__name__)


def prepare_data(symbol: str, period: int = 1000):
    """Prepara datos históricos para entrenamiento"""
    try:
        if not mt5.initialize():
            logger.error("❌ Error inicializando MT5")
            return None
        
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, period)
        if rates is None or len(rates) == 0:
            logger.warning(f"⚠️ No hay datos para {symbol}")
            return None
        
        df = pd.DataFrame(rates)
        
        df['return_1'] = df['close'].pct_change()
        df['return_5'] = df['close'].pct_change(5)
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['rsi'] = calculate_rsi(df['close'])
        df['target'] = (df['close'].shift(-5) > df['close']).astype(int)
        
        df = df.dropna()
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


def train_xgboost(symbol: str):
    """Entrena modelo XGBoost para un símbolo"""
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
    logger.info(f"   Clases: 0={n_0}, 1={n_1} ({n_1/(n_0+n_1)*100:.1f}% positivos)")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1]) if len(y_train[y_train == 1]) > 0 else 1
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='logloss'
    )
    model.fit(X_train_scaled, y_train)
    
    accuracy = model.score(X_test_scaled, y_test)
    y_pred = model.predict(X_test_scaled)
    report = classification_report(y_test, y_pred, output_dict=True)
    
    precision_1 = report.get('1', {}).get('precision', 0)
    recall_1 = report.get('1', {}).get('recall', 0)
    
    logger.info(f"✅ {symbol}: Accuracy={accuracy:.2%} | Precision(1)={precision_1:.2%} | Recall(1)={recall_1:.2%}")
    
    Path("data/models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, f"data/models/{symbol}_model.joblib")
    joblib.dump(scaler, f"data/models/{symbol}_scaler.joblib")
    
    return True


def main():
    print("\n" + "="*60)
    print("🚀 ENTRENANDO MODELOS DE IA PARA MT5")
    print("="*60 + "\n")
    
    if not mt5.initialize():
        logger.error("❌ Error inicializando MT5")
        return
    
    logger.info("✅ Conectado a MT5")
    
    # En la función main, añadir Forex:
    # En backtest_engine.py
    symbols = [ "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD",  # Mayores
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "AUDNZD",  # Cruces
    "EURAUD", "EURCHF", "GBPAUD", "GBPCAD", "GBPCHF",  # Más cruces
    "CADJPY", "CHFJPY", "NZDJPY", "NZDCAD",]   # Pares con JPY y CAD  # 🔥 Más volátiles
    
    
    logger.info(f"📊 Entrenando {len(symbols)} símbolos...\n")
    
    entrenados = 0
    for symbol in symbols:
        if train_xgboost(symbol):
            entrenados += 1
    
    print("\n" + "="*60)
    print(f"✅ {entrenados}/{len(symbols)} modelos entrenados")
    print(f"📁 Modelos guardados en: data/models/")
    print("="*60)
    
    model_dir = Path("data/models")
    if model_dir.exists():
        models = list(model_dir.glob("*_model.joblib"))
        print(f"\n📋 Modelos creados: {len(models)}")
        for m in models:
            print(f"   - {m.name}")
    
    mt5.shutdown()


if __name__ == "__main__":
    main()