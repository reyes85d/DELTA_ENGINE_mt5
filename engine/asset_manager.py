"""
Gestión de activos para MT5 - ACCIONES + FOREX
"""

from config import STOCKS, FOREX, SYMBOLS


class AssetManager:
    """Gestor de activos - Acciones y Forex"""
    
    def __init__(self):
        self.stocks = STOCKS
        self.forex = FOREX
        self.symbols = SYMBOLS
        self._cache = {}
    
    def get_all(self) -> list:
        """Devuelve todos los símbolos"""
        return self.symbols
    
    def get_stocks(self) -> list:
        """Devuelve solo acciones"""
        return self.stocks
    
    def get_forex(self) -> list:
        """Devuelve solo Forex"""
        return self.forex
    
    def get_asset_type(self, symbol: str) -> str:
        """Determina el tipo de activo"""
        if symbol in self.stocks:
            return 'STOCK'
        elif symbol in self.forex:
            return 'FOREX'
        return 'UNKNOWN'
    
    def is_stock(self, symbol: str) -> bool:
        return symbol in self.stocks
    
    def is_forex(self, symbol: str) -> bool:
        return symbol in self.forex
    
    def get_default_quantity(self, symbol: str) -> float:
        """Cantidad por defecto según el tipo de activo"""
        if self.is_stock(symbol):
            return STOCKS  # 10 acciones
        else:
            return FOREX  # 0.05 lotes