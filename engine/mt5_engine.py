"""
Motor principal para MetaTrader 5 - VERSIÓN COMPLETA Y CORREGIDA
"""

import time
from datetime import datetime
import MetaTrader5 as mt5

# 🔥 IMPORTAR CONFIGURACIÓN
from config import (
    ACCOUNT_SIZE,
    RISK_PER_TRADE,
    MAX_POSITIONS,
    SCAN_INTERVAL,
    STOCKS,
    FOREX,
    MIN_SCORE,
    ATR_MULTIPLIER_SL,
    ATR_MULTIPLIER_TP,
    STOCK_SL_PCT,
    STOCK_TP_PCT,
    DEFAULT_QTY_STOCK,
    DEFAULT_QTY_FOREX,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_SERVER
)

from engine.asset_manager import AssetManager
from engine.market_data import MarketData
from engine.order_manager import OrderManager
from engine.position_manager import PositionManager
from strategies.strategy import Strategy
from risk.risk_manager import RiskManager
from utils.logger import get_logger

logger = get_logger(__name__)


class MT5Engine:
    """Motor principal para MetaTrader 5"""

    def __init__(self):
        logger.info("Inicializando DELTA ENGINE para MT5...")
        self.connected = False
        self.running = False
        self.account = None
        self.start_time = datetime.now()
        self.scan_count = 0

        # Inicializar módulos
        self.asset_manager = AssetManager()
        self.market_data = MarketData()
        self.strategy = Strategy()
        self.risk_manager = RiskManager(ACCOUNT_SIZE, RISK_PER_TRADE, MAX_POSITIONS)
        self.order_manager = OrderManager(self)
        self.position_manager = PositionManager(self)

        self.connect()
        self.register_events()

    # ==========================================================
    # CONEXIÓN Y DESCONEXIÓN
    # ==========================================================

    def connect(self):
        """Conecta al terminal MetaTrader 5"""
        try:
            logger.info("Conectando a MetaTrader 5...")
            
            if not mt5.initialize():
                logger.error("Error al inicializar MT5")
                self.connected = False
                return

            if MT5_LOGIN:
                authorized = mt5.login(
                    login=MT5_LOGIN,
                    password=MT5_PASSWORD,
                    server=MT5_SERVER
                )
                if not authorized:
                    logger.error(f"Error en login: {mt5.last_error()}")
                    self.connected = False
                    return

            self.account = mt5.account_info()
            if self.account is None:
                logger.error("No se pudo obtener información de la cuenta")
                self.connected = False
                return

            self.connected = True
            logger.info(f"✅ Conectado a MT5 - Cuenta: {self.account.login}")
            logger.info(f"💰 Balance: ${self.account.balance:.2f}")
            logger.info(f"📈 Equity: ${self.account.equity:.2f}")
            self._sync_initial_state()

        except Exception as e:
            logger.exception(f"Error en conexión MT5: {e}")
            self.connected = False

    def disconnect(self):
        """Desconecta de MT5"""
        try:
            mt5.shutdown()
        except:
            pass
        self.connected = False
        logger.info("Desconectado de MT5.")

    def is_connected(self):
        return self.connected and mt5.terminal_info() is not None

    def _sync_initial_state(self):
        """Sincroniza posiciones y órdenes existentes al inicio"""
        logger.info("Sincronizando estado inicial...")
        self.position_manager.sync()
        self.order_manager.sync()
        logger.info("Estado inicial sincronizado.")

    # ==========================================================
    # EVENTOS
    # ==========================================================

    def register_events(self):
        """Registra eventos (MT5 no tiene sistema de eventos como IBKR)"""
        logger.info("✅ Eventos registrados para MT5")

    def on_connect(self):
        logger.info("Conectado a MT5")

    def on_disconnect(self):
        logger.warning("Desconectado de MT5")

    def on_error(self, error):
        logger.error(f"Error MT5: {error}")

    # ==========================================================
    # ESTADO Y ESTADÍSTICAS
    # ==========================================================

    def uptime(self):
        return datetime.now() - self.start_time

    def status(self):
        return {
            "connected": self.connected,
            "account": self.account.login if self.account else None,
            "uptime": str(self.uptime()),
            "positions": len(self.position_manager.all()),
            "scans": self.scan_count,
        }

    def metrics(self):
        return {
            "connected": self.connected,
            "account": self.account.login if self.account else None,
            "balance": self.account.balance if self.account else 0,
            "equity": self.account.equity if self.account else 0,
            "positions": len(self.position_manager.all()),
            "scans": self.scan_count,
            "uptime": str(self.uptime()),
        }

    def print_dashboard(self):
        """Imprime el dashboard de estado"""
        m = self.metrics()
        logger.info("=" * 50)
        logger.info("📊 DELTA ENGINE STATUS")
        logger.info("=" * 50)
        logger.info(f"🔌 Connected  : {m['connected']}")
        logger.info(f"💳 Account    : {m['account']}")
        logger.info(f"💰 Balance    : ${m['balance']:.2f}")
        logger.info(f"📈 Equity     : ${m['equity']:.2f}")
        logger.info(f"📊 Positions  : {m['positions']}")
        logger.info(f"🔄 Scans      : {m['scans']}")
        logger.info(f"⏱️  Uptime     : {m['uptime']}")
        logger.info("=" * 50)

    # ==========================================================
    # MERCADO ABIERTO
    # ==========================================================

    # En engine/mt5_engine.py, reemplaza la función is_market_open

    def is_market_open(self, symbol: str = None) -> bool:
        """Verifica si el mercado está abierto para un símbolo específico"""
        now = datetime.now()
        
        # Fin de semana
        if now.weekday() >= 5:  # Sábado o Domingo
            return False
        
        # Si no hay símbolo, asumir Forex (abierto 24/5)
        if symbol is None:
            return True
        
        # Verificar tipo de activo
        asset_type = self.asset_manager.get_asset_type(symbol)
        
        if asset_type == 'FOREX':
            # Forex opera 24/5 (excepto fines de semana)
            return True
        
        elif asset_type == 'STOCK':
            # Acciones: NYSE/NASDAQ 9:30 AM - 4:00 PM ET (14:30-21:00 UTC)
            hour_utc = now.hour + (now.minute / 60)
            # 14:30 UTC = 9:30 AM ET
            # 21:00 UTC = 4:00 PM ET
            return 14.5 <= hour_utc <= 21.0
        
        # Otros activos (asumir abiertos)
        return True

    def market_status(self):
        return "OPEN" if self.is_market_open() else "CLOSED"

    # ==========================================================
    # HEALTH CHECK
    # ==========================================================

    def health_check(self):
        """Verifica que los componentes estén operativos"""
        try:
            if not self.is_connected():
                logger.error("❌ No conectado a MT5")
                return False
            
            if self.asset_manager is None:
                logger.error("❌ AssetManager no inicializado")
                return False
            
            if self.market_data is None:
                logger.error("❌ MarketData no inicializado")
                return False
            
            if self.strategy is None:
                logger.error("❌ Strategy no inicializado")
                return False
            
            if self.risk_manager is None:
                logger.error("❌ RiskManager no inicializado")
                return False
            
            if self.order_manager is None:
                logger.error("❌ OrderManager no inicializado")
                return False
            
            if self.position_manager is None:
                logger.error("❌ PositionManager no inicializado")
                return False
            
            logger.info("✅ Health Check OK")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Health Check falló: {e}")
            return False

    # ==========================================================
    # SCANNER Y EJECUCIÓN
    # ==========================================================

    def scan_market(self):
        """Obtiene señales del mercado"""
        logger.info("🔍 Escaneando mercado...")
        symbols = self.asset_manager.get_all()
        signals = self.strategy.analyze_symbols(symbols)
        buys = [s for s in signals if s['action'] == 'BUY' and s['score'] >= MIN_SCORE]
        sells = [s for s in signals if s['action'] == 'SELL' and s['score'] >= MIN_SCORE]
        logger.info(f"📊 BUY={len(buys)} SELL={len(sells)}")
        return buys, sells

    # En engine/mt5_engine.py, reemplaza la función execute_trade

    def execute_trade(self, signal):
        """Ejecuta una orden con validación de SL/TP"""
        try:
            symbol = signal['symbol']
            price = signal['price']
            atr = signal.get('atr', 0.001)
            
            # 🔥 VERIFICAR MERCADO ABIERTO
            if not self.is_market_open(symbol):
                logger.info(f"⏳ {symbol}: Mercado cerrado, saltando...")
                return
            
            # VERIFICAR POSICIÓN
            if self.position_manager.exists(symbol):
                logger.info(f"⏳ {symbol}: Ya existe posición, saltando...")
                return
            
            # VERIFICAR TOTAL
            total_positions = self.position_manager.get_position_count()
            if total_positions >= MAX_POSITIONS:
                logger.info(f"⏳ Máximo de posiciones alcanzado ({MAX_POSITIONS}), saltando...")
                return
            
            # CALCULAR CANTIDAD SEGÚN TIPO DE ACTIVO
            asset_type = self.asset_manager.get_asset_type(symbol)
            
            # Obtener información del símbolo para validar SL/TP
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"❌ No se pudo obtener información de {symbol}")
                return
            
            # Calcular el tamaño mínimo de distancia (10 ticks)
            min_distance = symbol_info.trade_tick_size * 10
            
            if asset_type == 'STOCK':
                quantity = DEFAULT_QTY_STOCK
                if signal['action'] == 'BUY':
                    stop = price * (1 - STOCK_SL_PCT)
                    target = price * (1 + STOCK_TP_PCT)
                else:
                    stop = price * (1 + STOCK_SL_PCT)
                    target = price * (1 - STOCK_TP_PCT)
            else:
                quantity = DEFAULT_QTY_FOREX
                # Para Forex, usar ATR pero con validación
                if signal['action'] == 'BUY':
                    stop = price - (atr * ATR_MULTIPLIER_SL)
                    target = price + (atr * ATR_MULTIPLIER_TP)
                else:
                    stop = price + (atr * ATR_MULTIPLIER_SL)
                    target = price - (atr * ATR_MULTIPLIER_TP)
            
            # 🔥 VALIDAR SL/TP
            # Para compras: SL debe ser < price, TP debe ser > price
            # Para ventas: SL debe ser > price, TP debe ser < price
            
            if signal['action'] == 'BUY':
                # Validar SL (debe ser menor que el precio)
                if stop >= price or abs(stop - price) < min_distance:
                    stop = price - max(price * 0.005, min_distance)
                    logger.debug(f"   SL ajustado a {stop:.5f}")
                
                # Validar TP (debe ser mayor que el precio)
                if target <= price or abs(target - price) < min_distance:
                    target = price + max(price * 0.01, min_distance * 2)
                    logger.debug(f"   TP ajustado a {target:.5f}")
            
            else:  # SELL
                # Validar SL (debe ser mayor que el precio)
                if stop <= price or abs(stop - price) < min_distance:
                    stop = price + max(price * 0.005, min_distance)
                    logger.debug(f"   SL ajustado a {stop:.5f}")
                
                # Validar TP (debe ser menor que el precio)
                if target >= price or abs(target - price) < min_distance:
                    target = price - max(price * 0.01, min_distance * 2)
                    logger.debug(f"   TP ajustado a {target:.5f}")
            
            # 🔥 VERIFICAR QUE SL/TP NO ESTÉN INVERTIDOS
            if signal['action'] == 'BUY':
                if stop >= target:
                    logger.warning(f"⚠️ SL >= TP para BUY, ajustando...")
                    stop = price - 0.01
                    target = price + 0.02
            
            logger.info(f"📊 {symbol} ({asset_type}): {signal['action']} {quantity} @ {price:.2f}")
            logger.info(f"   SL: {stop:.2f} | TP: {target:.2f}")
            
            # Enviar orden
            result = self.order_manager.send_order(
                symbol=symbol,
                action=signal['action'],
                quantity=quantity,
                price=price,
                stop=stop,
                target=target,
            )
            
            if result and (result.volume > 0 or result.volume is not None):
                logger.info(f"✅ Orden ejecutada en {symbol}")
                self.position_manager.force_sync()
            else:
                logger.warning(f"❌ Orden falló en {symbol}")
                
        except Exception as e:
            logger.exception(f"Error ejecutando trade: {e}")

    # ==========================================================
    # BUCLE PRINCIPAL
    # ==========================================================

    # En engine/mt5_engine.py, modifica el bucle principal

    def run(self):
        """Bucle principal del motor"""
        if not self.is_connected():
            logger.error("❌ Motor no conectado a MT5.")
            return

        logger.info("=" * 60)
        logger.info("🚀 DELTA ENGINE para MT5 - INICIADO")
        logger.info("=" * 60)
        logger.info(f"📊 Acciones: {len(STOCKS)}")
        logger.info(f"🪙 Forex: {len(FOREX)}")
        logger.info(f"📈 Máximo posiciones: {MAX_POSITIONS}")
        logger.info(f"🎯 Score mínimo: {MIN_SCORE}")
        logger.info("=" * 60 + "\n")
        
        self.running = True

        while self.running:
            try:
                self.scan_count += 1
                
                # Sincronizar posiciones
                self.position_manager.sync()
                self.order_manager.sync()

                # Verificar mercado global (Forex)
                if not self.is_market_open():
                    logger.info("🔴 Mercado Forex cerrado (fin de semana). Esperando...")
                    time.sleep(60)
                    continue

                # Escanear
                buys, sells = self.scan_market()

                # Ejecutar compras (con validación individual)
                if buys:
                    available = self.risk_manager.max_positions - len(self.position_manager.all())
                    for signal in buys[:available]:
                        # 🔥 Verificar mercado para cada símbolo individualmente
                        if self.is_market_open(signal['symbol']):
                            self.execute_trade(signal)
                        else:
                            logger.info(f"⏳ {signal['symbol']}: Mercado cerrado, saltando...")

                # Ejecutar ventas (si las hay)
                if sells:
                    available = self.risk_manager.max_positions - len(self.position_manager.all())
                    for signal in sells[:available]:
                        if self.is_market_open(signal['symbol']):
                            self.execute_trade(signal)
                        else:
                            logger.info(f"⏳ {signal['symbol']}: Mercado cerrado, saltando...")

                # Resumen
                self.position_manager.print_summary()
                
                # Dashboard cada 10 escaneos
                if self.scan_count % 10 == 0:
                    self.print_dashboard()

                time.sleep(SCAN_INTERVAL)

            except KeyboardInterrupt:
                logger.warning("🛑 Motor detenido por el usuario.")
                break
            except Exception as e:
                logger.exception(f"❌ Error en bucle: {e}")
                time.sleep(60)

        self.stop()

    def stop(self):
        """Detiene el motor"""
        logger.warning("🛑 Parando motor...")
        self.running = False
        self.disconnect()
        logger.info("✅ Motor detenido.")

    def shutdown(self):
        """Apagado controlado"""
        logger.info("🔄 Apagando motor...")
        self.stop()
        logger.info("✅ Motor apagado correctamente")


def main():
    """Función principal"""
    logger.info("=" * 70)
    logger.info("🚀 DELTA ENGINE PRO - MT5")
    logger.info("=" * 70)
    
    engine = MT5Engine()
    
    if not engine.health_check():
        logger.error("❌ Health Check fallido.")
        return
    
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.warning("🛑 Interrupción del usuario.")
    except Exception as e:
        logger.exception(f"❌ Error: {e}")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()