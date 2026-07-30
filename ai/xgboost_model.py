"""
ai/xgboost_model.py - Modelo para predecir si subirá o bajará
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import joblib
from pathlib import Path

class XGBoostModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.features = []
    
    def prepare_data(self, symbol: str, period: str = "1y"):
        """Prepara datos históricos para entrenamiento"""
        # Descargar datos históricos
        import MetaTrader5 as mt5
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1000)
        df = pd.DataFrame(rates)
        
        # Crear features (indicadores)
        df['return_1'] = df['close'].pct_change()
        df['return_5'] = df['close'].pct_change(5)
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # Target: si subirá en las próximas 5 velas
        df['target'] = (df['close'].shift(-5) > df['close']).astype(int)
        
        df = df.dropna()
        return df
    
    def train(self, symbol: str):
        """Entrena el modelo"""
        df = self.prepare_data(symbol)
        
        features = ['return_1', 'return_5', 'sma_10', 'sma_20', 'rsi']
        X = df[features]
        y = df['target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1
        )
        self.model.fit(X_train_scaled, y_train)
        
        accuracy = self.model.score(X_test_scaled, y_test)
        print(f"✅ Modelo entrenado para {symbol} - Accuracy: {accuracy:.2%}")
        
        # Guardar modelo
        Path("data/models").mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, f"data/models/{symbol}_model.joblib")
        joblib.dump(self.scaler, f"data/models/{symbol}_scaler.joblib")