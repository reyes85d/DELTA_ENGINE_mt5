"""
Gestión de Riesgo Avanzada para DELTA ENGINE MT5
- Control de Drawdown dinámico
- Tamaño de posición adaptativo
- Límites por símbolo y globales
- Métricas de riesgo en tiempo real
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """
    Gestor de riesgo avanzado con control dinámico
    """
    
    def __init__(self, account_size: float, risk_per_trade: float, max_positions: int):
        """
        Inicializa el gestor de riesgo
        
        Args:
            account_size: Tamaño inicial de la cuenta
            risk_per_trade: Riesgo máximo por operación (0.01 = 1%)
            max_positions: Número máximo de posiciones simultáneas
        """
        # Configuración base
        self.initial_account_size = account_size
        self.current_account_size = account_size
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions
        
        # 🔥 CONFIGURACIÓN AVANZADA DE RIESGO
        self.max_drawdown_pct = 0.15  # 15% máximo drawdown
        self.max_daily_loss_pct = 0.05  # 5% pérdida máxima diaria
        self.max_consecutive_losses = 3  # Máximo pérdidas consecutivas
        self.max_risk_per_symbol = 0.05  # 5% del capital en un solo símbolo
        
        # 🔥 SEGUIMIENTO DE RENDIMIENTO
        self.daily_pnl = 0
        self.daily_start_equity = account_size
        self.peak_equity = account_size
        self.current_drawdown = 0
        self.drawdown_history = []
        
        # 🔥 ESTADÍSTICAS DE OPERACIONES
        self.trades = []
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.win_count = 0
        self.loss_count = 0
        self.total_pnl = 0
        
        # 🔥 LÍMITES POR SÍMBOLO
        self.symbol_limits = {}  # {symbol: {'max_volume': float, 'current_volume': float}}
        self.symbol_risk = {}  # {symbol: risk_factor}
        
        # 🔥 MATRIZ DE CORRELACIÓN (simplificada)
        self.correlation_matrix = self._init_correlation_matrix()
        
        logger.info(f"✅ RiskManager inicializado:")
        logger.info(f"   Cuenta: ${account_size:.2f}")
        logger.info(f"   Riesgo por trade: {risk_per_trade:.2%}")
        logger.info(f"   Max posiciones: {max_positions}")
        logger.info(f"   Max drawdown: {self.max_drawdown_pct:.2%}")
    
    # ==========================================================
    # CONFIGURACIÓN Y VALIDACIÓN
    # ==========================================================
    
    def _init_correlation_matrix(self) -> Dict:
        """
        Inicializa matriz de correlación entre símbolos (simplificada)
        """
        # Grupos de alta correlación
        return {
            'forex_majors': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF'],
            'tech_stocks': ['AAPL', 'MSFT', 'GOOG', 'NVDA', 'META', 'AMZN'],
            'crypto_related': ['MSTR', 'COIN']
        }
    
    def _are_correlated(self, symbol1: str, symbol2: str) -> bool:
        """
        Verifica si dos símbolos están altamente correlacionados
        """
        for group, symbols in self.correlation_matrix.items():
            if symbol1 in symbols and symbol2 in symbols:
                return True
        return False
    
    # ==========================================================
    # VALIDACIÓN DE RIESGO
    # ==========================================================
    
    def validate_trade(self, symbol: str, action: str, price: float, 
                      stop: float, volume: float) -> Tuple[bool, str]:
        """
        Valida si se puede ejecutar una operación
        
        Returns:
            (bool, str): (Aprobado, Razón)
        """
        try:
            # 🔥 1. VERIFICAR CAPITAL
            if self.current_account_size <= 0:
                return False, "Capital insuficiente"
            
            # 🔥 2. VERIFICAR DRAWDOWN
            if not self._check_drawdown():
                return False, f"Drawdown máximo excedido ({self.current_drawdown:.2%})"
            
            # 🔥 3. VERIFICAR PÉRDIDA DIARIA
            if not self._check_daily_loss():
                return False, f"Pérdida diaria máxima excedida ({abs(self.daily_pnl):.2f})"
            
            # 🔥 4. VERIFICAR PÉRDIDAS CONSECUTIVAS
            if not self._check_consecutive_losses():
                return False, f"Pérdidas consecutivas ({self.consecutive_losses}) excedidas"
            
            # 🔥 5. VERIFICAR RIESGO POR SÍMBOLO
            if not self._check_symbol_risk(symbol, volume):
                return False, f"Riesgo máximo para {symbol} excedido"
            
            # 🔥 6. VERIFICAR RIESGO DE CORRELACIÓN
            if not self._check_correlation_risk(symbol):
                return False, f"Riesgo de correlación para {symbol}"
            
            # 🔥 7. VERIFICAR RIESGO DE LA OPERACIÓN
            risk_amount = abs(price - stop) * volume
            risk_pct = risk_amount / self.current_account_size
            
            if risk_pct > self.risk_per_trade * 2:  # Máximo 2x el riesgo base
                return False, f"Riesgo de operación demasiado alto ({risk_pct:.2%})"
            
            return True, "Validación aprobada"
            
        except Exception as e:
            logger.error(f"Error en validate_trade: {e}")
            return False, f"Error en validación: {e}"
    
    # ==========================================================
    # CÁLCULO DE VOLUMEN ADAPTATIVO
    # ==========================================================
    
    def calculate_position_size(self, symbol: str, price: float, stop: float,
                                volatility: float = None) -> float:
        """
        Calcula el tamaño de posición adaptativo
        
        Args:
            symbol: Símbolo
            price: Precio de entrada
            stop: Stop Loss
            volatility: Volatilidad (opcional, para ajuste)
        
        Returns:
            float: Tamaño de posición recomendado
        """
        try:
            # 🔥 1. CALCULAR RIESGO BASE
            risk_amount = self.current_account_size * self.risk_per_trade
            
            # 🔥 2. CALCULAR RIESGO POR UNIDAD
            risk_per_unit = abs(price - stop)
            if risk_per_unit == 0:
                return 0
            
            # 🔥 3. CALCULAR VOLUMEN BASE
            base_volume = risk_amount / risk_per_unit
            
            # 🔥 4. AJUSTAR POR VOLATILIDAD
            if volatility:
                # Volatilidad alta = reducir tamaño
                if volatility > 0.02:  # 2% volatilidad diaria
                    volatility_factor = 0.5
                elif volatility > 0.01:  # 1% volatilidad diaria
                    volatility_factor = 0.75
                else:
                    volatility_factor = 1.0
            else:
                volatility_factor = 1.0
            
            # 🔥 5. AJUSTAR POR DRAWDOWN ACTUAL
            if self.current_drawdown > 0.05:  # Si estamos en drawdown > 5%
                drawdown_factor = 1 - (self.current_drawdown / 0.15)
                drawdown_factor = max(0.3, min(1.0, drawdown_factor))
            else:
                drawdown_factor = 1.0
            
            # 🔥 6. AJUSTAR POR RACHA DE PÉRDIDAS
            if self.consecutive_losses > 0:
                loss_factor = 1 / (1 + self.consecutive_losses * 0.3)
                loss_factor = max(0.3, loss_factor)
            else:
                loss_factor = 1.0
            
            # 🔥 7. VOLUMEN FINAL
            final_volume = base_volume * volatility_factor * drawdown_factor * loss_factor
            
            # 🔥 8. LIMITAR VOLUMEN
            # Límite superior (protección)
            max_volume = self._get_max_volume(symbol)
            final_volume = min(final_volume, max_volume)
            
            # Límite inferior (mínimo operativo)
            min_volume = 0.01 if symbol in self._get_forex_symbols() else 1
            final_volume = max(final_volume, min_volume)
            
            # Redondear según el tipo
            if symbol in self._get_forex_symbols():
                final_volume = round(final_volume, 2)
            else:
                final_volume = round(final_volume)
            
            logger.debug(f"📊 Tamaño posición {symbol}: {final_volume}")
            logger.debug(f"   Base: {base_volume:.2f}, Vol: {volatility_factor:.2f}")
            logger.debug(f"   DD: {drawdown_factor:.2f}, Loss: {loss_factor:.2f}")
            
            return final_volume
            
        except Exception as e:
            logger.error(f"Error calculando tamaño posición: {e}")
            return 0
    
    def _get_max_volume(self, symbol: str) -> float:
        """
        Obtiene el volumen máximo permitido para un símbolo
        """
        if symbol in self._get_forex_symbols():
            return 10.0  # 10 lotes máximo para Forex
        else:
            return 100.0  # 100 acciones máximo para stocks
    
    def _get_forex_symbols(self) -> List[str]:
        """Retorna lista de símbolos Forex"""
        return ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
                'AUDJPY', 'AUDNZD', 'CADJPY', 'CHFJPY', 'EURAUD',
                'EURCHF', 'EURGBP', 'EURJPY', 'GBPAUD', 'GBPCAD',
                'GBPCHF', 'GBPJPY', 'NZDCAD', 'NZDJPY', 'NZDUSD',
                'USDCHF']
    
    # ==========================================================
    # CHECKS DE RIESGO
    # ==========================================================
    
    def _check_drawdown(self) -> bool:
        """
        Verifica si se ha excedido el drawdown máximo
        """
        if self.peak_equity <= 0:
            return True
        
        self.current_drawdown = (self.peak_equity - self.current_account_size) / self.peak_equity
        
        if self.current_drawdown > self.max_drawdown_pct:
            logger.warning(f"⚠️ Drawdown excedido: {self.current_drawdown:.2%}")
            return False
        
        return True
    
    def _check_daily_loss(self) -> bool:
        """
        Verifica si se ha excedido la pérdida diaria máxima
        """
        if self.daily_start_equity <= 0:
            return True
        
        daily_loss_pct = self.daily_pnl / self.daily_start_equity
        
        if daily_loss_pct < -self.max_daily_loss_pct:
            logger.warning(f"⚠️ Pérdida diaria excedida: {daily_loss_pct:.2%}")
            return False
        
        return True
    
    def _check_consecutive_losses(self) -> bool:
        """
        Verifica si se ha excedido el número de pérdidas consecutivas
        """
        if self.consecutive_losses >= self.max_consecutive_losses:
            logger.warning(f"⚠️ {self.consecutive_losses} pérdidas consecutivas")
            return False
        
        return True
    
    def _check_symbol_risk(self, symbol: str, volume: float) -> bool:
        """
        Verifica el riesgo máximo por símbolo
        """
        # Calcular exposición actual al símbolo
        current_exposure = self.symbol_limits.get(symbol, {}).get('current_volume', 0)
        total_exposure = current_exposure + volume
        
        # Calcular valor monetario
        symbol_value = total_exposure * 100  # Simplificado
        risk_pct = symbol_value / self.current_account_size
        
        if risk_pct > self.max_risk_per_symbol:
            logger.warning(f"⚠️ Riesgo por símbolo excedido: {risk_pct:.2%}")
            return False
        
        return True
    
    def _check_correlation_risk(self, symbol: str) -> bool:
        """
        Verifica el riesgo de correlación con posiciones existentes
        """
        # Obtener posiciones actuales (simplificado, debería venir de PositionManager)
        current_positions = self._get_current_positions()
        
        correlated_count = 0
        for pos in current_positions:
            if self._are_correlated(symbol, pos['symbol']):
                correlated_count += 1
        
        # Máximo 2 posiciones en el mismo grupo correlacionado
        if correlated_count >= 2:
            logger.warning(f"⚠️ Demasiadas posiciones correlacionadas con {symbol}")
            return False
        
        return True
    
    def _get_current_positions(self) -> List[Dict]:
        """
        Obtiene posiciones actuales (simplificado)
        """
        # TODO: Integrar con PositionManager
        return []
    
    # ==========================================================
    # ACTUALIZACIÓN DE ESTADO
    # ==========================================================
    
    def update_equity(self, current_equity: float):
        """
        Actualiza el equity actual y el peak
        """
        self.current_account_size = current_equity
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # Actualizar drawdown
        self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0
        self.drawdown_history.append({
            'timestamp': datetime.now(),
            'equity': current_equity,
            'drawdown': self.current_drawdown
        })
    
    def register_trade(self, symbol: str, action: str, volume: float,
                      entry: float, exit: float, pnl: float):
        """
        Registra una operación para estadísticas
        """
        trade = {
            'symbol': symbol,
            'action': action,
            'volume': volume,
            'entry': entry,
            'exit': exit,
            'pnl': pnl,
            'timestamp': datetime.now()
        }
        
        self.trades.append(trade)
        self.total_pnl += pnl
        
        # Actualizar estadísticas
        if pnl > 0:
            self.win_count += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Actualizar exposición del símbolo
        if symbol not in self.symbol_limits:
            self.symbol_limits[symbol] = {'current_volume': 0}
        
        if action == 'BUY':
            self.symbol_limits[symbol]['current_volume'] += volume
        else:
            self.symbol_limits[symbol]['current_volume'] -= volume
    
    def reset_daily_stats(self):
        """
        Reinicia estadísticas diarias
        """
        self.daily_pnl = 0
        self.daily_start_equity = self.current_account_size
    
    # ==========================================================
    # MÉTRICAS Y REPORTES
    # ==========================================================
    
    def get_metrics(self) -> Dict:
        """
        Obtiene métricas completas de riesgo
        """
        total_trades = len(self.trades)
        win_rate = self.win_count / total_trades if total_trades > 0 else 0
        
        # Calcular Sharpe Ratio (simplificado)
        if total_trades > 0:
            pnls = [t['pnl'] for t in self.trades]
            sharpe = np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0
        else:
            sharpe = 0
        
        return {
            'account_size': self.current_account_size,
            'peak_equity': self.peak_equity,
            'current_drawdown': self.current_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'total_pnl': self.total_pnl,
            'sharpe_ratio': sharpe,
            'daily_pnl': self.daily_pnl,
            'max_positions': self.max_positions,
        }
    
    def print_report(self):
        """
        Imprime reporte de riesgo
        """
        m = self.get_metrics()
        
        print("\n" + "="*60)
        print("📊 REPORTE DE RIESGO")
        print("="*60)
        print(f"💰 Cuenta: ${m['account_size']:.2f}")
        print(f"🏔️  Peak Equity: ${m['peak_equity']:.2f}")
        print(f"📉 Drawdown: {m['current_drawdown']:.2%} / {m['max_drawdown_pct']:.2%}")
        print(f"🔄 Trades: {m['total_trades']}")
        print(f"🎯 Win Rate: {m['win_rate']:.2%} ({m['win_count']}-{m['loss_count']})")
        print(f"📈 Consecutivos: {m['consecutive_wins']}W / {m['consecutive_losses']}L")
        print(f"💰 Total P&L: ${m['total_pnl']:.2f}")
        print(f"📊 Sharpe: {m['sharpe_ratio']:.2f}")
        print(f"📊 Posiciones máximas: {m['max_positions']}")
        print("="*60)
    
    def check_risk_limits(self) -> Dict:
        """
        Verifica todos los límites de riesgo y retorna estado
        """
        return {
            'drawdown_ok': self.current_drawdown < self.max_drawdown_pct,
            'daily_loss_ok': self.daily_pnl > -self.max_daily_loss_pct * self.daily_start_equity,
            'consecutive_losses_ok': self.consecutive_losses < self.max_consecutive_losses,
            'positions_ok': len(self.trades) < self.max_positions,
            'overall_status': 'OK' if all([
                self.current_drawdown < self.max_drawdown_pct,
                self.daily_pnl > -self.max_daily_loss_pct * self.daily_start_equity,
                self.consecutive_losses < self.max_consecutive_losses,
                len(self.trades) < self.max_positions
            ]) else 'WARNING'
        }
    
    # ==========================================================
    # SISTEMA DE PAUSA AUTOMÁTICA
    # ==========================================================
    
    def should_pause_trading(self) -> Tuple[bool, str]:
        """
        Determina si se debe pausar el trading
        
        Returns:
            (bool, str): (Pausar, Razón)
        """
        checks = self.check_risk_limits()
        
        if not checks['drawdown_ok']:
            return True, f"Drawdown excedido ({self.current_drawdown:.2%})"
        
        if not checks['daily_loss_ok']:
            return True, f"Pérdida diaria excedida (${abs(self.daily_pnl):.2f})"
        
        if not checks['consecutive_losses_ok']:
            return True, f"{self.consecutive_losses} pérdidas consecutivas"
        
        if not checks['positions_ok']:
            return True, f"Máximo de posiciones alcanzado ({self.max_positions})"
        
        return False, "Trading activo"
    
    def pause_trading(self):
        """
        Pausa temporalmente el trading
        """
        logger.warning("🛑 Trading pausado por límite de riesgo")
        # TODO: Integrar con MT5Engine para detener ejecución
        # self.engine.running = False
    
    def resume_trading(self):
        """
        Reanuda el trading
        """
        logger.info("▶️ Trading reanudado")
        # TODO: Integrar con MT5Engine
        # self.engine.running = True