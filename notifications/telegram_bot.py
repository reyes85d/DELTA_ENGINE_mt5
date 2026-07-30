"""
Notificaciones por Telegram para DELTA ENGINE MT5
"""

import requests
import json
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramNotifier:
    """Envía notificaciones a Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str):
        """Envía un mensaje simple"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=data)
            if response.status_code == 200:
                logger.info("✅ Notificación enviada")
            else:
                logger.error(f"❌ Error enviando notificación: {response.text}")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
    
    def send_trade_notification(self, trade: dict):
        """Envía notificación de trade"""
        message = f"""
🚀 <b>NUEVO TRADE</b>
📊 Símbolo: {trade.get('symbol', 'N/A')}
📈 Acción: {trade.get('action', 'N/A')}
💲 Precio: ${trade.get('price', 0):.2f}
🎯 Stop Loss: ${trade.get('sl', 0):.2f}
🎯 Take Profit: ${trade.get('tp', 0):.2f}
⏰ Hora: {datetime.now().strftime('%H:%M:%S')}
        """
        self.send_message(message)
    
    def send_daily_report(self, positions: dict, pnl: float):
        """Envía reporte diario"""
        message = f"""
📊 <b>REPORTE DIARIO</b>
💰 P&L Total: ${pnl:.2f}
📊 Posiciones abiertas: {len(positions)}
⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        self.send_message(message)