# ai/predictor.py - VERSIÓN COMPLETA CORREGIDA

import joblib
import os
import numpy as np
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


class Predictor:
    """Predictor de IA para DELTA ENGINE usando XGBoost"""
    
    def __init__(self, model_dir="data/models/"):
        self.model_dir = model_dir
        self.models = {}
        self.scalers = {}
        self.feature_order = ['return_1', 'return_5', 'sma_10', 'sma_20', 'rsi']
        self._load_models()
    
    def _load_models(self):
        """Carga todos los modelos disponibles"""
        if not os.path.exists(self.model_dir):
            logger.warning(f"Directorio de modelos no encontrado: {self.model_dir}")
            return
        
        loaded_count = 0
        for file in os.listdir(self.model_dir):
            if file.endswith('_model.joblib'):
                symbol = file.replace('_model.joblib', '')
                model_path = os.path.join(self.model_dir, file)
                scaler_path = os.path.join(self.model_dir, f'{symbol}_scaler.joblib')
                
                try:
                    self.models[symbol] = joblib.load(model_path)
                    loaded_count += 1
                    
                    if os.path.exists(scaler_path):
                        self.scalers[symbol] = joblib.load(scaler_path)
                        logger.debug(f"✅ Modelo y scaler cargados para {symbol}")
                    else:
                        logger.debug(f"⚠️ Modelo cargado sin scaler para {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error cargando modelo {symbol}: {e}")
        
        logger.info(f"✅ {loaded_count} modelos cargados de {self.model_dir}")
    
        # ai/predictor.py - CORREGIR EL WARNING

    def predict(self, symbol: str, features: dict) -> dict:
        """Predice usando el modelo XGBoost - VERSIÓN CORREGIDA"""
        try:
            if symbol not in self.models:
                return {'signal': 'NEUTRAL', 'confidence': 0, 'score': 0}
            
            model = self.models[symbol]
            scaler = self.scalers.get(symbol)
            
            # Preparar features en el orden correcto
            feature_order = ['return_1', 'return_5', 'sma_10', 'sma_20', 'rsi']
            feature_values = [[features.get(f, 0) for f in feature_order]]
            
            # 🔥 CREAR DATAFRAME CON NOMBRES DE COLUMNAS PARA EVITAR EL WARNING
            import pandas as pd
            X = pd.DataFrame(feature_values, columns=feature_order)
            
            # Escalar si es necesario
            if scaler:
                X_scaled = scaler.transform(X)
            else:
                X_scaled = X.values
            
            # Predecir
            proba = model.predict_proba(X_scaled)[0]
            prediction = model.predict(X_scaled)[0]
            
            # Calcular score
            score = proba[1] * 70
            
            signal = 'BUY' if prediction == 1 else 'SELL'
            confidence = proba[1] if prediction == 1 else proba[0]
            
            return {
                'signal': signal,
                'confidence': confidence,
                'score': score,
                'probability': proba[1]
            }
            
        except Exception as e:
            logger.error(f"Error prediciendo {symbol}: {e}")
            return {'signal': 'NEUTRAL', 'confidence': 0, 'score': 0}
    
    def predict_batch(self, symbol: str, features_list: list) -> list:
        """Predice múltiples muestras a la vez"""
        results = []
        for features in features_list:
            results.append(self.predict(symbol, features))
        return results
    
    def is_ready(self) -> bool:
        """Verifica si hay modelos cargados"""
        return len(self.models) > 0
    
    def get_loaded_symbols(self) -> list:
        """Retorna lista de símbolos con modelos cargados"""
        return list(self.models.keys())
    
    def get_model_info(self, symbol: str) -> dict:
        """Obtiene información del modelo para un símbolo"""
        if symbol not in self.models:
            return {'loaded': False}
        
        model = self.models[symbol]
        info = {
            'loaded': True,
            'type': type(model).__name__,
            'has_scaler': symbol in self.scalers,
            'features': self.feature_order.copy()
        }
        
        if hasattr(model, 'n_features_in_'):
            info['n_features'] = model.n_features_in_
        
        return info