# test_ia.py - VERSIÓN CORREGIDA
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
import os

def test_ia_prediccion():
    """Prueba la predicción de la IA para GOOG con las features correctas"""
    
    print("\n" + "="*60)
    print("🧠 TEST DE PREDICCIÓN IA (CORREGIDO)")
    print("="*60)
    
    # Conectar a MT5
    if not mt5.initialize():
        print("❌ Error conectando a MT5")
        return
    
    simbolo = "GOOG"
    print(f"\n📊 Probando predicción para {simbolo}")
    print("-"*40)
    
    # Verificar modelo
    model_path = f"data/models/{simbolo}_model.joblib"
    scaler_path = f"data/models/{simbolo}_scaler.joblib"
    
    if not os.path.exists(model_path):
        print(f"❌ Modelo no encontrado: {model_path}")
        return
    
    modelo = joblib.load(model_path)
    scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
    
    print(f"✅ Modelo cargado: {type(modelo).__name__}")
    if scaler:
        print(f"✅ Scaler cargado: {type(scaler).__name__}")
    
    # Verificar features que espera el modelo
    if hasattr(modelo, 'feature_names_in_'):
        features_esperadas = list(modelo.feature_names_in_)
        print(f"📋 Features esperadas: {features_esperadas}")
    else:
        # Si no tiene feature_names, usar las del scaler
        if scaler and hasattr(scaler, 'feature_names_in_'):
            features_esperadas = list(scaler.feature_names_in_)
            print(f"📋 Features del scaler: {features_esperadas}")
        else:
            features_esperadas = ['return_1', 'return_5', 'sma_10', 'sma_20', 'rsi']
            print(f"📋 Features asumidas: {features_esperadas}")
    
    # Obtener datos (más velas para mejor cálculo)
    rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, 200)
    if rates is None or len(rates) < 50:
        print(f"❌ No se obtuvieron datos suficientes")
        return
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    print(f"📈 Datos obtenidos: {len(df)} velas")
    
    # Calcular features CORRECTAS
    features_df = calcular_features_correctas(df, features_esperadas)
    
    if features_df is None or len(features_df) == 0:
        print("❌ Error calculando features")
        return
    
    print(f"📊 Features calculadas: {features_df.shape[0]} filas, {features_df.shape[1]} columnas")
    
    # Mostrar últimas features
    ultimo = features_df.iloc[-1]
    print("\n📊 Últimos valores:")
    for f in features_esperadas:
        if f in ultimo:
            print(f"  {f}: {ultimo[f]:.6f}")
    
    # Escalar y predecir
    try:
        if scaler:
            features_scaled = scaler.transform(features_df)
            print("✅ Datos escalados correctamente")
        else:
            features_scaled = features_df.values
            print("⚠️ Sin scaler, usando datos sin escalar")
        
        # Predicción
        probabilidad = modelo.predict_proba(features_scaled)
        prediccion = modelo.predict(features_scaled)
        
        print(f"\n" + "="*60)
        print("🎯 RESULTADOS DE PREDICCIÓN")
        print("="*60)
        print(f"  Última predicción: {'🟢 COMPRA' if prediccion[-1] == 1 else '🔴 VENTA'}")
        print(f"  Probabilidad COMPRA: {probabilidad[-1][1]:.3f} ({probabilidad[-1][1]*100:.1f}%)")
        print(f"  Probabilidad VENTA:  {probabilidad[-1][0]:.3f} ({probabilidad[-1][0]*100:.1f}%)")
        
        # Score en escala 0-70
        score = probabilidad[-1][1] * 70
        print(f"\n  📊 Score: {score:.1f}/70")
        
        # Verificar threshold
        THRESHOLD = 35
        if score >= THRESHOLD:
            print(f"  ✅ SUPERA el threshold ({THRESHOLD})")
            print(f"  🟢 SEÑAL: COMPRA")
        else:
            print(f"  ❌ NO SUPERA el threshold ({THRESHOLD})")
            print(f"  🔴 SEÑAL: VENTA o NEUTRAL")
            
        # Mostrar histórico de predicciones
        print(f"\n📈 Histórico de predicciones (últimas 10):")
        for i in range(max(0, len(prediccion)-10), len(prediccion)):
            proba = probabilidad[i][1]
            pred = "🟢COMPRA" if prediccion[i] == 1 else "🔴VENTA"
            print(f"  {i}: {pred} (prob:{proba:.3f})")
            
    except Exception as e:
        print(f"❌ Error en predicción: {e}")
        import traceback
        traceback.print_exc()
    
    mt5.shutdown()
    
    print("\n" + "="*60)
    print("✅ PRUEBA COMPLETADA")
    print("="*60)

def calcular_features_correctas(df, features_esperadas):
    """Calcula las features que espera el modelo XGBoost"""
    try:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['tick_volume']
        
        features = pd.DataFrame()
        
        # 1. Returns (retornos)
        features['return_1'] = close.pct_change(periods=1) * 100  # En porcentaje
        features['return_5'] = close.pct_change(periods=5) * 100  # En porcentaje
        
        # 2. Medias móviles
        features['sma_10'] = close.rolling(window=10).mean()
        features['sma_20'] = close.rolling(window=20).mean()
        
        # 3. RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. MACD (opcional, pero lo añadimos por si acaso)
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        features['macd'] = macd - macd_signal
        
        # 5. ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features['atr'] = tr.rolling(window=14).mean()
        
        # 6. Volumen
        features['volume'] = volume
        
        # Eliminar NaN
        features = features.dropna()
        
        # Verificar que tenemos todas las features necesarias
        features_faltantes = [f for f in features_esperadas if f not in features.columns]
        if features_faltantes:
            print(f"⚠️ Features faltantes: {features_faltantes}")
            # Añadir features faltantes con ceros
            for f in features_faltantes:
                features[f] = 0
        
        # Seleccionar solo las features que espera el modelo
        features_disponibles = [f for f in features_esperadas if f in features.columns]
        if not features_disponibles:
            print("❌ Ninguna feature coincidente")
            return None
            
        features = features[features_disponibles]
        
        return features
        
    except Exception as e:
        print(f"❌ Error calculando features: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_ia_prediccion()