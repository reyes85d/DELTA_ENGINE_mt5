"""
Gestión de órdenes para MT5 - VERSIÓN CORREGIDA PARA ACCIONES
"""

import MetaTrader5 as mt5
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderManager:
    """Gestor de órdenes para MT5"""
    
    def __init__(self, engine):
        self.engine = engine
        self.orders = {}
        self._sync()
    
    def _sync(self):
        try:
            orders = mt5.orders_get()
            if orders:
                for order in orders:
                    self.orders[order.order] = order
        except Exception as e:
            logger.error(f"Error sincronizando órdenes: {e}")
    
    def sync(self):
        self._sync()
    
    def active_orders(self):
        return [o for o in self.orders.values() if o.time_expiration == 0]
    
    def send_order(self, symbol: str, action: str, quantity: float, 
                   price: float, stop: float, target: float) -> mt5.OrderSendResult:
        """Envía una orden - CORREGIDO PARA ACCIONES"""
        try:
            # VERIFICAR SÍMBOLO
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Símbolo {symbol} no encontrado")
                return None
            
            asset_type = self.engine.asset_manager.get_asset_type(symbol)
            
            # PARA ACCIONES, activar si es necesario
            if asset_type == 'STOCK' and not symbol_info.visible:
                mt5.symbol_select(symbol, True)
                symbol_info = mt5.symbol_info(symbol)
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"No hay precio para {symbol}")
                return None
            
            # CREAR ORDEN
            order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
            
            if action == "BUY":
                entry_price = tick.ask
            else:
                entry_price = tick.bid
            
            # 🔥 VERIFICAR SL/TP - Para acciones, si son 0 no se envían
            use_sl = stop > 0 and stop != entry_price
            use_tp = target > 0 and target != entry_price
            
            # 🔥 CONSTRUIR SOLICITUD SIN SL/TP si son inválidos
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(quantity),
                "type": order_type,
                "price": entry_price,
                "deviation": 20,
                "magic": 123456,
                "comment": f"Delta MT5 - {asset_type}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # 🔥 AÑADIR SL Y TP SOLO SI SON VÁLIDOS
            if use_sl:
                request["sl"] = float(stop)
            if use_tp:
                request["tp"] = float(target)
            
            logger.info(f"📤 {symbol}: {action} {quantity} ({asset_type})")
            logger.info(f"   Entry: {entry_price:.2f}")
            if use_sl:
                logger.info(f"   SL: {stop:.2f}")
            if use_tp:
                logger.info(f"   TP: {target:.2f}")
            
            # 🔥 ENVIAR ORDEN
            result = mt5.order_send(request)
            
            if result is None:
                logger.error("Error: order_send devolvió None")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Error: {result.comment} (código: {result.retcode})")
                return None
            
            logger.info(f"✅ {symbol}: Orden ejecutada")
            return result
            
        except Exception as e:
            logger.error(f"Error enviando orden: {e}")
            return None