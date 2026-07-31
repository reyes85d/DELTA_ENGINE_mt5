"""
Estrategia de trading para ACCIONES - OPTIMIZADA PARA MT5
Versión basada en backtesting con MSFT, AMZN, GOOG, NVDA
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from engine.market_data import MarketData
from utils.logger import get_logger

# 🔥 IMPORTAR CONFIGURACIÓN
from config import COOLDOWN_MINUTES, MIN_SCORE, USE_AI

# 🔥 IMPORTAR PREDICTOR IA
from ai.predictor import Predictor

logger = get_logger(__name__)


class Strategy:
    """Estrategia OPTIMIZADA para ACCIONES - Basada en backtesting exitoso"""
    
    def __init__(self):
        self.market_data = MarketData()
        self.last_trade_time = {}
        self.cooldown_minutes = COOLDOWN_MINUTES
        
        # 🔥 PARÁMETROS DE CALIDAD OPTIMIZADOS PARA ACCIONES
        self.min_volume_ratio = 1.2
        self.max_spread = 30
        self.min_atr = 0.0005
        self.trend_required = True
        
        # 🔥 PARÁMETROS DE FILTRO OPTIMIZADOS
        self.max_volatility_pct = 5.0
        self.min_adx = 20
        self.max_consecutive_losses = 3
        self.consecutive_losses = 0
        
        # 🔥 PARÁMETROS ESPECÍFICOS POR SÍMBOLO (basados en backtest)
        self.parametros_por_simbolo = {
            'MSFT': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 4.0},
            'AMZN': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 4.5},
            'GOOG': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 4.0},
            'NVDA': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 5.0},
            'AAPL': {'min_score': 30, 'rsi_threshold': 30, 'max_volatility': 3.5},
            'META': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 4.5},
            'NFLX': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 5.0},
            'INTC': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 4.0},
            'JPM': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 3.5},
            'JNJ': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 3.0},
            'V': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 3.5},
            'WMT': {'min_score': 35, 'rsi_threshold': 35, 'max_volatility': 3.0},
        }
        
        # 🔥 SÍMBOLOS EXCLUIDOS (por bajo rendimiento en backtest)
        self.simbolos_excluidos = ['TSLA']
        
        # 🔥 ESTADÍSTICAS DE RENDIMIENTO
        self.trades_history = []
        self.win_count = 0
        self.loss_count = 0
        
        # 🔥 INICIALIZAR IA
        self.use_ai = USE_AI
        self.predictor = Predictor() if USE_AI else None
        
        if self.use_ai:
            if self.predictor and self.predictor.is_ready():
                modelos = self.predictor.get_loaded_symbols()
                logger.info(f"✅ IA activada con modelos para: {modelos}")
                logger.info(f"📊 Símbolos excluidos: {self.simbolos_excluidos}")
            else:
                logger.warning("⚠️ IA activada pero sin modelos. Entrena con: python entrenar_modelos.py")
    
    def analyze_symbols(self, symbols: list) -> list:
        """Analiza una lista de símbolos y devuelve señales (solo acciones)"""
        signals = []
        for symbol in symbols:
            # 🔥 EXCLUIR SÍMBOLOS CON MAL RENDIMIENTO
            if symbol in self.simbolos_excluidos:
                continue
            
            # 🔥 VERIFICAR QUE SEA ACCIÓN (no Forex)
            if not self._es_accion(symbol):
                continue
                
            signal = self.analyze_symbol(symbol)
            if signal:
                signals.append(signal)
        return signals
    
    def _es_accion(self, symbol: str) -> bool:
        """Verifica si el símbolo es una acción (no Forex)"""
        # Lista de símbolos Forex para excluir
        forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
                        'USDCHF', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY',
                        'AUDJPY', 'AUDNZD', 'EURAUD', 'EURCHF', 'GBPAUD',
                        'GBPCAD', 'GBPCHF', 'CADJPY', 'CHFJPY', 'NZDJPY',
                        'NZDCAD']
        return symbol not in forex_symbols
    
    def _get_parametros_simbolo(self, symbol: str) -> dict:
        """Obtiene parámetros específicos para cada símbolo"""
        if symbol in self.parametros_por_simbolo:
            return self.parametros_por_simbolo[symbol]
        # Parámetros por defecto para acciones no listadas
        return {
            'min_score': MIN_SCORE,
            'rsi_threshold': 35,
            'max_volatility': 4.0
        }
    
    def analyze_symbol(self, symbol: str) -> dict:
        """
        Analiza un símbolo y devuelve una señal - OPTIMIZADO PARA ACCIONES
        """
        try:
            # 🔥 VERIFICAR COOLDOWN
            if symbol in self.last_trade_time:
                time_since = (datetime.now() - self.last_trade_time[symbol]).total_seconds() / 60
                if time_since < self.cooldown_minutes:
                    return None
            
            # 🔥 OBTENER PARÁMETROS ESPECÍFICOS DEL SÍMBOLO
            params = self._get_parametros_simbolo(symbol)
            min_score = params.get('min_score', MIN_SCORE)
            rsi_threshold = params.get('rsi_threshold', 35)
            max_volatility = params.get('max_volatility', 4.0)
            
            # 🔥 OBTENER DATOS
            data = self.market_data.get_rates(symbol, timeframe='M5', count=300)
            if data.empty:
                return None
            
            # 🔥 CALCULAR INDICADORES
            data = self._calculate_indicators(data)
            
            # Último valor
            last = data.iloc[-1]
            price = last['close']
            atr = last.get('atr', 0.001)
            
            # 🔥 FILTROS DE CALIDAD AVANZADOS (con parámetros específicos)
            if not self._filtros_calidad(data, symbol, max_volatility):
                return None
            
            # 🔥 1. SCORE DE REGLAS
            rule_score = self._calculate_score(data, rsi_threshold)
            
            # 🔥 2. PREDICCIÓN IA
            ai_signal = 'NEUTRAL'
            ai_confidence = 0
            ai_score = 0
            
            if self.use_ai and self.predictor and self.predictor.is_ready():
                features = {
                    'return_1': last.get('return_1', 0),
                    'return_5': last.get('return_5', 0),
                    'sma_10': last.get('sma_10', price),
                    'sma_20': last.get('sma_20', price),
                    'rsi': last.get('rsi', 50),
                }
                
                ai_result = self.predictor.predict(symbol, features)
                ai_signal = ai_result.get('signal', 'NEUTRAL')
                ai_confidence = ai_result.get('confidence', 0)
                ai_score = ai_result.get('score', 0)
                
                logger.debug(f"🤖 {symbol}: IA={ai_signal} (conf:{ai_confidence:.2%}, score:{ai_score:.1f})")
            
            # 🔥 3. FILTROS DE TENDENCIA (OPTIMIZADOS)
            is_bullish = last['close'] > last['sma_50']
            is_bearish = last['close'] < last['sma_50']
            
            # 🔥 4. VERIFICAR DRAWDOWN MÁXIMO
            if not self._check_drawdown_limit():
                logger.warning(f"⏸️ Drawdown máximo alcanzado, pausando operaciones")
                return None
            
            # 🔥 5. DECISIÓN FINAL OPTIMIZADA
            action = "NEUTRAL"
            final_confidence = 0
            
            # 🔥 CASO 1: IA dice COMPRA con score alto
            if ai_signal == 'BUY' and ai_score >= min_score:
                if is_bullish or ai_score >= 50:
                    action = 'BUY'
                    final_confidence = ai_confidence
                    logger.info(f"🟢 {symbol}: COMPRA por IA | Score={ai_score:.1f} | Conf={ai_confidence:.2%} | Tendencia={'🟢' if is_bullish else '⚪'}")
            
            # 🔥 CASO 2: IA dice VENTA con score alto
            elif ai_signal == 'SELL' and ai_score >= min_score:
                if is_bearish or ai_score >= 50:
                    action = 'SELL'
                    final_confidence = ai_confidence
                    logger.info(f"🔴 {symbol}: VENTA por IA | Score={ai_score:.1f} | Conf={ai_confidence:.2%} | Tendencia={'🔴' if is_bearish else '⚪'}")
            
            # 🔥 CASO 3: IA tiene score muy alto pero dice NEUTRAL (usar reglas)
            elif ai_score >= 55 and ai_signal == 'NEUTRAL':
                if rule_score > 0 and is_bullish:
                    action = 'BUY'
                    final_confidence = 0.6
                    logger.info(f"🟢 {symbol}: COMPRA por reglas (IA neutral) | Score={ai_score:.1f} | Rule={rule_score}")
                elif rule_score < 0 and is_bearish:
                    action = 'SELL'
                    final_confidence = 0.6
                    logger.info(f"🔴 {symbol}: VENTA por reglas (IA neutral) | Score={ai_score:.1f} | Rule={rule_score}")
            
            # 🔥 CASO 4: Score combinado (IA + Reglas) - FALLBACK OPTIMIZADO
            else:
                rule_score_norm = (rule_score + 100) / 200
                if ai_score > 0:
                    combined_score = (ai_score / 70) * 0.7 + rule_score_norm * 0.3
                else:
                    combined_score = rule_score_norm
                final_score = combined_score * 70
                
                if final_score >= min_score:
                    if is_bullish and rule_score > 0:
                        action = 'BUY'
                        final_confidence = combined_score
                        logger.info(f"🟢 {symbol}: COMPRA combinada | Score={final_score:.1f} | IA={ai_score:.1f} | Rule={rule_score}")
                    elif is_bearish and rule_score < 0:
                        action = 'SELL'
                        final_confidence = combined_score
                        logger.info(f"🔴 {symbol}: VENTA combinada | Score={final_score:.1f} | IA={ai_score:.1f} | Rule={rule_score}")
            
            # 🔥 FILTRO DE CONFIANZA
            if final_confidence < 0.55:
                if action != "NEUTRAL":
                    logger.debug(f"⏭️ {symbol}: Confianza baja ({final_confidence:.2%}), omitiendo")
                action = "NEUTRAL"
            
            # 🔥 NO DUPLICAR POSICIONES
            if action != "NEUTRAL":
                if self._has_open_position(symbol):
                    logger.info(f"⏭️ {symbol}: Ya tiene posición abierta, omitiendo señal")
                    return None
                
                self.last_trade_time[symbol] = datetime.now()
                
                return {
                    'symbol': symbol,
                    'action': action,
                    'price': price,
                    'score': ai_score,
                    'rule_score': rule_score,
                    'ai_score': ai_score,
                    'atr': atr,
                    'confidence': final_confidence,
                    'ai_signal': ai_signal,
                    'ai_confidence': ai_confidence,
                    'trend': 'BULLISH' if is_bullish else 'BEARISH',
                    'params': params
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analizando {symbol}: {e}")
            return None

    # ==========================================================
    # 🔥 FILTROS DE CALIDAD OPTIMIZADOS
    # ==========================================================
    
    def _filtros_calidad(self, data: pd.DataFrame, symbol: str, max_volatility: float = 4.0) -> bool:
        """
        Filtros avanzados optimizados para acciones
        """
        try:
            last = data.iloc[-1]
            
            # 1. FILTRO DE VOLATILIDAD (ajustable por símbolo)
            atr_pct = last.get('atr_pct', 0)
            if atr_pct < 0.3 or atr_pct > max_volatility:
                logger.debug(f"⚠️ {symbol}: Volatilidad fuera de rango: {atr_pct:.2f}% (max: {max_volatility}%)")
                return False
            
            # 2. FILTRO DE ADX (confirmar tendencia)
            adx = last.get('adx', 0)
            if adx < self.min_adx:
                logger.debug(f"⚠️ {symbol}: ADX bajo ({adx:.1f}) - Sin tendencia")
                return False
            
            # 3. FILTRO DE VOLUMEN
            if 'volume_ratio' in last:
                volume_ratio = last['volume_ratio']
                if volume_ratio < self.min_volume_ratio:
                    logger.debug(f"⚠️ {symbol}: Volumen bajo: {volume_ratio:.2f}")
                    return False
            
            # 4. FILTRO DE SPREAD
            if hasattr(self.market_data, 'get_spread'):
                spread = self.market_data.get_spread(symbol)
                if spread > self.max_spread:
                    logger.debug(f"⚠️ {symbol}: Spread alto: {spread}")
                    return False
            
            # 5. FILTRO DE HORARIO (ACCIONES: 9:30-16:00 ET)
            if not self._horario_acciones():
                logger.debug("⚠️ Fuera de horario de trading de acciones")
                return False
            
            # 6. FILTRO DE MOMENTUM OPTIMIZADO
            if 'rsi' in last:
                rsi = last['rsi']
                # Para acciones, RSI extremo puede ser buena señal
                # pero esperamos confirmación
                if rsi < 15 or rsi > 85:
                    logger.debug(f"⚠️ {symbol}: RSI extremo ({rsi:.1f}) - Esperar confirmación")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error en filtros de calidad: {e}")
            return True  # Si falla, permitir paso
    
    def _horario_acciones(self) -> bool:
        """
        Verifica si estamos en horario de trading de acciones
        NYSE/NASDAQ: 9:30 AM - 4:00 PM ET (14:30-21:00 UTC)
        """
        now = datetime.now()
        hour_utc = now.hour + (now.minute / 60)
        
        # Horario de acciones: 14:30-21:00 UTC
        # Añadimos 15 minutos de margen para apertura/cierre
        return 14.75 <= hour_utc <= 21.0
    
    def _check_drawdown_limit(self) -> bool:
        """
        Verifica si se ha excedido el límite de drawdown
        """
        if len(self.trades_history) < 10:
            return True
        
        # Calcular drawdown de las últimas 10 operaciones
        recent_trades = self.trades_history[-10:]
        pnls = [t.get('pnl', 0) for t in recent_trades if 'pnl' in t]
        
        if not pnls:
            return True
        
        # Calcular pérdidas consecutivas
        consecutive_losses = 0
        for pnl in reversed(pnls):
            if pnl < 0:
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= self.max_consecutive_losses:
            logger.warning(f"⚠️ {consecutive_losses} pérdidas consecutivas, pausando")
            return False
        
        return True
    
    def register_trade_result(self, pnl: float):
        """Registra el resultado de una operación para estadísticas"""
        self.trades_history.append({
            'timestamp': datetime.now(),
            'pnl': pnl
        })
        
        if pnl > 0:
            self.win_count += 1
            self.consecutive_losses = 0
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
    
    def get_performance_metrics(self) -> dict:
        """Obtiene métricas de rendimiento"""
        total_trades = len(self.trades_history)
        if total_trades == 0:
            return {'message': 'Sin operaciones aún'}
        
        win_rate = self.win_count / total_trades if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate,
            'consecutive_losses': self.consecutive_losses
        }

    # ==========================================================
    # MÉTODOS DE DIAGNÓSTICO
    # ==========================================================

    def debug_symbol(self, symbol: str):
        """Método de diagnóstico optimizado para acciones"""
        if symbol in self.simbolos_excluidos:
            print(f"❌ {symbol} está excluido del trading")
            return
        
        params = self._get_parametros_simbolo(symbol)
        
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG ANALIZANDO {symbol} (ACCION)")
        print(f"{'='*60}")
        print(f"📋 Parámetros: MIN_SCORE={params.get('min_score', MIN_SCORE)}, RSI_TH={params.get('rsi_threshold', 35)}")
        
        # Obtener datos
        data = self.market_data.get_rates(symbol, timeframe='M5', count=300)
        if data.empty:
            print("❌ No hay datos")
            return
        
        # Calcular indicadores
        data = self._calculate_indicators(data)
        last = data.iloc[-1]
        price = last['close']
        
        print(f"\n📊 DATOS ACTUALES:")
        print(f"  Precio: {price:.5f}")
        print(f"  RSI: {last.get('rsi', 0):.2f}")
        print(f"  ADX: {last.get('adx', 0):.2f}")
        print(f"  ATR%: {last.get('atr_pct', 0):.2f}%")
        print(f"  SMA20: {last.get('sma_20', 0):.5f}")
        print(f"  SMA50: {last.get('sma_50', 0):.5f}")
        print(f"  Return_1: {last.get('return_1', 0):.4f}%")
        print(f"  Return_5: {last.get('return_5', 0):.4f}%")
        
        # Verificar filtros
        print(f"\n🔍 FILTROS DE CALIDAD:")
        filtros_pasan = self._filtros_calidad(data, symbol, params.get('max_volatility', 4.0))
        print(f"  ✅ Filtros superados: {filtros_pasan}")
        
        # 1. Calcular rule_score
        rule_score = self._calculate_score(data, params.get('rsi_threshold', 35))
        print(f"\n📊 RULE SCORE: {rule_score}/100")
        
        # 2. Predicción IA
        ai_signal = 'NEUTRAL'
        ai_confidence = 0
        ai_score = 0
        
        if self.use_ai and self.predictor and self.predictor.is_ready():
            features = {
                'return_1': last.get('return_1', 0),
                'return_5': last.get('return_5', 0),
                'sma_10': last.get('sma_10', price),
                'sma_20': last.get('sma_20', price),
                'rsi': last.get('rsi', 50),
            }
            
            print(f"\n🤖 FEATURES PARA IA:")
            for key, value in features.items():
                print(f"  {key}: {value:.4f}")
            
            ai_result = self.predictor.predict(symbol, features)
            ai_signal = ai_result.get('signal', 'NEUTRAL')
            ai_confidence = ai_result.get('confidence', 0)
            ai_score = ai_result.get('score', 0)
            
            print(f"\n🤖 RESULTADO IA:")
            print(f"  Señal: {ai_signal}")
            print(f"  Score: {ai_score:.1f}/70")
            print(f"  Confianza: {ai_confidence:.2%}")
        
        # 3. Verificar condiciones
        is_bullish = last['close'] > last['sma_50']
        
        print(f"\n📈 CONDICIONES:")
        print(f"  Tendencia: {'🟢 ALCISTA' if is_bullish else '🔴 BAJISTA'}")
        
        # 4. Decisión final
        min_score = params.get('min_score', MIN_SCORE)
        print(f"\n🎯 DECISIÓN FINAL (MIN_SCORE={min_score}):")
        
        # Determinar si debería comprar
        should_buy = False
        reason = ""
        
        if ai_signal == 'BUY' and ai_score >= min_score:
            if is_bullish or ai_score >= 50:
                should_buy = True
                reason = "IA dice BUY con score alto"
            else:
                reason = "IA dice BUY pero no hay tendencia y score < 50"
        elif ai_score >= 55 and ai_signal == 'NEUTRAL':
            if rule_score > 0 and is_bullish:
                should_buy = True
                reason = "IA score muy alto, reglas positivas"
            else:
                reason = "IA score alto pero reglas o tendencia negativas"
        else:
            reason = "No cumple condiciones"
        
        print(f"  ¿Debería COMPRAR? {should_buy}")
        print(f"  Razón: {reason}")
        
        return should_buy

    def _has_open_position(self, symbol: str) -> bool:
        """Verifica si ya hay una posición abierta para el símbolo"""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=symbol)
            return len(positions) > 0
        except:
            return False
    
    def analyze_symbol_with_data(self, symbol: str, data: pd.DataFrame) -> dict:
        """Analiza un símbolo con datos ya cargados (para backtesting)"""
        try:
            # Excluir símbolos no deseados
            if symbol in self.simbolos_excluidos:
                return None
            
            # Calcular indicadores
            data = self._calculate_indicators(data)
            if data.empty:
                return None
            
            last = data.iloc[-1]
            price = last['close']
            atr = last.get('atr', 0.001)
            
            # Obtener parámetros específicos
            params = self._get_parametros_simbolo(symbol)
            min_score = params.get('min_score', MIN_SCORE)
            rsi_threshold = params.get('rsi_threshold', 35)
            
            # Calcular score
            rule_score = self._calculate_score(data, rsi_threshold)
            
            # PREDICCIÓN IA
            ai_signal = 'NEUTRAL'
            ai_confidence = 0
            ai_score = 0
            
            if self.use_ai and self.predictor and self.predictor.is_ready():
                features = {
                    'return_1': last.get('return_1', 0),
                    'return_5': last.get('return_5', 0),
                    'sma_10': last.get('sma_10', price),
                    'sma_20': last.get('sma_20', price),
                    'rsi': last.get('rsi', 50),
                }
                
                ai_result = self.predictor.predict(symbol, features)
                ai_signal = ai_result.get('signal', 'NEUTRAL')
                ai_confidence = ai_result.get('confidence', 0)
                ai_score = ai_result.get('score', 0)
            
            # FILTROS DE TENDENCIA
            is_bullish = last['close'] > last['sma_50']
            is_bearish = last['close'] < last['sma_50']
            
            # Decisión final
            action = "NEUTRAL"
            final_confidence = 0
            
            if ai_signal == 'BUY' and ai_score >= min_score:
                if is_bullish or ai_score >= 50:
                    action = 'BUY'
                    final_confidence = ai_confidence
            elif ai_signal == 'SELL' and ai_score >= min_score:
                if is_bearish or ai_score >= 50:
                    action = 'SELL'
                    final_confidence = ai_confidence
            elif ai_score >= 55 and ai_signal == 'NEUTRAL':
                if rule_score > 0 and is_bullish:
                    action = 'BUY'
                    final_confidence = 0.6
                elif rule_score < 0 and is_bearish:
                    action = 'SELL'
                    final_confidence = 0.6
            else:
                rule_score_norm = (rule_score + 100) / 200
                if ai_score > 0:
                    combined_score = (ai_score / 70) * 0.7 + rule_score_norm * 0.3
                else:
                    combined_score = rule_score_norm
                final_score = combined_score * 70
                
                if final_score >= min_score:
                    if is_bullish and rule_score > 0:
                        action = 'BUY'
                        final_confidence = combined_score
                    elif is_bearish and rule_score < 0:
                        action = 'SELL'
                        final_confidence = combined_score
            
            if final_confidence < 0.55:
                action = "NEUTRAL"
            
            if action != "NEUTRAL":
                return {
                    'symbol': symbol,
                    'action': action,
                    'price': price,
                    'score': ai_score,
                    'rule_score': rule_score,
                    'ai_score': ai_score,
                    'atr': atr,
                    'confidence': final_confidence,
                    'ai_signal': ai_signal,
                    'ai_confidence': ai_confidence,
                    'trend': 'BULLISH' if is_bullish else 'BEARISH'
                }
            return None
            
        except Exception as e:
            logger.error(f"Error analizando {symbol} en backtest: {e}")
            return None
    
    # ==========================================================
    # INDICADORES TÉCNICOS
    # ==========================================================
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos avanzados"""
        df = data.copy()
        
        # Medias Móviles
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['rsi_21'] = self._calculate_rsi(df['close'], 21)
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        df['atr'] = self._calculate_atr(df, 14)
        df['atr_pct'] = (df['atr'] / df['close']) * 100
        
        # Volumen
        if 'tick_volume' in df.columns:
            df['volume_sma'] = df['tick_volume'].rolling(20).mean()
            df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
        
        # Estocástico
        low_min = df['low'].rolling(14).min()
        high_max = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # ADX
        df['adx'] = self._calculate_adx(df, 14)
        
        # Retornos
        df['return_1'] = df['close'].pct_change(1) * 100
        df['return_5'] = df['close'].pct_change(5) * 100
        df['return_10'] = df['close'].pct_change(10) * 100
        
        # Soporte/Resistencia
        df['high_20'] = df['high'].rolling(20).max()
        df['low_20'] = df['low'].rolling(20).min()
        df['range_20'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'])
        
        df['high_50'] = df['high'].rolling(50).max()
        df['low_50'] = df['low'].rolling(50).min()
        df['range_50'] = (df['close'] - df['low_50']) / (df['high_50'] - df['low_50'])
        
        df = df.dropna()
        return df
    
    def _calculate_score(self, data: pd.DataFrame, rsi_threshold: int = 35) -> int:
        """Calcula el score basado en indicadores avanzados (optimizado)"""
        last = data.iloc[-1]
        score = 0
        
        # 1. Cruce de medias (15 pts) - MANTENIDO
        if last['sma_20'] > last['sma_50']:
            score += 10
            if last['sma_20'] > last['sma_200']:
                score += 5
        else:
            score -= 10
            if last['sma_20'] < last['sma_200']:
                score -= 5
        
        # 2. RSI (15 pts) - OPTIMIZADO CON THRESHOLD VARIABLE
        if last['rsi'] < rsi_threshold:
            score += 15
        elif last['rsi'] < rsi_threshold + 10:
            score += 10
        elif last['rsi'] > 75:
            score -= 15
        elif last['rsi'] > 65:
            score -= 10
        else:
            score += 5
        
        # 3. MACD (15 pts) - MANTENIDO
        if last['macd_histogram'] > 0:
            score += 10
            if len(data) > 3 and last['macd_histogram'] > data['macd_histogram'].iloc[-3]:
                score += 5
        else:
            score -= 10
            if len(data) > 3 and last['macd_histogram'] < data['macd_histogram'].iloc[-3]:
                score -= 5
        
        # 4. Bollinger Bands (10 pts) - MANTENIDO
        if last['bb_position'] < 0.15:
            score += 10
        elif last['bb_position'] > 0.85:
            score -= 10
        else:
            score += 3
        
        # 5. Estocástico (10 pts) - MANTENIDO
        if last['stoch_k'] < 15 and last['stoch_d'] < 15:
            score += 10
        elif last['stoch_k'] > 85 and last['stoch_d'] > 85:
            score -= 10
        else:
            score += 3
        
        # 6. ADX (10 pts) - MANTENIDO
        if last['adx'] > 25:
            if last['close'] > last['sma_20']:
                score += 10
            else:
                score -= 10
        
        # 7. Volumen (10 pts) - MANTENIDO
        if 'volume_ratio' in data.columns:
            if last['volume_ratio'] > 1.8:
                score += 10
            elif last['volume_ratio'] > 1.4:
                score += 5
        
        # 8. Soporte/Resistencia (10 pts) - MANTENIDO
        if last['range_20'] < 0.15:
            score += 10
        elif last['range_20'] > 0.85:
            score -= 10
        
        # 9. Retornos (5 pts) - MANTENIDO
        if last['return_5'] > 1:
            score += 5
        elif last['return_5'] < -3:
            score -= 5
        
        score = max(-100, min(100, score))
        return score
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = data['high'] - data['low']
        high_close = (data['high'] - data['close'].shift()).abs()
        low_close = (data['low'] - data['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean()
        return atr
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        try:
            high_low = data['high'] - data['low']
            high_close = (data['high'] - data['close'].shift()).abs()
            low_close = (data['low'] - data['close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            tr = ranges.max(axis=1)
            
            up_move = data['high'] - data['high'].shift()
            down_move = data['low'].shift() - data['low']
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            atr = tr.rolling(period).mean()
            plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / atr)
            minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / atr)
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(period).mean()
            return adx
        except:
            return pd.Series([25] * len(data))
    
    # ==========================================================
    # MÉTODOS DE UTILIDAD
    # ==========================================================
    
    def get_last_trades(self) -> dict:
        return self.last_trade_time
    
    def reset_cooldown(self, symbol: str = None):
        if symbol:
            self.last_trade_time.pop(symbol, None)
        else:
            self.last_trade_time.clear()
    
    def get_ai_status(self) -> dict:
        if not self.use_ai:
            return {'enabled': False, 'status': 'IA desactivada'}
        
        if self.predictor and self.predictor.is_ready():
            return {
                'enabled': True,
                'status': 'Activa',
                'models': self.predictor.get_loaded_symbols()
            }
        
        return {
            'enabled': True,
            'status': 'Sin modelos',
            'models': []
        }

# 1. ¿Es el símbolo una ACCIÓN?
#    ├── Sí → Continuar
#    └── No → Ignorar (Forex excluido)

# 2. ¿Está el símbolo en la lista de EXCLUIDOS? (TSLA)
#    ├── Sí → Ignorar
#    └── No → Continuar

# 3. ¿Estamos en HORARIO DE ACCIONES? (14:45-21:00 UTC)
#    ├── Sí → Continuar
#    └── No → Ignorar

# 4. ¿CUMPLE FILTROS DE CALIDAD?
#    ├── Volatilidad (ATR% entre 0.3% y max_volatility% por símbolo)
#    ├── ADX > 20 (confirmar tendencia)
#    ├── Volumen ratio > 1.2
#    ├── Spread < 30
#    └── RSI no extremo (< 15 o > 85) → Esperar confirmación

# 5. ¿IA dice BUY y Score >= MIN_SCORE (30-35 según símbolo)?
#    ├── Sí → ¿Tendencia alcista (SMA50) o Score >= 50?
#    │   ├── Sí → 🟢 COMPRA (Confianza = Confianza IA)
#    │   └── No → Siguiente caso
#    └── No → Siguiente caso

# 6. ¿IA dice SELL y Score >= MIN_SCORE (30-35 según símbolo)?
#    ├── Sí → ¿Tendencia bajista (SMA50) o Score >= 50?
#    │   ├── Sí → 🔴 VENTA (Confianza = Confianza IA)
#    │   └── No → Siguiente caso
#    └── No → Siguiente caso

# 7. ¿IA Score >= 55 y IA dice NEUTRAL?
#    ├── Sí → ¿Reglas positivas y tendencia alcista?
#    │   ├── Sí → 🟢 COMPRA (Confianza = 0.6)
#    │   └── No → Siguiente caso
#    └── No → Siguiente caso

# 8. SCORE COMBINADO (IA + Reglas)
#    ├── ¿Score combinado >= MIN_SCORE?
#    │   ├── Sí → ¿Tendencia alcista y reglas positivas?
#    │   │   ├── Sí → 🟢 COMPRA (Confianza = Score combinado)
#    │   │   └── No → ¿Tendencia bajista y reglas negativas?
#    │   │       ├── Sí → 🔴 VENTA (Confianza = Score combinado)
#    │   │       └── No → NEUTRAL
#    │   └── No → NEUTRAL
#    └── FIN → NEUTRAL

# 9. FILTRO FINAL DE CONFIANZA
#    ├── ¿Confianza >= 0.55?
#    │   ├── Sí → Ejecutar orden
#    │   └── No → NEUTRAL
#    └── FIN