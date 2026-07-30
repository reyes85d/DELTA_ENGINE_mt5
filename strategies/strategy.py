"""
Estrategia de trading para MT5 - CON INDICADORES AVANZADOS Y IA - VERSIÓN MEJORADA
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
    """Estrategia mejorada con filtros de calidad"""
    
    def __init__(self):
        self.market_data = MarketData()
        self.last_trade_time = {}
        self.cooldown_minutes = COOLDOWN_MINUTES
        
        # 🔥 PARÁMETROS DE CALIDAD
        self.min_volume_ratio = 1.2
        self.max_spread = 30
        self.min_atr = 0.0005
        self.trend_required = True
        
        # 🔥 INICIALIZAR IA
        self.use_ai = USE_AI
        self.predictor = Predictor() if USE_AI else None
        
        if self.use_ai:
            if self.predictor and self.predictor.is_ready():
                logger.info(f"✅ IA activada con modelos para: {self.predictor.get_loaded_symbols()}")
            else:
                logger.warning("⚠️ IA activada pero sin modelos. Entrena con: python entrenar_modelos.py")
    
    def analyze_symbols(self, symbols: list) -> list:
        """Analiza una lista de símbolos y devuelve señales"""
        signals = []
        for symbol in symbols:
            signal = self.analyze_symbol(symbol)
            if signal:
                signals.append(signal)
        return signals
    
    def analyze_symbol(self, symbol: str) -> dict:
        """
        Analiza un símbolo y devuelve una señal con IA + Scoring - VERSIÓN CORREGIDA
        """
        try:
            # Verificar cooldown
            if symbol in self.last_trade_time:
                time_since = (datetime.now() - self.last_trade_time[symbol]).total_seconds() / 60
                if time_since < self.cooldown_minutes:
                    return None
            
            # Obtener datos
            data = self.market_data.get_rates(symbol, timeframe='M5', count=300)
            if data.empty:
                return None
            
            # Calcular indicadores
            data = self._calculate_indicators(data)
            
            # Último valor
            last = data.iloc[-1]
            price = last['close']
            atr = last.get('atr', 0.001)
            
            # 🔥 1. SCORE DE REGLAS (sistema tradicional)
            rule_score = self._calculate_score(data)
            
            # 🔥 2. PREDICCIÓN IA (XGBoost)
            ai_signal = 'NEUTRAL'
            ai_confidence = 0
            ai_score = 0
            
            if self.use_ai and self.predictor and self.predictor.is_ready():
                # Preparar features para el modelo XGBoost
                features = {
                    'return_1': last.get('return_1', 0),
                    'return_5': last.get('return_5', 0),
                    'sma_10': last.get('sma_10', price),
                    'sma_20': last.get('sma_20', price),
                    'rsi': last.get('rsi', 50),
                }
                
                # Obtener predicción
                ai_result = self.predictor.predict(symbol, features)
                ai_signal = ai_result.get('signal', 'NEUTRAL')
                ai_confidence = ai_result.get('confidence', 0)
                ai_score = ai_result.get('score', 0)  # Score en escala 0-70
                
                # 🔥 LOG PARA VER QUÉ PREDICE LA IA
                logger.info(f"🤖 {symbol}: IA={ai_signal} (conf:{ai_confidence:.2%}, score:{ai_score:.1f})")
            
            # 🔥 3. FILTROS DE TENDENCIA
            is_bullish = last['close'] > last['sma_50']
            is_bearish = last['close'] < last['sma_50']
            
            # 🔥 4. DECISIÓN FINAL - PRIORIZANDO IA
            action = "NEUTRAL"
            final_confidence = 0
            
            # 🔥 NUEVA LÓGICA: La IA tiene más peso
            
            # CASO 1: IA dice COMPRA con score alto
            if ai_signal == 'BUY' and ai_score >= MIN_SCORE:
                # Si hay tendencia alcista O el score es muy alto (>50)
                if is_bullish or ai_score >= 50:
                    action = 'BUY'
                    final_confidence = ai_confidence
                    logger.info(f"🟢 {symbol}: COMPRA por IA | Score={ai_score:.1f} | Conf={ai_confidence:.2%} | Tendencia={'🟢' if is_bullish else '⚪'}")
            
            # CASO 2: IA dice VENTA con score alto
            elif ai_signal == 'SELL' and ai_score >= MIN_SCORE:
                if is_bearish or ai_score >= 50:
                    action = 'SELL'
                    final_confidence = ai_confidence
                    logger.info(f"🔴 {symbol}: VENTA por IA | Score={ai_score:.1f} | Conf={ai_confidence:.2%} | Tendencia={'🔴' if is_bearish else '⚪'}")
            
            # CASO 3: IA tiene score muy alto pero dice NEUTRAL (usar reglas)
            elif ai_score >= 55 and ai_signal == 'NEUTRAL':
                if rule_score > 0 and is_bullish:
                    action = 'BUY'
                    final_confidence = 0.6
                    logger.info(f"🟢 {symbol}: COMPRA por reglas (IA neutral) | Score={ai_score:.1f} | Rule={rule_score}")
                elif rule_score < 0 and is_bearish:
                    action = 'SELL'
                    final_confidence = 0.6
                    logger.info(f"🔴 {symbol}: VENTA por reglas (IA neutral) | Score={ai_score:.1f} | Rule={rule_score}")
            
            # CASO 4: Score combinado (IA + Reglas) - FALLBACK
            else:
                # Normalizar rule_score a escala 0-1 (de -100 a +100)
                rule_score_norm = (rule_score + 100) / 200  # 0-1
                
                # Calcular score combinado (70% IA, 30% reglas)
                if ai_score > 0:
                    combined_score = (ai_score / 70) * 0.7 + rule_score_norm * 0.3
                else:
                    combined_score = rule_score_norm
                
                # Convertir a escala 0-70
                final_score = combined_score * 70
                
                # Si el score combinado supera el threshold
                if final_score >= MIN_SCORE:
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
                # Verificar si ya hay posición abierta
                if self._has_open_position(symbol):
                    logger.info(f"⏭️ {symbol}: Ya tiene posición abierta, omitiendo señal")
                    return None
                
                self.last_trade_time[symbol] = datetime.now()
                
                return {
                    'symbol': symbol,
                    'action': action,
                    'price': price,
                    'score': ai_score,  # Score principal de IA
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
            logger.error(f"Error analizando {symbol}: {e}")
            return None

    def debug_symbol(self, symbol: str):
        """
        Método de diagnóstico para ver por qué no hay señal
        """
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG ANALIZANDO {symbol}")
        print(f"{'='*60}")
        
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
        print(f"  SMA20: {last.get('sma_20', 0):.5f}")
        print(f"  SMA50: {last.get('sma_50', 0):.5f}")
        print(f"  Return_1: {last.get('return_1', 0):.4f}%")
        print(f"  Return_5: {last.get('return_5', 0):.4f}%")
        
        # 1. Calcular rule_score
        rule_score = self._calculate_score(data)
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
        is_bearish = last['close'] < last['sma_50']
        
        print(f"\n📈 CONDICIONES:")
        print(f"  Tendencia: {'🟢 ALCISTA' if is_bullish else '🔴 BAJISTA'}")
        print(f"  ¿Precio > SMA50? {last['close']:.5f} > {last['sma_50']:.5f} = {is_bullish}")
        
        # 4. Verificar si cumple condiciones de compra
        buy_conditions = {
            'ai_signal_buy': ai_signal == 'BUY',
            'rule_score_positive': rule_score > 0,
            'ai_score_threshold': ai_score >= MIN_SCORE,
            'is_bullish': is_bullish,
        }
        
        print(f"\n🎯 CONDICIONES DE COMPRA:")
        for cond, value in buy_conditions.items():
            print(f"  {cond}: {value}")
        
        # 5. Verificar posición abierta
        has_position = self._has_open_position(symbol)
        print(f"\n📊 POSICIÓN ABIERTA: {has_position}")
        
        # 6. Verificar cooldown
        in_cooldown = symbol in self.last_trade_time
        if in_cooldown:
            time_since = (datetime.now() - self.last_trade_time[symbol]).total_seconds() / 60
            print(f"  Cooldown: {time_since:.1f} min (requiere {self.cooldown_minutes} min)")
        
        # 7. Decisión final
        print(f"\n🎯 DECISIÓN FINAL:")
        
        # Calcular score combinado
        rule_score_norm = (rule_score + 100) / 200
        if ai_score > 0:
            combined_score = (ai_score / 70) * 0.7 + rule_score_norm * 0.3
        else:
            combined_score = rule_score_norm
        final_score = combined_score * 70
        
        print(f"  Score combinado: {final_score:.1f}/70")
        
        # Determinar si debería comprar según la nueva lógica
        should_buy = False
        reason = ""
        
        if ai_signal == 'BUY' and ai_score >= MIN_SCORE:
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
        elif final_score >= MIN_SCORE and is_bullish and rule_score > 0:
            should_buy = True
            reason = "Score combinado alto"
        else:
            reason = "No cumple condiciones"
        
        print(f"\n  ¿Debería COMPRAR? {should_buy}")
        print(f"  Razón: {reason}")
        
        if has_position:
            print(f"  ⚠️ PERO ya hay posición abierta")
        
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
        """
        Analiza un símbolo con datos ya cargados (para backtesting)
        """
        try:
            # Calcular indicadores
            data = self._calculate_indicators(data)
            if data.empty:
                return None
            
            last = data.iloc[-1]
            price = last['close']
            atr = last.get('atr', 0.001)
            
            # Calcular score
            rule_score = self._calculate_score(data)
            
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
            
            if ai_signal == 'BUY' and ai_score >= MIN_SCORE:
                if is_bullish or ai_score >= 50:
                    action = 'BUY'
                    final_confidence = ai_confidence
            elif ai_signal == 'SELL' and ai_score >= MIN_SCORE:
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
                
                if final_score >= MIN_SCORE:
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
    
    def _calculate_score(self, data: pd.DataFrame) -> int:
        """Calcula el score basado en indicadores avanzados"""
        last = data.iloc[-1]
        score = 0
        
        # 1. Cruce de medias (15 pts)
        if last['sma_20'] > last['sma_50']:
            score += 10
            if last['sma_20'] > last['sma_200']:
                score += 5
        else:
            score -= 10
            if last['sma_20'] < last['sma_200']:
                score -= 5
        
        # 2. RSI (15 pts) - más exigente
        if last['rsi'] < 25:  # 🔥 Más sobrevendido
            score += 15
        elif last['rsi'] < 35:
            score += 10
        elif last['rsi'] > 75:  # 🔥 Más sobrecomprado
            score -= 15
        elif last['rsi'] > 65:
            score -= 10
        else:
            score += 5
        
        # 3. MACD (15 pts)
        if last['macd_histogram'] > 0:
            score += 10
            if len(data) > 3 and last['macd_histogram'] > data['macd_histogram'].iloc[-3]:
                score += 5
        else:
            score -= 10
            if len(data) > 3 and last['macd_histogram'] < data['macd_histogram'].iloc[-3]:
                score -= 5
        
        # 4. Bollinger Bands (10 pts)
        if last['bb_position'] < 0.15:  # 🔥 Más cerca de banda inferior
            score += 10
        elif last['bb_position'] > 0.85:  # 🔥 Más cerca de banda superior
            score -= 10
        else:
            score += 3
        
        # 5. Estocástico (10 pts) - más exigente
        if last['stoch_k'] < 15 and last['stoch_d'] < 15:
            score += 10
        elif last['stoch_k'] > 85 and last['stoch_d'] > 85:
            score -= 10
        else:
            score += 3
        
        # 6. ADX (10 pts)
        if last['adx'] > 25:
            if last['close'] > last['sma_20']:
                score += 10
            else:
                score -= 10
        
        # 7. Volumen (10 pts) - más exigente
        if 'volume_ratio' in data.columns:
            if last['volume_ratio'] > 1.8:
                score += 10
            elif last['volume_ratio'] > 1.4:
                score += 5
        
        # 8. Soporte/Resistencia (10 pts)
        if last['range_20'] < 0.15:  # 🔥 Más cerca de soporte
            score += 10
        elif last['range_20'] > 0.85:  # 🔥 Más cerca de resistencia
            score -= 10
        
        # 9. Retornos (5 pts) - más exigente
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