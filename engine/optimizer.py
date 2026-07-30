"""
Optimizador de parámetros para DELTA ENGINE MT5
Prueba diferentes combinaciones de SL/TP y encuentra la mejor
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import MetaTrader5 as mt5
from engine.backtest_engine import BacktestEngine
from utils.logger import get_logger

logger = get_logger(__name__)


class Optimizer:
    """Optimizador de parámetros"""
    
    def __init__(self, symbol: str = 'AAPL', start_date: str = '2025-01-01', end_date: str = '2026-07-28'):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.results = []
        self.best_result = None
    
    def run(self):
        """Ejecuta la optimización"""
        print("\n" + "="*70)
        print(f"🚀 OPTIMIZANDO PARÁMETROS PARA {self.symbol}")
        print("="*70)
        
        # 🔥 RANGOS DE PARÁMETROS A PROBAR
        sl_multipliers = [1.5, 2.0, 2.5, 3.0]
        tp_multipliers = [2.5, 3.0, 4.0, 5.0]
        risk_percents = [0.5, 1.0, 1.5, 2.0]
        
        total_combinations = len(sl_multipliers) * len(tp_multipliers) * len(risk_percents)
        print(f"📊 Probando {total_combinations} combinaciones...\n")
        
        count = 0
        for sl_mult in sl_multipliers:
            for tp_mult in tp_multipliers:
                for risk_pct in risk_percents:
                    count += 1
                    
                    # 🔥 EJECUTAR BACKTEST CON ESTOS PARÁMETROS
                    backtest = BacktestEngine(initial_balance=10000.0)
                    
                    # Modificar parámetros dinámicamente
                    backtest.sl_multiplier = sl_mult
                    backtest.tp_multiplier = tp_mult
                    backtest.risk_percent = risk_pct / 100
                    
                    # Ejecutar backtest (sin logs para velocidad)
                    result = self._run_silent(backtest)
                    
                    # Guardar resultado
                    result['sl_mult'] = sl_mult
                    result['tp_mult'] = tp_mult
                    result['risk_pct'] = risk_pct
                    self.results.append(result)
                    
                    print(f"  {count}/{total_combinations} | SL={sl_mult}x | TP={tp_mult}x | Riesgo={risk_pct}% | Retorno: {result['return']:.2f}%")
        
        # 🔥 ENCONTRAR LA MEJOR COMBINACIÓN
        self.best_result = max(self.results, key=lambda x: x['return'])
        
        self.print_best()
        self.save_results()
        
        return self.best_result
    
    def _run_silent(self, backtest):
        """Ejecuta backtest sin logs para optimización"""
        try:
            # Guardar logs originales
            import logging
            original_level = logging.getLogger().level
            logging.getLogger().setLevel(logging.ERROR)
            
            # Modificar parámetros
            backtest.sl_multiplier = getattr(backtest, 'sl_multiplier', 1.5)
            backtest.tp_multiplier = getattr(backtest, 'tp_multiplier', 2.5)
            backtest.risk_percent = getattr(backtest, 'risk_percent', 0.02)
            
            # Ejecutar backtest
            backtest.run(self.symbol, self.start_date, self.end_date, 'H1')
            
            # Restaurar logs
            logging.getLogger().setLevel(original_level)
            
            # Devolver métricas
            return {
                'return': ((backtest.balance - backtest.initial_balance) / backtest.initial_balance) * 100,
                'final_balance': backtest.balance,
                'total_trades': len(backtest.trades),
                'win_rate': len([t for t in backtest.trades if t.get('pnl', 0) > 0]) / len(backtest.trades) * 100 if backtest.trades else 0,
                'profit_factor': self._calc_profit_factor(backtest.trades),
                'max_drawdown': getattr(backtest, 'max_drawdown', 0)
            }
        except Exception as e:
            return {
                'return': -100,
                'final_balance': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 100
            }
    
    def _calc_profit_factor(self, trades):
        """Calcula el factor de beneficio"""
        if not trades:
            return 0
        total_win = sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0])
        total_loss = abs(sum([t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]))
        return total_win / total_loss if total_loss > 0 else 0
    
    def print_best(self):
        """Imprime la mejor combinación"""
        if not self.best_result:
            return
        
        print("\n" + "="*70)
        print("🏆 MEJOR COMBINACIÓN ENCONTRADA")
        print("="*70)
        print(f"📊 Símbolo: {self.symbol}")
        print(f"📈 Retorno: {self.best_result['return']:.2f}%")
        print(f"💰 Balance final: ${self.best_result['final_balance']:,.2f}")
        print(f"📊 Trades: {self.best_result['total_trades']}")
        print(f"🎯 Win Rate: {self.best_result['win_rate']:.1f}%")
        print(f"📊 Factor de beneficio: {self.best_result['profit_factor']:.2f}")
        print(f"📉 Max Drawdown: {self.best_result['max_drawdown']:.1f}%")
        print("-"*70)
        print(f"🔧 SL: {self.best_result['sl_mult']}x ATR")
        print(f"🔧 TP: {self.best_result['tp_mult']}x ATR")
        print(f"🔧 Riesgo: {self.best_result['risk_pct']}% por trade")
        print("="*70)
    
    def save_results(self):
        """Guarda los resultados en CSV"""
        try:
            df = pd.DataFrame(self.results)
            df.to_csv(f"optimization_results_{self.symbol}.csv", index=False)
            print(f"\n💾 Resultados guardados en: optimization_results_{self.symbol}.csv")
        except Exception as e:
            print(f"⚠️ Error guardando resultados: {e}")


def main():
    """Función principal de optimización"""
    print("\n" + "="*70)
    print("🚀 OPTIMIZADOR DE PARÁMETROS")
    print("="*70)
    print("Este proceso probará diferentes combinaciones de SL/TP y riesgo")
    print("Puede tomar varios minutos...")
    
    # Optimizar para AAPL
    optimizer = Optimizer('AAPL', '2025-01-01', '2026-07-28')
    best = optimizer.run()
    
    # Optimizar para GOOG
    print("\n" + "-"*70)
    optimizer2 = Optimizer('GOOG', '2025-01-01', '2026-07-28')
    best2 = optimizer2.run()
    
    # Optimizar para MSFT
    print("\n" + "-"*70)
    optimizer3 = Optimizer('MSFT', '2025-01-01', '2026-07-28')
    best3 = optimizer3.run()
    
    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN DE OPTIMIZACIÓN")
    print("="*70)
    print(f"📈 AAPL: SL={best['sl_mult']}x | TP={best['tp_mult']}x | Riesgo={best['risk_pct']}% | Retorno={best['return']:.2f}%")
    print(f"📈 GOOG: SL={best2['sl_mult']}x | TP={best2['tp_mult']}x | Riesgo={best2['risk_pct']}% | Retorno={best2['return']:.2f}%")
    print(f"📈 MSFT: SL={best3['sl_mult']}x | TP={best3['tp_mult']}x | Riesgo={best3['risk_pct']}% | Retorno={best3['return']:.2f}%")
    print("="*70)


if __name__ == "__main__":
    main()