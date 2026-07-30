"""
Motor de Backtesting para DELTA ENGINE MT5
"""

import sys
import os
# 🔥 AÑADIR RUTA DEL PROYECTO
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import MetaTrader5 as mt5

# 🔥 IMPORTAR CONFIGURACIÓN
from config import (
    ATR_MULTIPLIER_SL,
    ATR_MULTIPLIER_TP,
    ACCOUNT_SIZE,
    RISK_PER_TRADE,
    MIN_SCORE
)

from strategies.strategy import Strategy
from utils.logger import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """Motor de backtesting"""
    
    def __init__(self, initial_balance: float = ACCOUNT_SIZE):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.equity_curve = []
        self.max_drawdown = 0
        self.peak_balance = initial_balance
        
        # 🔥 USAR PARÁMETROS DE CONFIG
        self.sl_multiplier = ATR_MULTIPLIER_SL
        self.tp_multiplier = ATR_MULTIPLIER_TP
        self.risk_percent = RISK_PER_TRADE / 100
        
    def run(self, symbol: str, start_date: str, end_date: str, timeframe: str = 'H1'):
        """Ejecuta backtest para un símbolo"""
        # Conectar a MT5
        if not mt5.initialize():
            logger.error("❌ Error inicializando MT5")
            return
        
        logger.info(f"📊 Backtesting {symbol} desde {start_date} hasta {end_date}")
        
        # Obtener datos históricos
        rates = mt5.copy_rates_range(
            symbol, 
            self._get_timeframe(timeframe),
            datetime.strptime(start_date, '%Y-%m-%d'),
            datetime.strptime(end_date, '%Y-%m-%d')
        )
        
        if rates is None or len(rates) == 0:
            logger.error(f"❌ No hay datos para {symbol}")
            mt5.shutdown()
            return
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Inicializar estrategia
        strategy = Strategy()
        
        # Variables de estado
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        
        trades = []
        equity = [self.initial_balance]
        
        logger.info(f"📊 {len(df)} velas analizadas")
        
        # 🔥 LISTA DE SÍMBOLOS FOREX
        forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
        
        for i in range(200, len(df) - 5):
            data = df.iloc[:i]
            
            # Analizar con la estrategia
            signal = strategy.analyze_symbol_with_data(symbol, data)
            
            current_price = df.iloc[i]['close']
            
            # Si hay señal y no tenemos posición
            if signal and position == 0:
                action = signal['action']
                price = signal['price']
                atr = signal.get('atr', 0.001)
                
                # 🔥 USAR PARÁMETROS DE CONFIG
                if action == 'BUY':
                    entry = current_price
                    sl = entry - (atr * self.sl_multiplier)
                    tp = entry + (atr * self.tp_multiplier)
                else:
                    entry = current_price
                    sl = entry + (atr * self.sl_multiplier)
                    tp = entry - (atr * self.tp_multiplier)
                
                # 🔥 CALCULAR LOTE REALISTA
                risk_amount = self.balance * self.risk_percent
                risk_in_points = abs(entry - sl)
                
                if symbol in forex_symbols:
                    # Forex: 1 lote = 100,000 unidades, 1 punto = 0.0001
                    # Valor de 1 punto por lote = $10
                    lot_size = risk_amount / (risk_in_points * 10) if risk_in_points > 0 else 0.01
                    lot_size = max(0.01, min(lot_size, 0.1))  # 🔥 Entre 0.01 y 0.1 lotes
                else:
                    # Acciones: 1 acción = 1 unidad
                    lot_size = risk_amount / (risk_in_points * 1) if risk_in_points > 0 else 1
                    lot_size = max(5, min(lot_size, 25))  # 🔥 Entre 1 y 10 acciones
                    lot_size = round(lot_size, 0)  # 🔥 Acciones enteras
                
                # Si el drawdown > 20%, cerrar todo
                if (self.initial_balance - self.balance) / self.initial_balance > 0.20:
                    logger.warning("⚠️ Drawdown máximo alcanzado (20%)")
                    break
                
                # Redondear lote
                if symbol in forex_symbols:
                    lot_size = round(lot_size, 2)
                else:
                    lot_size = int(lot_size)
                
                position = 1 if action == 'BUY' else -1
                entry_price = entry
                stop_loss = sl
                take_profit = tp
                
                trades.append({
                    'date': df.iloc[i]['time'],
                    'action': action,
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                    'status': 'open',
                    'lot_size': lot_size,
                    'commission': 0
                })
                
                logger.info(f"🔹 {action} en {symbol} @ {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f} | Lote: {lot_size}")
            
            # Verificar SL/TP
            elif position != 0:
                # 🔥 MULTIPLICADOR SEGÚN ACTIVO
                if symbol in forex_symbols:
                    multiplier = 100000 * lot_size  # Forex
                else:
                    multiplier = lot_size  # Acciones
                
                if position == 1:  # BUY
                    if current_price <= stop_loss:
                        pnl = (stop_loss - entry_price) * multiplier
                        self.balance += pnl
                        trades[-1]['status'] = 'SL'
                        trades[-1]['exit'] = stop_loss
                        trades[-1]['pnl'] = pnl
                        position = 0
                        logger.info(f"🔴 SL en {symbol} @ {stop_loss:.2f} | P&L: ${pnl:.2f}")
                    
                    elif current_price >= take_profit:
                        pnl = (take_profit - entry_price) * multiplier
                        self.balance += pnl
                        trades[-1]['status'] = 'TP'
                        trades[-1]['exit'] = take_profit
                        trades[-1]['pnl'] = pnl
                        position = 0
                        logger.info(f"🟢 TP en {symbol} @ {take_profit:.2f} | P&L: ${pnl:.2f}")
                
                else:  # SELL
                    if current_price >= stop_loss:
                        pnl = (entry_price - stop_loss) * multiplier
                        self.balance += pnl
                        trades[-1]['status'] = 'SL'
                        trades[-1]['exit'] = stop_loss
                        trades[-1]['pnl'] = pnl
                        position = 0
                        logger.info(f"🔴 SL en {symbol} @ {stop_loss:.2f} | P&L: ${pnl:.2f}")
                    
                    elif current_price <= take_profit:
                        pnl = (entry_price - take_profit) * multiplier
                        self.balance += pnl
                        trades[-1]['status'] = 'TP'
                        trades[-1]['exit'] = take_profit
                        trades[-1]['pnl'] = pnl
                        position = 0
                        logger.info(f"🟢 TP en {symbol} @ {take_profit:.2f} | P&L: ${pnl:.2f}")
            
            # Registrar equity
            equity.append(self.balance)
            
            # Calcular drawdown
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            current_drawdown = (self.peak_balance - self.balance) / self.peak_balance * 100
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
        
        # Cerrar posición abierta al final
        if position != 0:
            final_price = df.iloc[-1]['close']
            if symbol in forex_symbols:
                multiplier = 100000 * lot_size
            else:
                multiplier = lot_size
            if position == 1:
                pnl = (final_price - entry_price) * multiplier
            else:
                pnl = (entry_price - final_price) * multiplier
            self.balance += pnl
            trades[-1]['status'] = 'close'
            trades[-1]['exit'] = final_price
            trades[-1]['pnl'] = pnl
            position = 0
        
        # Resultados
        self.trades = trades
        self.equity_curve = equity
        self.print_results(symbol)
        
        mt5.shutdown()
    
    def _get_timeframe(self, tf: str):
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1,
        }
        return timeframe_map.get(tf, mt5.TIMEFRAME_H1)
    
    def print_results(self, symbol: str):
        """Imprime los resultados del backtest"""
        if not self.trades:
            print("📭 No hay trades")
            return
        
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in self.trades if t.get('pnl', 0) < 0])
        
        total_pnl = sum([t.get('pnl', 0) for t in self.trades])
        
        print("\n" + "="*60)
        print(f"📊 RESULTADOS BACKTEST - {symbol}")
        print("="*60)
        print(f"💰 Balance inicial: ${self.initial_balance:,.2f}")
        print(f"💰 Balance final: ${self.balance:,.2f}")
        print(f"📈 Retorno total: {((self.balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        print(f"📊 Trades totales: {total_trades}")
        print(f"🟢 Trades ganadores: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        print(f"🔴 Trades perdedores: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
        print(f"💰 P&L total: ${total_pnl:,.2f}")
        
        if winning_trades > 0:
            avg_win = sum([t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0]) / winning_trades
            print(f"📈 Ganancia media: ${avg_win:,.2f}")
        
        if losing_trades > 0:
            avg_loss = sum([t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0]) / losing_trades
            print(f"📉 Pérdida media: ${avg_loss:,.2f}")
        
        total_win = sum([t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) > 0])
        total_loss = abs(sum([t.get('pnl', 0) for t in self.trades if t.get('pnl', 0) < 0]))
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        print(f"📊 Factor de beneficio: {profit_factor:.2f}")
        print(f"📉 Max Drawdown: {self.max_drawdown:.1f}%")
        print("="*60)


def run_backtest():
    """Ejecuta backtest para varios símbolos"""
    print("\n" + "="*60)
    print("🚀 INICIANDO BACKTEST")
    print("="*60)
    
    symbols = [ "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD",  # Mayores
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "AUDNZD",  # Cruces
    "EURAUD", "EURCHF", "GBPAUD", "GBPCAD", "GBPCHF",  # Más cruces
    "CADJPY", "CHFJPY", "NZDJPY", "NZDCAD",]   # Pares con JPY y CAD  # 🔥 Más volátiles
    
    for symbol in symbols:
        backtest = BacktestEngine(initial_balance=10000.0)
        backtest.run(symbol, '2025-01-01', '2026-07-28', 'M15')
        print("\n")

if __name__ == "__main__":
    run_backtest()