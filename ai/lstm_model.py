"""
ai/lstm_model.py - Modelo LSTM para predicción de precios
"""

import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

class LSTMModel:
    def __init__(self, sequence_length=60):
        self.sequence_length = sequence_length
        self.model = None
    
    def create_sequences(self, data):
        X, y = [], []
        for i in range(self.sequence_length, len(data)):
            X.append(data[i-self.sequence_length:i])
            y.append(data[i, 0])  # Predecir el precio de cierre
        return np.array(X), np.array(y)
    
    def train(self, symbol: str):
        """Entrena modelo LSTM"""
        # Descargar datos
        import MetaTrader5 as mt5
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1000)
        df = pd.DataFrame(rates)
        
        # Normalizar
        data = df[['close']].values
        scaler = MinMaxScaler()
        data_scaled = scaler.fit_transform(data)
        
        # Crear secuencias
        X, y = self.create_sequences(data_scaled)
        
        # Dividir
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # Crear modelo LSTM
        self.model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.sequence_length, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse')
        self.model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=0)
        
        # Guardar
        self.model.save(f"data/models/{symbol}_lstm.h5")
        joblib.dump(scaler, f"data/models/{symbol}_lstm_scaler.joblib")