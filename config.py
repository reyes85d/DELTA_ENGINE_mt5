"""
Configuración para DELTA ENGINE - MetaTrader 5
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONEXIÓN MT5
# =========================================================
MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# =========================================================
# TRADING
# =========================================================
ACCOUNT_SIZE = 10000.0
RISK_PER_TRADE = 1.0
MAX_POSITIONS = 20
MAX_POSITIONS_PER_SYMBOL = 1

# 🔥 CANTIDADES POR DEFECTO
DEFAULT_QTY_STOCK = 10   # 10 acciones
DEFAULT_QTY_FOREX = 0.05  # 0.05 lotes

# =========================================================
# 🔥 SL/TP
# =========================================================
ATR_MULTIPLIER_SL = 2.0
ATR_MULTIPLIER_TP = 3.0

# Para acciones - porcentaje
STOCK_SL_PCT = 0.03   # 3% stop loss
STOCK_TP_PCT = 0.05   # 5% take profit

MIN_RISK_REWARD = 1.5
MAX_DAILY_LOSS = 3.0

# =========================================================
# 🔥 ACTIVOS - ACCIONES
# =========================================================
STOCKS = [
    "AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA", "META",
    "NFLX", "INTC", "JPM", "V", "WMT", "JNJ", "PG",
]

# =========================================================
# ACTIVOS - FOREX
# =========================================================
FOREX = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD",  # Mayores
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "AUDNZD",  # Cruces
    "EURAUD", "EURCHF", "GBPAUD", "GBPCAD", "GBPCHF",  # Más cruces
    "CADJPY", "CHFJPY", "NZDJPY", "NZDCAD",  # Pares con JPY y CAD
]
# =========================================================
# UNIFICAR SÍMBOLOS
# =========================================================
SYMBOLS = STOCKS + FOREX

# =========================================================
# IA / ESTRATEGIA
# =========================================================
CONFIDENCE_THRESHOLD = 0.60
USE_AI = True
USE_SCORING = True
MIN_SCORE = 60

# =========================================================
# SCAN INTERVAL
# =========================================================
SCAN_INTERVAL = 60

# =========================================================
# COOLDOWN
# =========================================================
COOLDOWN_MINUTES = 5