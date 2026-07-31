"""
Motor principal para MetaTrader 5 - VERSIÓN COMPLETA CON INTEGRACIÓN DE MÓDULOS MEJORADOS
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
    MT5_SERVER,
    COOLDOWN_MINUTES
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
    """Motor principal para MetaTrader 5 - VERSIÓN MEJORADA"""

    def __init__(self):
        logger.info("🚀 Inicializando DELTA ENGINE para MT5...")
        self.connected = False
        self.running = False
        self.account = None
        self.start_time = datetime.now()
        self.scan_count = 0
        
        # 🔥 ESTADO DEL SISTEMA
        self.paused = False
        self.pause_reason = None
        self.last_equity_update = None
        
        # 🔥 MÉTRICAS DE RENDIMIENTO
        self.equity_peak = 0
        self.equity_current = 0
        self.daily_pnl = 0
        self.daily_start_equity = 0
        
        # 🔥 INICIALIZAR MÓDULOS MEJORADOS
        self.asset_manager = AssetManager()
        self.market_data = MarketData()
        self.strategy = Strategy()
        self.risk_manager = RiskManager(ACCOUNT_SIZE, RISK_PER_TRADE, MAX_POSITIONS)
        self.order_manager = OrderManager(self)
        self.position_manager = PositionManager(self)

        # 🔥 CONEXIÓN
        self.connect()
        self.register_events()
        
        # 🔥 ACTUALIZAR EQUITY INICIAL
        self._update_equity()

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
            self.equity_peak = self.account.equity
            self.equity_current = self.account.equity
            self.daily_start_equity = self.account.equity
            
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
    # ACTUALIZACIÓN DE EQUITY Y RIESGO
    # ==========================================================

    def _update_equity(self):
        """Actualiza el equity y verifica límites de riesgo"""
        try:
            account = mt5.account_info()
            if account is None:
                return
            
            self.equity_current = account.equity
            
            # Actualizar peak
            if self.equity_current > self.equity_peak:
                self.equity_peak = self.equity_current
            
            # Actualizar RiskManager
            if hasattr(self, 'risk_manager'):
                self.risk_manager.update_equity(self.equity_current)
                self.risk_manager.daily_pnl = self.equity_current - self.daily_start_equity
                
                # Verificar si debemos pausar
                should_pause, reason = self.risk_manager.should_pause_trading()
                if should_pause and not self.paused:
                    self.paused = True
                    self.pause_reason = reason
                    logger.warning(f"⏸️ Trading pausado: {reason}")
                elif not should_pause and self.paused:
                    self.paused = False
                    self.pause_reason = None
                    logger.info("▶️ Trading reanudado")
            
            self.last_equity_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error actualizando equity: {e}")

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
            "paused": self.paused,
            "pause_reason": self.pause_reason,
            "equity": self.equity_current,
            "equity_peak": self.equity_peak,
            "drawdown": (self.equity_peak - self.equity_current) / self.equity_peak if self.equity_peak > 0 else 0
        }

    def metrics(self):
        return {
            "connected": self.connected,
            "account": self.account.login if self.account else None,
            "balance": self.account.balance if self.account else 0,
            "equity": self.equity_current,
            "equity_peak": self.equity_peak,
            "drawdown": (self.equity_peak - self.equity_current) / self.equity_peak if self.equity_peak > 0 else 0,
            "positions": len(self.position_manager.all()),
            "scans": self.scan_count,
            "uptime": str(self.uptime()),
            "paused": self.paused,
            "daily_pnl": self.daily_pnl,
        }

    def print_dashboard(self):
        """Imprime el dashboard de estado mejorado"""
        m = self.metrics()
        logger.info("=" * 60)
        logger.info("📊 DELTA ENGINE STATUS")
        logger.info("=" * 60)
        logger.info(f"🔌 Connected  : {m['connected']}")
        logger.info(f"💳 Account    : {m['account']}")
        logger.info(f"💰 Balance    : ${m['balance']:.2f}")
        logger.info(f"📈 Equity     : ${m['equity']:.2f}")
        logger.info(f"🏔️  Peak Equity: ${m['equity_peak']:.2f}")
        logger.info(f"📉 Drawdown   : {m['drawdown']:.2%}")
        logger.info(f"📊 Positions  : {m['positions']}")
        logger.info(f"🔄 Scans      : {m['scans']}")
        logger.info(f"⏱️  Uptime     : {m['uptime']}")
        logger.info(f"⏸️  Paused     : {m['paused']}")
        if m['paused']:
            logger.info(f"   Razón      : {self.pause_reason}")
        logger.info("=" * 60)

    # ==========================================================
    # MERCADO ABIERTO MEJORADO
    # ==========================================================

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
    # HEALTH CHECK MEJORADO
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
            
            # 🔥 VERIFICAR CONEXIÓN A MT5
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("❌ No se pudo obtener información de cuenta MT5")
                return False
            
            # 🔥 VERIFICAR SÍMBOLOS
            symbols = self.asset_manager.get_all()
            for symbol in symbols[:5]:  # Verificar primeros 5
                if not mt5.symbol_select(symbol, True):
                    logger.warning(f"⚠️ Símbolo no disponible: {symbol}")
            
            logger.info("✅ Health Check OK")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Health Check falló: {e}")
            return False

    # ==========================================================
    # SCANNER Y EJECUCIÓN MEJORADOS
    # ==========================================================

    def scan_market(self):
        """Obtiene señales del mercado con filtros mejorados"""
        logger.info("🔍 Escaneando mercado...")
        symbols = self.asset_manager.get_all()
        
        # 🔥 OBTENER SEÑALES DE LA ESTRATEGIA MEJORADA
        signals = self.strategy.analyze_symbols(symbols)
        
        # 🔥 FILTRAR POR SCORE MÍNIMO
        buys = [s for s in signals if s['action'] == 'BUY' and s['score'] >= MIN_SCORE]
        sells = [s for s in signals if s['action'] == 'SELL' and s['score'] >= MIN_SCORE]
        
        logger.info(f"📊 BUY={len(buys)} SELL={len(sells)}")
        
        # 🔥 LOG DE SEÑALES DETECTADAS
        for signal in buys[:3]:
            logger.info(f"   🟢 {signal['symbol']}: Score={signal['score']:.1f} | Conf={signal['confidence']:.2%}")
        for signal in sells[:3]:
            logger.info(f"   🔴 {signal['symbol']}: Score={signal['score']:.1f} | Conf={signal['confidence']:.2%}")
        
        return buys, sells

    def execute_trade(self, signal):
        """Ejecuta una orden con integración completa de todos los módulos mejorados"""
        try:
            symbol = signal['symbol']
            price = signal['price']
            atr = signal.get('atr', 0.001)
            action = signal['action']
            
            # 🔥 VERIFICAR MERCADO ABIERTO
            if not self.is_market_open(symbol):
                logger.info(f"⏳ {symbol}: Mercado cerrado, saltando...")
                return
            
            # 🔥 VERIFICAR SI EL SISTEMA ESTÁ PAUSADO
            if self.paused:
                logger.info(f"⏸️ Sistema pausado: {self.pause_reason}")
                return
            
            # 🔥 VERIFICAR POSICIÓN
            if self.position_manager.exists(symbol):
                logger.info(f"⏳ {symbol}: Ya existe posición, saltando...")
                return
            
            # 🔥 VERIFICAR TOTAL DE POSICIONES
            total_positions = self.position_manager.get_position_count()
            if total_positions >= MAX_POSITIONS:
                logger.info(f"⏳ Máximo de posiciones alcanzado ({MAX_POSITIONS}), saltando...")
                return
            
            # 🔥 CALCULAR CANTIDAD SEGÚN TIPO DE ACTIVO
            asset_type = self.asset_manager.get_asset_type(symbol)
            
            # Obtener información del símbolo
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"❌ No se pudo obtener información de {symbol}")
                return
            
            # 🔥 USAR RISK MANAGER PARA CALCULAR TAMAÑO DE POSICIÓN
            if asset_type == 'STOCK':
                quantity = DEFAULT_QTY_STOCK
                if action == 'BUY':
                    stop = price * (1 - STOCK_SL_PCT)
                    target = price * (1 + STOCK_TP_PCT)
                else:
                    stop = price * (1 + STOCK_SL_PCT)
                    target = price * (1 - STOCK_TP_PCT)
            else:
                # 🔥 USAR RISK MANAGER PARA TAMAÑO ADAPTATIVO
                risk_quantity = self.risk_manager.calculate_position_size(
                    symbol, price, stop if 'stop' in locals() else price * 0.99, atr
                )
                quantity = risk_quantity if risk_quantity > 0 else DEFAULT_QTY_FOREX
                
                if action == 'BUY':
                    stop = price - (atr * ATR_MULTIPLIER_SL)
                    target = price + (atr * ATR_MULTIPLIER_TP)
                else:
                    stop = price + (atr * ATR_MULTIPLIER_SL)
                    target = price - (atr * ATR_MULTIPLIER_TP)
            
            # 🔥 VALIDAR SL/TP (usando la validación del OrderManager)
            is_valid, message = self.order_manager._validate_prices(symbol, price, stop, target, action)
            if not is_valid:
                logger.warning(f"⚠️ {symbol}: {message}")
                # Ajustar SL/TP automáticamente
                if action == 'BUY':
                    stop = price * 0.99
                    target = price * 1.01
                else:
                    stop = price * 1.01
                    target = price * 0.99
            
            # 🔥 VERIFICAR RIESGO CON EL RISK MANAGER
            risk_check, risk_reason = self.risk_manager.validate_trade(
                symbol, action, price, stop, quantity
            )
            if not risk_check:
                logger.warning(f"⚠️ Riesgo rechazado: {risk_reason}")
                return
            
            logger.info(f"📊 {symbol} ({asset_type}): {action} {quantity} @ {price:.5f}")
            logger.info(f"   SL: {stop:.5f} | TP: {target:.5f}")
            
            # 🔥 ENVIAR ORDEN USANDO ORDER MANAGER MEJORADO
            result = self.order_manager.send_order(
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price,
                stop=stop,
                target=target,
                max_retries=3
            )
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Orden ejecutada en {symbol}")
                self.position_manager.force_sync()
                
                # 🔥 REGISTRAR EN RISK MANAGER
                self.risk_manager.register_trade(
                    symbol=symbol,
                    action=action,
                    volume=quantity,
                    entry=price,
                    exit=0,  # Se actualizará al cerrar
                    pnl=0
                )
                
                # 🔥 ACTUALIZAR EQUITY
                self._update_equity()
                
            else:
                error_msg = result.comment if result else "Unknown error"
                logger.warning(f"❌ Orden falló en {symbol}: {error_msg}")
                
        except Exception as e:
            logger.exception(f"Error ejecutando trade: {e}")

    # ==========================================================
    # GESTIÓN DE POSICIONES ACTIVAS
    # ==========================================================

    def manage_active_positions(self):
        """Gestiona posiciones activas con trailing stop y breakeven"""
        try:
            positions = self.position_manager.all()
            if not positions:
                return
            
            for symbol, pos in positions.items():
                # 🔥 SI ESTÁ EN GANANCIA, APLICAR TRAILING STOP
                if pos['profit'] > 0:
                    # Intentar mover a breakeven primero
                    if abs(pos['profit_pct']) > 0.5:  # 0.5% de ganancia
                        self.position_manager.apply_breakeven_stop(symbol)
                    
                    # Si la ganancia es mayor, aplicar trailing
                    if abs(pos['profit_pct']) > 1.0:  # 1% de ganancia
                        self.position_manager.apply_trailing_stop(symbol)
                
                # 🔥 SI ESTÁ EN PÉRDIDA Y ES GRANDE, CONSIDERAR CIERRE
                elif pos['profit'] < 0:
                    if abs(pos['profit_pct']) > 3.0:  # 3% de pérdida
                        logger.info(f"⚠️ {symbol}: Pérdida del {abs(pos['profit_pct']):.2f}%, cerrando...")
                        self.position_manager.close_position(symbol)
                        
        except Exception as e:
            logger.error(f"Error gestionando posiciones: {e}")

    # ==========================================================
    # BUCLE PRINCIPAL MEJORADO
    # ==========================================================

    def run(self):
        """Bucle principal del motor con integración completa"""
        if not self.is_connected():
            logger.error("❌ Motor no conectado a MT5.")
            return

        logger.info("=" * 70)
        logger.info("🚀 DELTA ENGINE para MT5 - INICIADO")
        logger.info("=" * 70)
        logger.info(f"📊 Acciones: {len(STOCKS)}")
        logger.info(f"🪙 Forex: {len(FOREX)}")
        logger.info(f"📈 Máximo posiciones: {MAX_POSITIONS}")
        logger.info(f"🎯 Score mínimo: {MIN_SCORE}")
        logger.info(f"⏱️  Cooldown: {COOLDOWN_MINUTES} min")
        logger.info(f"💀 Riesgo por trade: {RISK_PER_TRADE:.2%}")
        logger.info("=" * 70 + "\n")
        
        self.running = True

        while self.running:
            try:
                self.scan_count += 1
                
                # 🔥 ACTUALIZAR EQUITY
                self._update_equity()
                
                # 🔥 SINCRONIZAR POSICIONES
                self.position_manager.sync()
                self.order_manager.sync()

                # 🔥 VERIFICAR MERCADO
                if not self.is_market_open():
                    logger.info("🔴 Mercado cerrado. Esperando...")
                    time.sleep(60)
                    continue

                # 🔥 VERIFICAR SI ESTÁ PAUSADO POR RIESGO
                if self.paused:
                    logger.info(f"⏸️ Sistema pausado: {self.pause_reason}")
                    time.sleep(30)
                    continue

                # 🔥 GESTIONAR POSICIONES ACTIVAS
                self.manage_active_positions()

                # 🔥 ESCANEAR MERCADO
                buys, sells = self.scan_market()

                # 🔥 EJECUTAR COMPRAS
                if buys:
                    available = MAX_POSITIONS - len(self.position_manager.all())
                    for signal in buys[:available]:
                        if self.is_market_open(signal['symbol']):
                            self.execute_trade(signal)
                        else:
                            logger.info(f"⏳ {signal['symbol']}: Mercado cerrado, saltando...")

                # 🔥 EJECUTAR VENTAS
                if sells:
                    available = MAX_POSITIONS - len(self.position_manager.all())
                    for signal in sells[:available]:
                        if self.is_market_open(signal['symbol']):
                            self.execute_trade(signal)
                        else:
                            logger.info(f"⏳ {signal['symbol']}: Mercado cerrado, saltando...")

                # 🔥 RESUMEN DE POSICIONES
                self.position_manager.print_summary()
                
                # 🔥 DASHBOARD CADA 10 ESCANEOS
                if self.scan_count % 10 == 0:
                    self.print_dashboard()
                    
                    # Mostrar métricas de riesgo
                    risk_metrics = self.risk_manager.get_metrics()
                    if risk_metrics.get('total_trades', 0) > 0:
                        logger.info(f"📊 Win Rate: {risk_metrics['win_rate']:.2%}")
                        logger.info(f"📊 Sharpe: {risk_metrics['sharpe_ratio']:.2f}")

                # 🔥 RESET DIARIO
                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    self.risk_manager.reset_daily_stats()
                    logger.info("🔄 Estadísticas diarias reiniciadas")

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
    logger.info("🚀 DELTA ENGINE PRO - MT5 (VERSIÓN MEJORADA)")
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