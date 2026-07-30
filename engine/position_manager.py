"""
Gestión de posiciones para MT5 - VERSIÓN COMPLETA
"""

import MetaTrader5 as mt5
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class PositionManager:
    """Gestor de posiciones para MT5"""
    
    def __init__(self, engine):
        self.engine = engine
        self._positions = {}
        self._last_sync = None
        self._sync()
    
    def _sync(self):
        """Sincroniza TODAS las posiciones existentes"""
        try:
            positions = mt5.positions_get()
            self._positions = {}
            
            if positions:
                for pos in positions:
                    self._positions[pos.symbol] = {
                        'symbol': pos.symbol,
                        'ticket': pos.ticket,
                        'qty': pos.volume,
                        'open_price': pos.price_open,
                        'current_price': pos.price_current,
                        'profit': pos.profit,
                        'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                        'time': pos.time,
                    }
            
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
    
    def all(self):
        """Devuelve todas las posiciones"""
        return self._positions
    
    def exists(self, symbol: str) -> bool:
        """Verifica si existe una posición para un símbolo"""
        self._sync()
        return symbol in self._positions
    
    def get(self, symbol: str):
        """Obtiene una posición por símbolo"""
        self._sync()
        return self._positions.get(symbol)
    
    def get_position_count(self) -> int:
        """Obtiene el número total de posiciones"""
        self._sync()
        return len(self._positions)
    
    def get_count(self) -> int:
        """Obtiene el número total de posiciones (alias)"""
        return self.get_position_count()
    
    def get_symbols(self) -> list:
        """Obtiene la lista de símbolos con posiciones abiertas"""
        self._sync()
        return list(self._positions.keys())
    
    def close_position(self, symbol: str):
        """Cierra una posición"""
        try:
            self._sync()
            pos = self._positions.get(symbol)
            if pos is None:
                logger.warning(f"No hay posición en {symbol}")
                return False
            
            order_type = mt5.ORDER_TYPE_SELL if pos['type'] == 'BUY' else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos['qty'],
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
                logger.error(f"Error cerrando {symbol}: {result.comment}")
                return False
            
            logger.info(f"✅ Posición cerrada: {symbol}")
            self._sync()
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición {symbol}: {e}")
            return False
    
    def close_all(self):
        """Cierra todas las posiciones"""
        self._sync()
        if not self._positions:
            logger.info("📭 No hay posiciones para cerrar")
            return 0
        
        closed = 0
        for symbol in list(self._positions.keys()):
            if self.close_position(symbol):
                closed += 1
        
        return closed
    
    def print_summary(self):
        """Imprime un resumen de TODAS las posiciones"""
        self._sync()
        
        if not self._positions:
            logger.info("📭 No hay posiciones abiertas")
            return
        
        total_pnl = 0
        logger.info(f"💰 POSICIONES ({len(self._positions)}):")
        for symbol, pos in self._positions.items():
            pnl = pos.get('profit', 0)
            total_pnl += pnl
            emoji = "🟢" if pnl > 0 else "🔴"
            logger.info(f"  {emoji} {symbol}: {pos['qty']} @ {pos['open_price']:.5f} | P&L: ${pnl:.2f}")
        
        emoji_total = "🟢" if total_pnl > 0 else "🔴"
        logger.info(f"  TOTAL P&L: {emoji_total} ${total_pnl:.2f}")