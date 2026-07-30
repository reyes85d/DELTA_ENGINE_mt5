# debug_goog.py - Colocado en C:\Users\Reyes\Desktop\DELTA_ENGINE_MT5\
import sys
import os

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.strategy import Strategy
import MetaTrader5 as mt5

def main():
    print("\n" + "="*60)
    print("🐛 DEBUG DE GOOG")
    print("="*60)
    
    # Inicializar MT5
    if not mt5.initialize():
        print("❌ Error conectando a MT5")
        return
    
    print("✅ Conectado a MT5")
    
    # Crear estrategia
    strategy = Strategy()
    
    # Debug de GOOG
    strategy.debug_symbol('EURUSD')
    
    mt5.shutdown()

if __name__ == "__main__":
    main()