"""
Obtención de datos de mercado desde MT5
"""

import pandas as pd
import MetaTrader5 as mt5
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketData:
    """Obtiene datos de mercado de MT5"""
    
    def __init__(self):
        pass
    
    def get_rates(self, symbol: str, timeframe: str = "M5", count: int = 100) -> pd.DataFrame:
        """
        Obtiene velas de MT5
        
        Args:
            symbol: Símbolo (ej: 'EURUSD')
            timeframe: 'M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1'
            count: Número de velas a obtener
        
        Returns:
            DataFrame con columnas: time, open, high, low, close, tick_volume, spread, real_volume
        """
        try:
            # Mapear timeframe a MT5
            timeframe_map = {
                'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1,
                'MN1': mt5.TIMEFRAME_MN1
            }
            tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
            
            # Obtener datos
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No se obtuvieron datos para {symbol}")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> float:
        """Obtiene el precio actual (Bid) de un símbolo"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return tick.bid
            return 0.0
        except Exception as e:
            logger.error(f"Error obteniendo precio de {symbol}: {e}")
            return 0.0
    
    def get_current_ask(self, symbol: str) -> float:
        """Obtiene el precio Ask de un símbolo"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return tick.ask
            return 0.0
        except Exception as e:
            logger.error(f"Error obteniendo Ask de {symbol}: {e}")
            return 0.0
    
    def get_spread(self, symbol: str) -> int:
        """Obtiene el spread en puntos"""
        try:
            info = mt5.symbol_info(symbol)
            if info:
                return info.spread
            return 0
        except Exception as e:
            logger.error(f"Error obteniendo spread de {symbol}: {e}")
            return 0