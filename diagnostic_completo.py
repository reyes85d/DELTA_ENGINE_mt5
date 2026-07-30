# diagnostic_completo.py
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import os
import sys

def diagnosticar_completo():
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA")
    print("="*60)
    
    # 1. Conectar a MT5
    print("\n📡 1. CONEXIÓN A MT5")
    print("-"*40)
    if not mt5.initialize():
        print("❌ Error al conectar MT5")
        return
    print("✅ MT5 conectado")
    
    # 2. Verificar modelos cargados
    print("\n🧠 2. MODELOS DISPONIBLES")
    print("-"*40)
    model_dir = "data/models/"
    if os.path.exists(model_dir):
        modelos = [f for f in os.listdir(model_dir) if f.endswith('.joblib') and 'model' in f]
        print(f"✅ Modelos encontrados: {len(modelos)}")
        for m in modelos[:5]:  # Mostrar primeros 5
            print(f"   - {m}")
        if len(modelos) > 5:
            print(f"   ... y {len(modelos)-5} más")
    else:
        print("❌ Directorio de modelos no encontrado")
    
    # 3. Probar símbolos específicos
    print("\n📊 3. ANÁLISIS DE SÍMBOLOS")
    print("-"*40)
    
    simbolos_prueba = [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
        "AAPL", "GOOG", "NVDA", "TSLA"
    ]
    
    resultados = []
    
    for simbolo in simbolos_prueba:
        print(f"\n🔹 {simbolo}")
        print("   " + "-"*35)
        
        # Verificar si existe en MT5
        info = mt5.symbol_info(simbolo)
        if not info:
            print(f"   ❌ Símbolo no disponible en MT5")
            continue
            
        # Obtener datos
        rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, 100)
        if rates is None or len(rates) < 50:
            print(f"   ❌ Datos insuficientes: {len(rates) if rates is not None else 0} velas")
            continue
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Calcular indicadores
        close = df['close']
        high = df['high']
        low = df['low']
        
        # 1. RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 2. MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        
        # 3. Medias móviles
        sma20 = close.rolling(window=20).mean()
        sma50 = close.rolling(window=50).mean()
        
        # 4. Bollinger Bands
        bb_middle = sma20
        bb_std = close.rolling(window=20).std()
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std
        
        # 5. ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        # Últimos valores
        ultimo_precio = close.iloc[-1]
        ultimo_rsi = rsi.iloc[-1]
        ultimo_macd = macd.iloc[-1] - macd_signal.iloc[-1]  # Histograma
        ultimo_atr = atr.iloc[-1]
        
        print(f"   💰 Precio actual: {ultimo_precio:.5f}")
        print(f"   📈 RSI (14): {ultimo_rsi:.2f}")
        print(f"   📊 MACD Hist: {ultimo_macd:.5f}")
        print(f"   📉 ATR (14): {ultimo_atr:.5f}")
        
        # Tendencias
        tendencia = "NEUTRAL"
        if sma20.iloc[-1] > sma50.iloc[-1] and close.iloc[-1] > sma20.iloc[-1]:
            tendencia = "ALCISTA"
        elif sma20.iloc[-1] < sma50.iloc[-1] and close.iloc[-1] < sma20.iloc[-1]:
            tendencia = "BAJISTA"
        
        print(f"   🎯 Tendencia: {tendencia}")
        
        # Señales
        senal = "NEUTRAL"
        score = 0
        
        # RSI señales
        if ultimo_rsi < 30:
            senal = "COMPRA (sobreventa)"
            score += 25
        elif ultimo_rsi > 70:
            senal = "VENTA (sobrecompra)"
            score += 25
            
        # MACD señales
        if ultimo_macd > 0 and ultimo_macd > macd.iloc[-2] - macd_signal.iloc[-2]:
            score += 20
            if senal == "NEUTRAL":
                senal = "COMPRA (MACD)"
        elif ultimo_macd < 0 and ultimo_macd < macd.iloc[-2] - macd_signal.iloc[-2]:
            score += 20
            if senal == "NEUTRAL":
                senal = "VENTA (MACD)"
                
        # Tendencia
        if tendencia == "ALCISTA":
            score += 15
        elif tendencia == "BAJISTA":
            score += 15
            
        # Volumen
        if rates[-1]['tick_volume'] > rates[-2]['tick_volume'] * 1.2:
            score += 10
            
        print(f"   🎲 Score estimado: {score}/70")
        print(f"   🚦 Señal: {senal}")
        
        # Guardar resultado
        resultados.append({
            'simbolo': simbolo,
            'precio': ultimo_precio,
            'rsi': ultimo_rsi,
            'score': score,
            'senal': senal,
            'tendencia': tendencia
        })
        
        # Verificar modelo específico
        modelo_path = f"data/models/{simbolo}_model.joblib"
        if os.path.exists(modelo_path):
            print(f"   ✅ Modelo IA disponible")
            try:
                modelo = joblib.load(modelo_path)
                print(f"   🤖 Tipo: {type(modelo).__name__}")
            except:
                print(f"   ⚠️ Error cargando modelo")
        else:
            print(f"   ❌ Modelo IA NO disponible")
    
    # 4. Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE SEÑALES")
    print("="*60)
    
    # Crear DataFrame
    df_resultados = pd.DataFrame(resultados)
    df_resultados = df_resultados.sort_values('score', ascending=False)
    
    print("\n🏆 TOP 5 MEJORES OPORTUNIDADES:")
    print("-"*40)
    for i, row in df_resultados.head(5).iterrows():
        emoji = "🟢" if "COMPRA" in row['senal'] else "🔴" if "VENTA" in row['senal'] else "⚪"
        print(f"{emoji} {row['simbolo']}: Score={row['score']:.0f} | {row['senal']} | {row['precio']:.5f}")
    
    print("\n⚠️ SÍMBOLOS CON POSICIONES ABIERTAS:")
    print("-"*40)
    positions = mt5.positions_get()
    if positions:
        for pos in positions:
            simbolo = pos.symbol
            tipo = "COMPRA" if pos.type == 0 else "VENTA"
            print(f"   🟡 {simbolo}: {tipo} {pos.volume} @ {pos.price_open:.5f} | P&L: {pos.profit:.2f}")
    else:
        print("   No hay posiciones abiertas")
    
    # 5. Recomendaciones
    print("\n💡 RECOMENDACIONES")
    print("="*60)
    
    # Ver si hay scores altos
    scores_altos = df_resultados[df_resultados['score'] >= 35]
    if len(scores_altos) > 0:
        print(f"✅ Hay {len(scores_altos)} símbolos con score cercano al threshold (40)")
        print("   Considera:")
        print("   - Bajar el SCORE_MINIMO a 35 temporalmente")
        print("   - Revisar estos símbolos manualmente:")
        for _, row in scores_altos.head(3).iterrows():
            print(f"     • {row['simbolo']} (score: {row['score']:.0f})")
    else:
        print("⚠️ Todos los scores están por debajo de 35")
        print("   Posibles causas:")
        print("   - Mercado en rango (sin tendencia clara)")
        print("   - Indicadores en zona neutral")
        print("   - Modelo necesita más datos de entrenamiento")
        print("   - Los features del modelo no capturan bien el momento")
    
    # 6. Verificar últimos trades
    print("\n📜 ÚLTIMOS TRADES (si existen)")
    print("-"*40)
    history = mt5.history_deals_get(
        datetime.now() - timedelta(days=1),
        datetime.now()
    )
    if history and len(history) > 0:
        for deal in history[-5:]:
            print(f"   {deal.symbol}: {deal.type} {deal.volume} @ {deal.price:.5f} | {deal.profit:.2f}")
    else:
        print("   No hay trades en las últimas 24h")
    
    mt5.shutdown()
    
    print("\n" + "="*60)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("="*60 + "\n")

if __name__ == "__main__":
    diagnosticar_completo()