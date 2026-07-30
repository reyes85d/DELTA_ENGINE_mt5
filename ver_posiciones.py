"""
Ver todas las posiciones en MT5
"""

import MetaTrader5 as mt5

def main():
    if not mt5.initialize():
        print("❌ Error inicializando MT5")
        return
    
    print("✅ Conectado a MT5")
    
    # Obtener todas las posiciones
    positions = mt5.positions_get()
    
    if not positions:
        print("📭 No hay posiciones abiertas")
        mt5.shutdown()
        return
    
    print(f"\n📊 TOTAL: {len(positions)} posiciones")
    print("=" * 60)
    print(f"{'Símbolo':<10} {'Tipo':<6} {'Lotes':<8} {'Precio':<12} {'P&L':<10}")
    print("-" * 60)
    
    total_pnl = 0
    for pos in positions:
        pnl = pos.profit
        total_pnl += pnl
        tipo = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
        print(f"{pos.symbol:<10} {tipo:<6} {pos.volume:<8} {pos.price_open:<12.5f} ${pnl:<10.2f}")
    
    print("-" * 60)
    print(f"TOTAL P&L: ${total_pnl:.2f}")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()