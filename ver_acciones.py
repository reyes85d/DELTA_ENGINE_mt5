"""
Ver acciones disponibles en MT5
"""

import MetaTrader5 as mt5

def main():
    if not mt5.initialize():
        print("❌ Error inicializando MT5")
        return
    
    print("✅ Conectado a MT5\n")
    
    stocks = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
        "NFLX", "AMD", "INTC", "PYPL", "UBER", "COIN", "PLTR",
        "JPM", "V", "WMT", "JNJ", "PG", "KO", "PEP", "MCD"
    ]
    
    print("📊 VERIFICANDO ACCIONES:")
    print("=" * 55)
    print(f"{'Símbolo':<10} {'Disponible':<15} {'Precio':<12} {'Spread':<8}")
    print("-" * 55)
    
    disponibles = 0
    for symbol in stocks:
        info = mt5.symbol_info(symbol)
        if info:
            tick = mt5.symbol_info_tick(symbol)
            price = tick.ask if tick else 0
            spread = info.spread if info.spread else 0
            print(f"{symbol:<10} ✅ Disponible   ${price:<11.2f} {spread:<8}")
            disponibles += 1
        else:
            if mt5.symbol_select(symbol, True):
                info = mt5.symbol_info(symbol)
                if info:
                    print(f"{symbol:<10} ✅ Activado     $0.00")
                    disponibles += 1
                else:
                    print(f"{symbol:<10} ❌ No disponible")
            else:
                print(f"{symbol:<10} ❌ No disponible")
    
    print("-" * 55)
    print(f"Total: {disponibles}/{len(stocks)} acciones disponibles")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()