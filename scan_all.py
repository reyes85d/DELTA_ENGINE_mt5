# scan_all.py
from strategies.strategy import Strategy
import MetaTrader5 as mt5

def scan_all():
    mt5.initialize()
    strategy = Strategy()
    
    print("\n" + "="*70)
    print("🔍 ESCANEO COMPLETO DE SEÑALES")
    print("="*70)
    
    # Todos los símbolos con modelos
    symbols = strategy.predictor.get_loaded_symbols() if strategy.predictor else []
    
    if not symbols:
        print("❌ No hay modelos cargados")
        return
    
    signals_found = []
    
    for symbol in symbols:
        signal = strategy.analyze_symbol(symbol)
        if signal:
            signals_found.append(signal)
            print(f"\n✅ {symbol}: {signal['action']}")
            print(f"   Score: {signal['score']:.1f}/70")
            print(f"   Confianza: {signal['confidence']:.2%}")
            print(f"   Tendencia: {signal['trend']}")
    
    print("\n" + "="*70)
    print(f"📊 RESULTADOS: {len(signals_found)} señales encontradas de {len(symbols)} símbolos")
    
    if signals_found:
        print("\n🎯 SEÑALES DETECTADAS:")
        for s in signals_found:
            emoji = "🟢" if s['action'] == 'BUY' else "🔴"
            print(f"  {emoji} {s['symbol']}: {s['action']} | Score: {s['score']:.1f} | Conf: {s['confidence']:.2%}")
    else:
        print("\n❌ No se encontraron señales que cumplan todos los filtros")
        print("💡 Prueba a reducir los filtros en strategy.py")
    
    mt5.shutdown()

if __name__ == "__main__":
    scan_all()