"""
Gestión de riesgo para MT5
"""

from typing import Dict, Any
from dataclasses import dataclass

from config import MAX_DAILY_LOSS


@dataclass
class TradeInfo:
    """Información de un trade evaluado"""
    quantity: float
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float


class RiskManager:
    """Gestor de riesgo"""
    
    def __init__(self, account_size: float, risk_per_trade: float, max_positions: int):
        self.account_size = account_size
        self.risk_per_trade = risk_per_trade / 100
        self.max_positions = max_positions
        self.daily_loss = 0.0
        self.daily_trades = 0
    
    def evaluate_trade(self, entry: float, stop: float, target: float, symbol: str) -> TradeInfo:
        """
        Evalúa un trade y calcula el tamaño de lote adecuado
        """
        # Calcular riesgo en pips/precio
        risk_amount = abs(entry - stop)
        reward_amount = abs(target - entry)
        
        # Calcular riesgo/recompensa
        rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        # 🔥 CONVERTIR RIESGO A PIPS
        # Para Forex, 1 pip = 0.0001 (para la mayoría de pares)
        # Para JPY, 1 pip = 0.01
        pip_size = 0.0001
        if symbol.endswith('JPY'):
            pip_size = 0.01
        
        risk_in_pips = risk_amount / pip_size if pip_size > 0 else 1
        
        # 🔥 CALCULAR LOTE BASADO EN RIESGO
        # Valor de 1 pip para 1 lote estándar = 10 USD (aprox)
        pip_value_per_lot = 10.0
        
        # Lotes = (riesgo en USD) / (pips * valor_pip_por_lote)
        max_risk_usd = self.account_size * self.risk_per_trade
        lot_size = max_risk_usd / (risk_in_pips * pip_value_per_lot) if risk_in_pips > 0 else 0.01
        
        # 🔥 LIMITAR LOTES
        lot_size = max(0.01, min(lot_size, 0.1))  # 🔥 MÁXIMO 0.1 LOTES
        
        # 🔥 REDONDEAR A 2 DECIMALES
        lot_size = round(lot_size, 2)
        
        return TradeInfo(
            quantity=lot_size,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            risk_reward_ratio=rr_ratio
        )
        
    def can_open_position(self, current_positions: int) -> bool:
        """Verifica si se puede abrir una nueva posición"""
        return current_positions < self.max_positions
    
    def register_trade(self, pnl: float):
        """Registra un trade para el control diario"""
        if pnl < 0:
            self.daily_loss += abs(pnl)
        self.daily_trades += 1
    
    def reset_daily(self):
        """Reinicia el contador diario"""
        self.daily_loss = 0.0
        self.daily_trades = 0
    
    def exceeded_daily_loss(self) -> bool:
        """Verifica si se superó la pérdida diaria máxima"""
        max_loss = self.account_size * (MAX_DAILY_LOSS / 100)
        return self.daily_loss >= max_loss