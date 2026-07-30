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
    
    def predict(self, symbol: str, features: dict) -> dict:
        """
        Predice usando el modelo XGBoost
        
        Args:
            symbol: Símbolo a predecir (ej: 'GOOG')
            features: Diccionario con las features requeridas
            
        Returns:
            Dict con: signal, confidence, score, probability, prediction
        """
        try:
            if symbol not in self.models:
                logger.debug(f"⚠️ No hay modelo para {symbol}")
                return {
                    'signal': 'NEUTRAL', 
                    'confidence': 0, 
                    'score': 0,
                    'probability': 0.5,
                    'prediction': 0
                }
            
            model = self.models[symbol]
            
            # Preparar features en el orden correcto
            feature_values = []
            for f in self.feature_order:
                value = features.get(f, 0)
                # Si es NaN, convertir a 0
                if pd.isna(value) or np.isnan(value):
                    value = 0
                feature_values.append(value)
            
            # Convertir a array 2D
            X = np.array([feature_values], dtype=np.float32)
            
            # Aplicar scaler si existe
            if symbol in self.scalers:
                try:
                    X = self.scalers[symbol].transform(X)
                except Exception as e:
                    logger.debug(f"Error escalando {symbol}: {e}")
                    # Si falla el scaler, usar datos sin escalar
            
            # Predecir probabilidades
            try:
                # Intentar con predict_proba (para XGBoost, RandomForest, etc)
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(X)[0]
                    prediction = model.predict(X)[0]
                else:
                    # Para modelos sin predict_proba
                    prediction = model.predict(X)[0]
                    proba = [1 - prediction, prediction]  # Estimación simple
            except Exception as e:
                logger.error(f"Error en predicción {symbol}: {e}")
                return {
                    'signal': 'NEUTRAL', 
                    'confidence': 0, 
                    'score': 0,
                    'probability': 0.5,
                    'prediction': 0
                }
            
            # Calcular score (0-70)
            # proba[1] = probabilidad de clase 1 (BUY)
            buy_probability = float(proba[1])
            score = buy_probability * 70
            
            # Determinar señal
            if prediction == 1:
                signal = 'BUY'
                confidence = buy_probability
            else:
                signal = 'SELL'
                confidence = float(proba[0])
            
            # 🔥 LOG DE DIAGNÓSTICO
            logger.debug(f"🤖 {symbol}: pred={prediction} | proba_Buy={buy_probability:.3f} | score={score:.1f}/70")
            
            return {
                'signal': signal,
                'confidence': confidence,
                'score': score,
                'probability': buy_probability,
                'prediction': int(prediction)
            }
            
        except Exception as e:
            logger.error(f"Error prediciendo {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'signal': 'NEUTRAL', 
                'confidence': 0, 
                'score': 0,
                'probability': 0.5,
                'prediction': 0
            }
    
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