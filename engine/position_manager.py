"""
Gestión de posiciones para MT5 - VERSIÓN MEJORADA CON ANÁLISIS AVANZADO
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class PositionManager:
    """Gestor de posiciones avanzado para MT5"""
    
    def __init__(self, engine):
        self.engine = engine
        self._positions = {}
        self._position_history = []
        self._last_sync = None
        self._sync()
        
        # 🔥 CONFIGURACIÓN DE GESTIÓN
        self.trailing_stop_activation = 0.01  # 1% para activar trailing stop
        self.trailing_stop_distance = 0.005   # 0.5% distancia del trailing
        self.breakeven_activation = 0.005     # 0.5% para mover a breakeven
        
        # 🔥 ESTADÍSTICAS
        self.total_pnl = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.best_trade = 0
        self.worst_trade = 0
        
        logger.info("✅ PositionManager inicializado")
    
    # ==========================================================
    # SINCRONIZACIÓN
    # ==========================================================
    
    # En la función _sync(), reemplaza esta sección:

    def _sync(self):
        """Sincroniza TODAS las posiciones existentes"""
        try:
            positions = mt5.positions_get()
            self._positions = {}
            
            if positions:
                for pos in positions:
                    # Calcular métricas adicionales
                    pnl_pct = (pos.profit / (pos.volume * pos.price_open)) * 100 if pos.volume > 0 else 0
                    
                    # 🔥 CONSTRUIR DICCIONARIO CON ATRIBUTOS SEGUROS
                    pos_data = {
                        'symbol': pos.symbol,
                        'ticket': pos.ticket,
                        'qty': pos.volume,
                        'open_price': pos.price_open,
                        'current_price': pos.price_current,
                        'profit': pos.profit,
                        'profit_pct': pnl_pct,
                        'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                        'time': pos.time,
                        'time_open': datetime.fromtimestamp(pos.time),
                    }
                    
                    # 🔥 AÑADIR ATRIBUTOS SOLO SI EXISTEN (usando hasattr)
                    if hasattr(pos, 'swap'):
                        pos_data['swap'] = pos.swap
                    if hasattr(pos, 'commission'):
                        pos_data['commission'] = pos.commission
                    if hasattr(pos, 'sl'):
                        pos_data['sl'] = pos.sl
                    if hasattr(pos, 'tp'):
                        pos_data['tp'] = pos.tp
                    
                    self._positions[pos.symbol] = pos_data
            
            self._last_sync = datetime.now()
            logger.debug(f"✅ {len(self._positions)} posiciones sincronizadas")
                
        except Exception as e:
            logger.error(f"Error sincronizando posiciones: {e}")

    def sync(self):
        """Método público para sincronizar"""
        self._sync()
        return self._positions
    
    def force_sync(self):
        """Fuerza una sincronización completa"""
        self._sync()
        return self._positions
    
    # ==========================================================
    # CONSULTAS DE POSICIONES
    # ==========================================================
    
    def all(self) -> Dict:
        """Devuelve todas las posiciones"""
        self._sync()
        return self._positions
    
    def exists(self, symbol: str) -> bool:
        """Verifica si existe una posición para un símbolo"""
        self._sync()
        return symbol in self._positions
    
    def get(self, symbol: str) -> Optional[Dict]:
        """Obtiene una posición por símbolo"""
        self._sync()
        return self._positions.get(symbol)
    
    def get_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Obtiene una posición por ticket"""
        self._sync()
        for pos in self._positions.values():
            if pos['ticket'] == ticket:
                return pos
        return None
    
    def get_position_count(self) -> int:
        """Obtiene el número total de posiciones"""
        self._sync()
        return len(self._positions)
    
    def get_symbols(self) -> List[str]:
        """Obtiene la lista de símbolos con posiciones abiertas"""
        self._sync()
        return list(self._positions.keys())
    
    def get_open_positions(self) -> List[Dict]:
        """Obtiene todas las posiciones abiertas como lista"""
        self._sync()
        return list(self._positions.values())
    
    # ==========================================================
    # ANÁLISIS DE POSICIONES
    # ==========================================================
    
    def get_total_pnl(self) -> float:
        """Obtiene el P&L total de todas las posiciones"""
        self._sync()
        return sum(pos['profit'] for pos in self._positions.values())
    
    def get_winning_positions(self) -> List[Dict]:
        """Obtiene posiciones ganadoras"""
        self._sync()
        return [pos for pos in self._positions.values() if pos['profit'] > 0]
    
    def get_losing_positions(self) -> List[Dict]:
        """Obtiene posiciones perdedoras"""
        self._sync()
        return [pos for pos in self._positions.values() if pos['profit'] < 0]
    
    def get_best_position(self) -> Optional[Dict]:
        """Obtiene la mejor posición"""
        self._sync()
        if not self._positions:
            return None
        return max(self._positions.values(), key=lambda x: x['profit'])
    
    def get_worst_position(self) -> Optional[Dict]:
        """Obtiene la peor posición"""
        self._sync()
        if not self._positions:
            return None
        return min(self._positions.values(), key=lambda x: x['profit'])
    
    def get_positions_by_symbol_type(self, symbol: str, position_type: str) -> List[Dict]:
        """Obtiene posiciones por símbolo y tipo"""
        self._sync()
        return [pos for pos in self._positions.values() 
                if pos['symbol'] == symbol and pos['type'] == position_type]
    
    # ==========================================================
    # GESTIÓN DE POSICIONES
    # ==========================================================
    
    def close_position(self, symbol: str, qty: float = None) -> bool:
        """
        Cierra una posición total o parcialmente
        
        Args:
            symbol: Símbolo
            qty: Cantidad a cerrar (None = cerrar todo)
        """
        try:
            self._sync()
            pos = self._positions.get(symbol)
            if pos is None:
                logger.warning(f"No hay posición en {symbol}")
                return False
            
            close_qty = qty if qty is not None else pos['qty']
            
            # Verificar que no se cierre más de lo que se tiene
            if close_qty > pos['qty']:
                logger.warning(f"Cantidad a cerrar ({close_qty}) > posición ({pos['qty']})")
                close_qty = pos['qty']
            
            # Determinar tipo de orden de cierre
            order_type = mt5.ORDER_TYPE_SELL if pos['type'] == 'BUY' else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": close_qty,
                "type": order_type,
                "position": pos['ticket'],
                "deviation": 20,
                "magic": 123456,
                "comment": "Delta Engine MT5 - Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Error cerrando {symbol}: {result.comment} (código: {result.retcode})")
                return False
            
            # Registrar cierre
            logger.info(f"✅ Posición cerrada: {symbol} {close_qty} @ {result.price:.5f}")
            
            # Si se cerró todo, actualizar estadísticas
            if close_qty == pos['qty']:
                self._update_trade_stats(pos, result)
            
            self._sync()
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición {symbol}: {e}")
            return False
    
    def modify_position(self, symbol: str, sl: float = None, tp: float = None) -> bool:
        """
        Modifica SL/TP de una posición
        
        Args:
            symbol: Símbolo
            sl: Nuevo Stop Loss (None = no cambiar)
            tp: Nuevo Take Profit (None = no cambiar)
        """
        try:
            self._sync()
            pos = self._positions.get(symbol)
            if pos is None:
                logger.warning(f"No hay posición en {symbol}")
                return False
            
            # Preparar modificación
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos['ticket'],
            }
            
            if sl is not None:
                request["sl"] = float(sl)
            if tp is not None:
                request["tp"] = float(tp)
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Error modificando {symbol}: {result.comment}")
                return False
            
            logger.info(f"✅ Posición modificada: {symbol}")
            if sl is not None:
                logger.info(f"   Nuevo SL: {sl:.5f}")
            if tp is not None:
                logger.info(f"   Nuevo TP: {tp:.5f}")
            
            self._sync()
            return True
            
        except Exception as e:
            logger.error(f"Error modificando posición {symbol}: {e}")
            return False
    
    # ==========================================================
    # GESTIÓN AVANZADA DE POSICIONES
    # ==========================================================
    
    def apply_trailing_stop(self, symbol: str) -> bool:
        """
        Aplica trailing stop a una posición
        
        Args:
            symbol: Símbolo
        """
        try:
            self._sync()
            pos = self._positions.get(symbol)
            if pos is None:
                return False
            
            current_price = pos['current_price']
            open_price = pos['open_price']
            profit_pct = pos['profit_pct']
            
            # Solo aplicar trailing si estamos en ganancia suficiente
            if abs(profit_pct) < self.trailing_stop_activation * 100:
                return False
            
            # Calcular nuevo SL
            if pos['type'] == 'BUY':
                new_sl = current_price * (1 - self.trailing_stop_distance)
                # Solo mover SL hacia arriba
                if new_sl <= pos['sl']:
                    return False
            else:  # SELL
                new_sl = current_price * (1 + self.trailing_stop_distance)
                # Solo mover SL hacia abajo
                if new_sl >= pos['sl']:
                    return False
            
            return self.modify_position(symbol, sl=new_sl)
            
        except Exception as e:
            logger.error(f"Error aplicando trailing stop: {e}")
            return False
    
    def apply_breakeven_stop(self, symbol: str) -> bool:
        """
        Mueve el SL a breakeven (precio de entrada)
        
        Args:
            symbol: Símbolo
        """
        try:
            self._sync()
            pos = self._positions.get(symbol)
            if pos is None:
                return False
            
            profit_pct = pos['profit_pct']
            
            # Solo mover a breakeven si estamos en ganancia suficiente
            if abs(profit_pct) < self.breakeven_activation * 100:
                return False
            
            # Mover SL al precio de entrada
            if pos['type'] == 'BUY':
                new_sl = pos['open_price']
                # Solo si el nuevo SL es mayor que el actual
                if new_sl <= pos['sl']:
                    return False
            else:  # SELL
                new_sl = pos['open_price']
                # Solo si el nuevo SL es menor que el actual
                if new_sl >= pos['sl']:
                    return False
            
            return self.modify_position(symbol, sl=new_sl)
            
        except Exception as e:
            logger.error(f"Error aplicando breakeven: {e}")
            return False
    
    def apply_take_profit_partial(self, symbol: str, pct_to_close: float) -> bool:
        """
        Cierra parcialmente una posición
        
        Args:
            symbol: Símbolo
            pct_to_close: Porcentaje a cerrar (0-1)
        """
        try:
            self._sync()
            pos = self._positions.get(symbol)
            if pos is None:
                return False
            
            qty_to_close = pos['qty'] * pct_to_close
            if qty_to_close < 0.01:  # Mínimo para cerrar
                return False
            
            return self.close_position(symbol, qty_to_close)
            
        except Exception as e:
            logger.error(f"Error cerrando parcialmente: {e}")
            return False
    
    # ==========================================================
    # GESTIÓN MASIVA DE POSICIONES
    # ==========================================================
    
    def close_all(self) -> int:
        """Cierra todas las posiciones"""
        self._sync()
        if not self._positions:
            logger.info("📭 No hay posiciones para cerrar")
            return 0
        
        closed = 0
        for symbol in list(self._positions.keys()):
            if self.close_position(symbol):
                closed += 1
        
        logger.info(f"✅ Cerradas {closed} posiciones")
        return closed
    
    def close_all_winning(self) -> int:
        """Cierra todas las posiciones ganadoras"""
        self._sync()
        winning = self.get_winning_positions()
        
        closed = 0
        for pos in winning:
            if self.close_position(pos['symbol']):
                closed += 1
        
        logger.info(f"✅ Cerradas {closed} posiciones ganadoras")
        return closed
    
    def close_all_losing(self) -> int:
        """Cierra todas las posiciones perdedoras"""
        self._sync()
        losing = self.get_losing_positions()
        
        closed = 0
        for pos in losing:
            if self.close_position(pos['symbol']):
                closed += 1
        
        logger.info(f"✅ Cerradas {closed} posiciones perdedoras")
        return closed
    
    # ==========================================================
    # ESTADÍSTICAS Y REPORTES
    # ==========================================================
    
    def _update_trade_stats(self, pos: Dict, result):
        """Actualiza estadísticas al cerrar una posición"""
        pnl = pos['profit']
        
        self.total_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1
            if pnl > self.best_trade:
                self.best_trade = pnl
        else:
            self.losing_trades += 1
            if pnl < self.worst_trade:
                self.worst_trade = pnl
        
        # Guardar historial
        self._position_history.append({
            'symbol': pos['symbol'],
            'type': pos['type'],
            'qty': pos['qty'],
            'open_price': pos['open_price'],
            'close_price': result.price,
            'pnl': pnl,
            'pnl_pct': pos['profit_pct'],
            'open_time': pos['time_open'],
            'close_time': datetime.now(),
            'duration': datetime.now() - pos['time_open']
        })
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de posiciones"""
        self._sync()
        
        total_positions = len(self._positions)
        total_pnl = self.get_total_pnl()
        
        # Calcular métricas de posiciones abiertas
        if total_positions > 0:
            avg_pnl = total_pnl / total_positions
            winning = len([p for p in self._positions.values() if p['profit'] > 0])
            losing = len([p for p in self._positions.values() if p['profit'] < 0])
            win_rate = winning / total_positions if total_positions > 0 else 0
        else:
            avg_pnl = 0
            winning = 0
            losing = 0
            win_rate = 0
        
        # Estadísticas históricas
        total_closed = len(self._position_history)
        if total_closed > 0:
            closed_pnl = sum(p['pnl'] for p in self._position_history)
            closed_winning = len([p for p in self._position_history if p['pnl'] > 0])
            closed_win_rate = closed_winning / total_closed if total_closed > 0 else 0
        else:
            closed_pnl = 0
            closed_win_rate = 0
        
        return {
            'open_positions': total_positions,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'winning': winning,
            'losing': losing,
            'win_rate': win_rate,
            'closed_positions': total_closed,
            'closed_pnl': closed_pnl,
            'closed_win_rate': closed_win_rate,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade
        }
    
    def print_summary(self):
        """Imprime un resumen de TODAS las posiciones"""
        self._sync()
        
        if not self._positions:
            logger.info("📭 No hay posiciones abiertas")
            return
        
        # Calcular totales
        total_pnl = 0
        winning = 0
        losing = 0
        
        logger.info(f"💰 POSICIONES ({len(self._positions)}):")
        for symbol, pos in self._positions.items():
            pnl = pos.get('profit', 0)
            total_pnl += pnl
            
            if pnl > 0:
                winning += 1
            elif pnl < 0:
                losing += 1
            
            emoji = "🟢" if pnl > 0 else "🔴"
            pnl_pct = pos.get('profit_pct', 0)
            
            # Mostrar tiempo abierto
            time_open = pos.get('time_open')
            if time_open:
                duration = datetime.now() - time_open
                hours = duration.total_seconds() / 3600
                time_str = f"{hours:.1f}h"
            else:
                time_str = "N/A"
            
            logger.info(f"  {emoji} {symbol}: {pos['qty']} @ {pos['open_price']:.5f} | "
                       f"P&L: ${pnl:.2f} ({pnl_pct:.2f}%) | {time_str}")
            
            # Mostrar SL/TP si existen
            if pos.get('sl') and pos['sl'] > 0:
                logger.info(f"      SL: {pos['sl']:.5f}")
            if pos.get('tp') and pos['tp'] > 0:
                logger.info(f"      TP: {pos['tp']:.5f}")
        
        # Resumen
        emoji_total = "🟢" if total_pnl > 0 else "🔴"
        logger.info(f"  TOTAL P&L: {emoji_total} ${total_pnl:.2f}")
        logger.info(f"  Posiciones: 🟢 {winning} ganadoras | 🔴 {losing} perdedoras")
    
    def print_detailed_report(self):
        """Imprime un reporte detallado con estadísticas"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 REPORTE DE POSICIONES")
        print("="*60)
        print(f"📊 Posiciones abiertas: {stats['open_positions']}")
        print(f"💰 P&L total: ${stats['total_pnl']:.2f}")
        print(f"📈 P&L promedio: ${stats['avg_pnl']:.2f}")
        print(f"🟢 Ganadoras: {stats['winning']}")
        print(f"🔴 Perdedoras: {stats['losing']}")
        print(f"🎯 Win Rate: {stats['win_rate']:.2%}")
        print("-"*60)
        print(f"📊 Posiciones cerradas: {stats['closed_positions']}")
        print(f"💰 P&L cerrado: ${stats['closed_pnl']:.2f}")
        print(f"🎯 Win Rate cerrado: {stats['closed_win_rate']:.2%}")
        print("-"*60)
        print(f"🏆 Mejor trade: ${stats['best_trade']:.2f}")
        print(f"💀 Peor trade: ${stats['worst_trade']:.2f}")
        print("="*60)
    
    def export_positions(self, filepath: str = "positions.csv") -> bool:
        """Exporta posiciones a CSV para análisis"""
        try:
            self._sync()
            if not self._positions:
                logger.warning("No hay posiciones para exportar")
                return False
            
            df = pd.DataFrame(self._positions.values())
            df.to_csv(filepath, index=False)
            logger.info(f"✅ Posiciones exportadas a {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exportando posiciones: {e}")
            return False