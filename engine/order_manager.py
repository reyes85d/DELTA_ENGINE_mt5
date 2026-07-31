"""
Gestión de órdenes para MT5 - VERSIÓN MEJORADA CON VALIDACIONES AVANZADAS
"""

import MetaTrader5 as mt5
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderManager:
    """Gestor de órdenes avanzado para MT5"""
    
    def __init__(self, engine):
        self.engine = engine
        self.orders = {}
        self.order_history = []
        self.max_retries = 3
        self.retry_delay = 1  # segundos
        self._sync()
    
    # ==========================================================
    # SINCronización
    # ==========================================================
    
    def _sync(self):
        """Sincroniza órdenes activas"""
        try:
            orders = mt5.orders_get()
            if orders:
                for order in orders:
                    self.orders[order.order] = order
            logger.debug(f"🔄 Órdenes sincronizadas: {len(self.orders)}")
        except Exception as e:
            logger.error(f"Error sincronizando órdenes: {e}")
    
    def sync(self):
        """Método público para sincronizar"""
        self._sync()
    
    def active_orders(self) -> List:
        """Retorna órdenes activas"""
        return [o for o in self.orders.values() if o.time_expiration == 0]
    
    def get_order(self, order_id: int):
        """Obtiene una orden por ID"""
        return self.orders.get(order_id)
    
    # ==========================================================
    # VALIDACIÓN DE PRECIOS
    # ==========================================================
    
    def _validate_prices(self, symbol: str, entry: float, stop: float, 
                         target: float, action: str) -> Tuple[bool, str]:
        """
        Valida que los precios sean correctos para la orden
        
        Returns:
            (bool, str): (Válido, Mensaje)
        """
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False, f"Símbolo {symbol} no encontrado"
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return False, f"No hay precio para {symbol}"
            
            # 🔥 VERIFICAR QUE EL PRECIO DE ENTRADA SEA VÁLIDO
            if action == "BUY":
                if entry <= 0 or entry < tick.bid * 0.9:
                    return False, f"Precio de entrada inválido: {entry}"
            else:  # SELL
                if entry <= 0 or entry > tick.ask * 1.1:
                    return False, f"Precio de entrada inválido: {entry}"
            
            # 🔥 VERIFICAR SL/TP
            min_distance = symbol_info.trade_tick_size * 10
            
            if stop > 0:
                if action == "BUY":
                    if stop >= entry:
                        return False, f"SL ({stop}) debe ser menor que entrada ({entry})"
                    if entry - stop < min_distance:
                        return False, f"SL demasiado cerca ({entry - stop:.5f} < {min_distance:.5f})"
                else:  # SELL
                    if stop <= entry:
                        return False, f"SL ({stop}) debe ser mayor que entrada ({entry})"
                    if stop - entry < min_distance:
                        return False, f"SL demasiado cerca ({stop - entry:.5f} < {min_distance:.5f})"
            
            if target > 0:
                if action == "BUY":
                    if target <= entry:
                        return False, f"TP ({target}) debe ser mayor que entrada ({entry})"
                    if target - entry < min_distance * 2:
                        return False, f"TP demasiado cerca ({target - entry:.5f} < {min_distance * 2:.5f})"
                else:  # SELL
                    if target >= entry:
                        return False, f"TP ({target}) debe ser menor que entrada ({entry})"
                    if entry - target < min_distance * 2:
                        return False, f"TP demasiado cerca ({entry - target:.5f} < {min_distance * 2:.5f})"
            
            # 🔥 VERIFICAR QUE SL < TP (para BUY) o SL > TP (para SELL)
            if stop > 0 and target > 0:
                if action == "BUY" and stop >= target:
                    return False, f"SL ({stop}) debe ser menor que TP ({target})"
                if action == "SELL" and stop <= target:
                    return False, f"SL ({stop}) debe ser mayor que TP ({target})"
            
            return True, "Precios válidos"
            
        except Exception as e:
            return False, f"Error en validación: {e}"
    
    # ==========================================================
    # ENVÍO DE ÓRDENES CON REINTENTOS
    # ==========================================================
    
    def send_order(self, symbol: str, action: str, quantity: float, 
                   price: float, stop: float = 0, target: float = 0,
                   max_retries: int = 3) -> Optional[mt5.OrderSendResult]:
        """
        Envía una orden con validación avanzada y reintentos
        
        Args:
            symbol: Símbolo
            action: 'BUY' o 'SELL'
            quantity: Cantidad (acciones o lotes)
            price: Precio de entrada
            stop: Stop Loss (0 = sin SL)
            target: Take Profit (0 = sin TP)
            max_retries: Número máximo de reintentos
        
        Returns:
            OrderSendResult o None si falla
        """
        try:
            # 🔥 1. VERIFICAR SÍMBOLO
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"❌ Símbolo {symbol} no encontrado")
                return None
            
            # 🔥 2. ACTIVAR SÍMBOLO SI ES NECESARIO
            asset_type = self.engine.asset_manager.get_asset_type(symbol)
            if asset_type == 'STOCK' and not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"❌ No se pudo activar {symbol}")
                    return None
            
            # 🔥 3. OBTENER PRECIO ACTUAL
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"❌ No hay precio para {symbol}")
                return None
            
            # 🔥 4. DETERMINAR PRECIO DE ENTRADA
            if action == "BUY":
                entry_price = tick.ask if price <= 0 else price
            else:
                entry_price = tick.bid if price <= 0 else price
            
            # 🔥 5. CALCULAR SL/TP SI NO SE PROPORCIONARON
            if stop == 0:
                stop = self._calculate_stop(symbol, action, entry_price)
            if target == 0:
                target = self._calculate_target(symbol, action, entry_price)
            
            # 🔥 6. VALIDAR PRECIOS
            is_valid, message = self._validate_prices(symbol, entry_price, stop, target, action)
            if not is_valid:
                logger.error(f"❌ Validación falló: {message}")
                return None
            
            # 🔥 7. VERIFICAR RIESGO CON EL RISK MANAGER
            if hasattr(self.engine, 'risk_manager'):
                risk_check, risk_reason = self.engine.risk_manager.validate_trade(
                    symbol, action, entry_price, stop, quantity
                )
                if not risk_check:
                    logger.warning(f"⚠️ Riesgo rechazado: {risk_reason}")
                    return None
            
            # 🔥 8. CONSTRUIR SOLICITUD
            order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
            
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
            
            # Añadir SL/TP solo si son válidos
            if stop > 0 and stop != entry_price:
                request["sl"] = float(stop)
            if target > 0 and target != entry_price:
                request["tp"] = float(target)
            
            # 🔥 9. ENVIAR ORDEN CON REINTENTOS
            result = self._send_with_retry(request, max_retries)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                # Registrar orden exitosa
                self._register_order(result, symbol, action, quantity, entry_price, stop, target)
                return result
            else:
                logger.error(f"❌ Orden falló: {result.comment if result else 'Unknown error'}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error enviando orden: {e}")
            return None
    
    def _send_with_retry(self, request: Dict, max_retries: int) -> Optional[mt5.OrderSendResult]:
        """
        Envía una orden con reintentos en caso de error
        """
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"🔄 Reintento {attempt}/{max_retries}...")
                    time.sleep(self.retry_delay * attempt)
                
                result = mt5.order_send(request)
                
                if result is None:
                    logger.error("❌ order_send devolvió None")
                    continue
                
                # 🔥 ERRORES RECUPERABLES
                if result.retcode in [10016, 10018, 10027, 10028]:
                    logger.warning(f"⚠️ Error recuperable: {result.comment} (código: {result.retcode})")
                    continue
                
                # 🔥 ERRORES FATALES
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"❌ Error fatal: {result.comment} (código: {result.retcode})")
                    return result
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Error en intento {attempt}: {e}")
                if attempt == max_retries:
                    return None
        
        return None
    
    # ==========================================================
    # CÁLCULO DE SL/TP AUTOMÁTICOS
    # ==========================================================
    
    def _calculate_stop(self, symbol: str, action: str, price: float) -> float:
        """Calcula un stop loss automático basado en ATR o porcentaje"""
        try:
            # Obtener ATR del símbolo (desde MarketData)
            atr = self._get_atr(symbol)
            
            if atr > 0:
                if action == "BUY":
                    return price - (atr * 1.5)  # 1.5x ATR para SL
                else:
                    return price + (atr * 1.5)
            else:
                # Fallback: 1% de distancia
                if action == "BUY":
                    return price * 0.99
                else:
                    return price * 1.01
                    
        except Exception as e:
            logger.error(f"Error calculando SL: {e}")
            return price * 0.99 if action == "BUY" else price * 1.01
    
    def _calculate_target(self, symbol: str, action: str, price: float) -> float:
        """Calcula un take profit automático basado en ATR o porcentaje"""
        try:
            atr = self._get_atr(symbol)
            
            if atr > 0:
                if action == "BUY":
                    return price + (atr * 3.0)  # 3x ATR para TP
                else:
                    return price - (atr * 3.0)
            else:
                # Fallback: 2% de distancia
                if action == "BUY":
                    return price * 1.02
                else:
                    return price * 0.98
                    
        except Exception as e:
            logger.error(f"Error calculando TP: {e}")
            return price * 1.02 if action == "BUY" else price * 0.98
    
    def _get_atr(self, symbol: str) -> float:
        """Obtiene el ATR del símbolo desde MarketData"""
        try:
            if hasattr(self.engine, 'market_data'):
                data = self.engine.market_data.get_rates(symbol, timeframe='M5', count=50)
                if not data.empty and 'atr' in data.columns:
                    return data['atr'].iloc[-1]
            return 0
        except:
            return 0
    
    # ==========================================================
    # REGISTRO DE ÓRDENES
    # ==========================================================
    
    def _register_order(self, result: mt5.OrderSendResult, symbol: str, 
                        action: str, quantity: float, price: float, 
                        stop: float, target: float):
        """Registra una orden exitosa"""
        order_info = {
            'order_id': result.order,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'stop': stop,
            'target': target,
            'timestamp': datetime.now(),
            'result': result
        }
        
        self.order_history.append(order_info)
        self.orders[result.order] = result
        
        logger.info(f"✅ Orden registrada: {symbol} {action} {quantity} @ {price}")
    
    # ==========================================================
    # MODIFICACIÓN Y CANCELACIÓN DE ÓRDENES
    # ==========================================================
    
    def modify_order(self, order_id: int, stop: float = None, target: float = None) -> bool:
        """
        Modifica una orden existente (SL/TP)
        """
        try:
            order = self.get_order(order_id)
            if order is None:
                logger.error(f"❌ Orden {order_id} no encontrada")
                return False
            
            # Preparar modificación
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "order": order_id,
            }
            
            if stop is not None:
                request["sl"] = float(stop)
            if target is not None:
                request["tp"] = float(target)
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Orden {order_id} modificada")
                return True
            else:
                logger.error(f"❌ Error modificando orden: {result.comment if result else 'Unknown'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error modificando orden: {e}")
            return False
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancela una orden pendiente
        """
        try:
            result = mt5.order_cancel(order_id)
            
            if result:
                logger.info(f"✅ Orden {order_id} cancelada")
                self.orders.pop(order_id, None)
                return True
            else:
                logger.error(f"❌ Error cancelando orden {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error cancelando orden: {e}")
            return False
    
    # ==========================================================
    # ESTADÍSTICAS Y REPORTES
    # ==========================================================
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de órdenes"""
        total_orders = len(self.order_history)
        
        if total_orders == 0:
            return {'total_orders': 0}
        
        # Órdenes por tipo
        buy_orders = len([o for o in self.order_history if o['action'] == 'BUY'])
        sell_orders = total_orders - buy_orders
        
        # Símbolos más operados
        symbols = {}
        for order in self.order_history:
            sym = order['symbol']
            symbols[sym] = symbols.get(sym, 0) + 1
        
        top_symbols = sorted(symbols.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_orders': total_orders,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'top_symbols': top_symbols,
            'active_orders': len(self.active_orders())
        }
    
    def print_report(self):
        """Imprime reporte de órdenes"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 REPORTE DE ÓRDENES")
        print("="*60)
        print(f"📝 Total órdenes: {stats['total_orders']}")
        print(f"📈 BUY: {stats['buy_orders']} | SELL: {stats['sell_orders']}")
        print(f"🔄 Activas: {stats['active_orders']}")
        print(f"\n🏆 Top símbolos:")
        for sym, count in stats['top_symbols']:
            print(f"   {sym}: {count}")
        print("="*60)
    
    # ==========================================================
    # LIMPIEZA DE ÓRDENES HUÉRFANAS
    # ==========================================================
    
    def cleanup_orphan_orders(self):
        """Limpia órdenes huérfanas (no sincronizadas)"""
        try:
            active_orders = mt5.orders_get()
            if not active_orders:
                return
            
            sync_orders = set(self.orders.keys())
            mt5_orders = set(o.order for o in active_orders)
            
            # Remover órdenes que ya no existen en MT5
            orphan = sync_orders - mt5_orders
            for order_id in orphan:
                self.orders.pop(order_id, None)
                logger.info(f"🧹 Orden huérfana removida: {order_id}")
            
        except Exception as e:
            logger.error(f"Error limpiando órdenes huérfanas: {e}")