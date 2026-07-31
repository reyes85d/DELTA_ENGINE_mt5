"""
Motor de Backtesting para DELTA ENGINE MT5 - VERSIÓN CON CONFIG
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt

# 🔥 IMPORTAR CONFIGURACIÓN COMPLETA
from config import (
    ATR_MULTIPLIER_SL,
    ATR_MULTIPLIER_TP,
    ACCOUNT_SIZE,
    RISK_PER_TRADE,
    MIN_SCORE,
    STOCKS,
    FOREX,
    DEFAULT_QTY_STOCK,
    DEFAULT_QTY_FOREX,
    COOLDOWN_MINUTES,
    MAX_POSITIONS,
    SCAN_INTERVAL
)

from strategies.strategy import Strategy
from utils.logger import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """Motor de backtesting mejorado con métricas avanzadas"""
    
    def __init__(self, initial_balance: float = ACCOUNT_SIZE):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.equity_curve = []
        self.max_drawdown = 0
        self.peak_balance = initial_balance
        
        # 🔥 PARÁMETROS DE CONFIG
        self.sl_multiplier = ATR_MULTIPLIER_SL
        self.tp_multiplier = ATR_MULTIPLIER_TP
        self.risk_percent = RISK_PER_TRADE / 100 if RISK_PER_TRADE < 1 else 0.01
        self.min_score = MIN_SCORE
        
        # 🔥 ESTADÍSTICAS AVANZADAS
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        self.best_trade = 0
        self.worst_trade = 0
        
        # 🔥 SEGUIMIENTO DE DRAWDOWN
        self.drawdown_history = []
        self.max_drawdown_pct = 0
        
        # 🔥 SÍMBOLOS FOREX (para cálculos de lote)
        self.forex_symbols = FOREX
        
        logger.info(f"✅ BacktestEngine inicializado: Balance=${initial_balance:.2f}")
        logger.info(f"📊 Símbolos disponibles: {len(STOCKS)} acciones, {len(FOREX)} forex")
    
    def run(self, symbol: str, start_date: str, end_date: str, 
            timeframe: str = 'H1', use_ai: bool = True) -> Dict:
        """
        Ejecuta backtest para un símbolo
        
        Args:
            symbol: Símbolo a testear
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1, W1)
            use_ai: Usar IA o solo reglas
        
        Returns:
            Dict con resultados
        """
        # Conectar a MT5
        if not mt5.initialize():
            logger.error("❌ Error inicializando MT5")
            return {}
        
        logger.info(f"📊 Backtesting {symbol} desde {start_date} hasta {end_date} ({timeframe})")
        
        # Obtener datos históricos
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        rates = mt5.copy_rates_range(
            symbol, 
            self._get_timeframe(timeframe),
            start_dt,
            end_dt
        )
        
        if rates is None or len(rates) == 0:
            logger.error(f"❌ No hay datos para {symbol}")
            mt5.shutdown()
            return {}
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # 🔥 INICIALIZAR ESTRATEGIA
        strategy = Strategy()
        
        # 🔥 ESTADO DEL BACKTEST
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        entry_time = None
        lot_size = 0
        position_type = None
        
        trades = []
        equity_curve = [self.initial_balance]
        timestamps = [df.iloc[0]['time']]
        
        logger.info(f"📈 {len(df)} velas analizadas")
        
        # 🔥 BUCLE PRINCIPAL
        for i in range(200, len(df) - 5):
            data = df.iloc[:i+1]
            current_price = df.iloc[i]['close']
            current_time = df.iloc[i]['time']
            
            # 🔥 ACTUALIZAR EQUITY SI HAY POSICIÓN
            if position != 0:
                if symbol in self.forex_symbols:
                    multiplier = 100000 * lot_size
                else:
                    multiplier = lot_size
                
                if position == 1:
                    unrealized_pnl = (current_price - entry_price) * multiplier
                else:
                    unrealized_pnl = (entry_price - current_price) * multiplier
                
                current_equity = self.balance + unrealized_pnl
                equity_curve.append(current_equity)
                timestamps.append(current_time)
            
            # 🔥 ANALIZAR SEÑAL
            signal = strategy.analyze_symbol_with_data(symbol, data)
            
            # 🔥 SI HAY SEÑAL Y NO TENEMOS POSICIÓN
            if signal and position == 0:
                action = signal['action']
                score = signal.get('score', 0)
                
                # Verificar si cumple con el score mínimo
                if score < self.min_score:
                    continue
                
                atr = signal.get('atr', 0.001)
                price = signal['price']
                
                # 🔥 CALCULAR ENTRY, SL, TP
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
                
                if symbol in self.forex_symbols:
                    lot_size = risk_amount / (risk_in_points * 10) if risk_in_points > 0 else 0.01
                    lot_size = max(0.01, min(lot_size, 0.1))
                    lot_size = round(lot_size, 2)
                else:
                    lot_size = risk_amount / (risk_in_points * 1) if risk_in_points > 0 else 1
                    lot_size = max(1, min(lot_size, 50))
                    lot_size = int(round(lot_size, 0))
                
                # 🔥 VERIFICAR DRAWDOWN MÁXIMO
                if self.max_drawdown_pct > 20:
                    logger.warning(f"⚠️ Drawdown máximo alcanzado ({self.max_drawdown_pct:.1f}%)")
                    break
                
                # 🔥 ABRIR POSICIÓN
                position = 1 if action == 'BUY' else -1
                entry_price = entry
                stop_loss = sl
                take_profit = tp
                entry_time = current_time
                position_type = action
                
                trade = {
                    'symbol': symbol,
                    'action': action,
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                    'lot_size': lot_size,
                    'entry_time': current_time,
                    'score': score,
                    'status': 'open'
                }
                trades.append(trade)
                
                logger.debug(f"🔹 {action} en {symbol} @ {entry:.5f} | SL: {sl:.5f} | TP: {tp:.5f} | Lote: {lot_size}")
            
            # 🔥 GESTIONAR POSICIÓN ABIERTA
            elif position != 0:
                trade = trades[-1]
                
                if symbol in self.forex_symbols:
                    multiplier = 100000 * lot_size
                else:
                    multiplier = lot_size
                
                hit_sl = False
                hit_tp = False
                exit_price = 0
                
                if position == 1:
                    if current_price <= stop_loss:
                        hit_sl = True
                        exit_price = stop_loss
                    elif current_price >= take_profit:
                        hit_tp = True
                        exit_price = take_profit
                else:
                    if current_price >= stop_loss:
                        hit_sl = True
                        exit_price = stop_loss
                    elif current_price <= take_profit:
                        hit_tp = True
                        exit_price = take_profit
                
                if hit_sl or hit_tp:
                    if position == 1:
                        pnl = (exit_price - entry_price) * multiplier
                    else:
                        pnl = (entry_price - exit_price) * multiplier
                    
                    self.balance += pnl
                    self.total_pnl += pnl
                    
                    trade['exit'] = exit_price
                    trade['exit_time'] = current_time
                    trade['pnl'] = pnl
                    trade['status'] = 'closed'
                    
                    if pnl > 0:
                        self.winning_trades += 1
                        if pnl > self.best_trade:
                            self.best_trade = pnl
                    else:
                        self.losing_trades += 1
                        if pnl < self.worst_trade:
                            self.worst_trade = pnl
                    
                    logger.debug(f"{'🟢 TP' if hit_tp else '🔴 SL'} en {symbol} @ {exit_price:.5f} | P&L: ${pnl:.2f}")
                    
                    position = 0
                    entry_price = 0
                    stop_loss = 0
                    take_profit = 0
                    
                    equity_curve.append(self.balance)
                    timestamps.append(current_time)
                    
                    self._update_drawdown()
        
        # 🔥 CERRAR POSICIÓN ABIERTA AL FINAL
        if position != 0:
            final_price = df.iloc[-1]['close']
            
            if symbol in self.forex_symbols:
                multiplier = 100000 * lot_size
            else:
                multiplier = lot_size
            
            if position == 1:
                pnl = (final_price - entry_price) * multiplier
            else:
                pnl = (entry_price - final_price) * multiplier
            
            self.balance += pnl
            trades[-1]['exit'] = final_price
            trades[-1]['exit_time'] = df.iloc[-1]['time']
            trades[-1]['pnl'] = pnl
            trades[-1]['status'] = 'close'
            position = 0
        
        # 🔥 GUARDAR RESULTADOS
        self.trades = trades
        self.equity_curve = equity_curve
        
        results = self.print_results(symbol)
        
        mt5.shutdown()
        return results
    
    def _get_timeframe(self, tf: str):
        """Convierte string a timeframe MT5"""
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1,
        }
        return timeframe_map.get(tf, mt5.TIMEFRAME_H1)
    
    def _update_drawdown(self):
        """Actualiza el drawdown máximo"""
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        
        drawdown = (self.peak_balance - self.balance) / self.peak_balance * 100
        if drawdown > self.max_drawdown_pct:
            self.max_drawdown_pct = drawdown
        
        self.drawdown_history.append({
            'timestamp': datetime.now(),
            'drawdown': drawdown,
            'balance': self.balance
        })
    
    def print_results(self, symbol: str) -> Dict:
        """Imprime resultados detallados del backtest"""
        if not self.trades:
            print("📭 No hay trades")
            return {}
        
        closed_trades = [t for t in self.trades if t.get('status') in ['closed', 'close']]
        total_closed = len(closed_trades)
        
        if total_closed == 0:
            print("📭 No hay trades cerrados")
            return {}
        
        winning_trades = len([t for t in closed_trades if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in closed_trades if t.get('pnl', 0) < 0])
        
        total_pnl = sum([t.get('pnl', 0) for t in closed_trades])
        
        total_win = sum([t.get('pnl', 0) for t in closed_trades if t.get('pnl', 0) > 0])
        total_loss = abs(sum([t.get('pnl', 0) for t in closed_trades if t.get('pnl', 0) < 0]))
        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')
        
        win_rate = winning_trades / total_closed if total_closed > 0 else 0
        
        avg_win = total_win / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        returns = [t.get('pnl', 0) for t in closed_trades]
        sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        print("\n" + "="*70)
        print(f"📊 RESULTADOS BACKTEST - {symbol}")
        print("="*70)
        print(f"💰 Balance inicial: ${self.initial_balance:,.2f}")
        print(f"💰 Balance final: ${self.balance:,.2f}")
        print(f"📈 Retorno total: {((self.balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        print(f"📈 Ganancia: ${self.balance - self.initial_balance:,.2f}")
        print("-"*70)
        print(f"📊 Trades totales: {len(self.trades)}")
        print(f"📊 Trades cerrados: {total_closed}")
        print(f"🟢 Ganadores: {winning_trades} ({win_rate:.1%})")
        print(f"🔴 Perdedores: {losing_trades} ({1-win_rate:.1%})")
        print("-"*70)
        print(f"💰 P&L total: ${total_pnl:,.2f}")
        print(f"📈 Ganancia media: ${avg_win:,.2f}")
        print(f"📉 Pérdida media: ${avg_loss:,.2f}")
        print(f"📊 Factor de beneficio: {profit_factor:.2f}")
        print(f"🎯 Expectativa: ${expectancy:,.2f} por trade")
        print(f"📊 Sharpe Ratio: {sharpe:.2f}")
        print("-"*70)
        print(f"🏆 Mejor trade: ${self.best_trade:,.2f}")
        print(f"💀 Peor trade: ${self.worst_trade:,.2f}")
        print(f"📉 Max Drawdown: {self.max_drawdown_pct:.1f}%")
        print("="*70)
        
        return {
            'symbol': symbol,
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'return_pct': ((self.balance - self.initial_balance) / self.initial_balance * 100),
            'total_trades': len(self.trades),
            'closed_trades': total_closed,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'sharpe_ratio': sharpe,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade,
            'max_drawdown': self.max_drawdown_pct
        }
    
    def plot_equity_curve(self, symbol: str):
        """Grafica la curva de equity"""
        if not self.equity_curve:
            print("📭 No hay datos de equity para graficar")
            return
        
        try:
            plt.figure(figsize=(12, 6))
            plt.plot(self.equity_curve, color='blue', linewidth=1.5)
            plt.axhline(y=self.initial_balance, color='gray', linestyle='--', alpha=0.5)
            plt.title(f'Curva de Equity - {symbol}')
            plt.xlabel('Tiempo')
            plt.ylabel('Balance ($)')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f'{symbol}_equity_curve.png')
            plt.close()
            logger.info(f"✅ Gráfico guardado: {symbol}_equity_curve.png")
        except Exception as e:
            logger.error(f"Error generando gráfico: {e}")


def run_backtest():
    """Ejecuta backtest para todos los símbolos de config.py"""
    print("\n" + "="*70)
    print("🚀 INICIANDO BACKTEST CON SÍMBOLOS DE CONFIG")
    print("="*70)
    
    # 🔥 OBTENER SÍMBOLOS DE CONFIG
    symbols = STOCKS + FOREX
    
    # 🔥 FILTRAR SÍMBOLOS QUE EXISTEN EN MT5
    valid_symbols = []
    mt5.initialize()
    for symbol in symbols:
        info = mt5.symbol_info(symbol)
        if info is not None:
            valid_symbols.append(symbol)
        else:
            logger.warning(f"⚠️ {symbol} no disponible en MT5, omitiendo...")
    mt5.shutdown()
    
    print(f"📊 Símbolos configurados: {len(symbols)}")
    print(f"📊 Símbolos disponibles: {len(valid_symbols)}")
    print(f"📊 Símbolos a testear: {valid_symbols[:10]}..." if len(valid_symbols) > 10 else valid_symbols)
    print("="*70 + "\n")
    
    all_results = []
    
    for i, symbol in enumerate(valid_symbols, 1):
        print(f"\n{'#'*70}")
        print(f"📊 [{i}/{len(valid_symbols)}] ANALIZANDO {symbol}")
        print("="*70)
        
        try:
            backtest = BacktestEngine(initial_balance=10000.0)
            results = backtest.run(symbol, '2025-01-01', '2026-07-28', 'M15')
            
            if results:
                all_results.append(results)
                backtest.plot_equity_curve(symbol)
                
        except Exception as e:
            logger.error(f"❌ Error en backtest de {symbol}: {e}")
    
    # 🔥 RESUMEN COMPARATIVO
    if all_results:
        print("\n" + "="*70)
        print("📊 RESUMEN COMPARATIVO DE SÍMBOLOS")
        print("="*70)
        
        df_results = pd.DataFrame(all_results)
        df_results = df_results.sort_values('return_pct', ascending=False)
        
        print("\n🏆 RANKING POR RETORNO:")
        for i, row in df_results.iterrows():
            emoji = "🟢" if row['return_pct'] > 0 else "🔴"
            print(f"  {emoji} {row['symbol']}: {row['return_pct']:.2f}% | Win Rate: {row['win_rate']:.1%} | PF: {row['profit_factor']:.2f} | DD: {row['max_drawdown']:.1f}%")
        
        # Guardar resultados
        df_results.to_csv('backtest_results_completo.csv', index=False)
        print(f"\n✅ Resultados guardados en: backtest_results_completo.csv")
        
        # Mostrar top 5
        print("\n🥇 TOP 5 MEJORES SÍMBOLOS:")
        for i, row in df_results.head(5).iterrows():
            print(f"  {i+1}. {row['symbol']}: {row['return_pct']:.2f}% (Win Rate: {row['win_rate']:.1%})")
        
        print("\n🥉 TOP 5 PEORES SÍMBOLOS:")
        for i, row in df_results.tail(5).iterrows():
            print(f"  {len(df_results)-i}. {row['symbol']}: {row['return_pct']:.2f}% (Win Rate: {row['win_rate']:.1%})")
    
    print("\n" + "="*70)
    print("✅ BACKTEST COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    run_backtest()