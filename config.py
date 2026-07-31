"""
Configuración para DELTA ENGINE - OPTIMIZADA PARA ACCIONES
Basada en resultados de backtesting (MSFT +47%, AMZN +45%, GOOG +40%, NVDA +25%)
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
# TRADING - OPTIMIZADO
# =========================================================
ACCOUNT_SIZE = 10000.0
RISK_PER_TRADE = 0.01  # 🔥 CAMBIADO: 1% (era 100%)
MAX_POSITIONS = 10  # 🔥 CAMBIADO: 10 (era 20)
MAX_POSITIONS_PER_SYMBOL = 1

# 🔥 CANTIDADES POR DEFECTO
DEFAULT_QTY_STOCK = 10
DEFAULT_QTY_FOREX = 0.05

# =========================================================
# 🔥 SL/TP - OPTIMIZADO
# =========================================================
ATR_MULTIPLIER_SL = 2.0
ATR_MULTIPLIER_TP = 3.0

# Para acciones - OPTIMIZADO (basado en backtest)
STOCK_SL_PCT = 0.025   # 🔥 2.5% (era 3%)
STOCK_TP_PCT = 0.05    # 5% (mantenido)

MIN_RISK_REWARD = 2.0  # 🔥 CAMBIADO: 2.0 (era 1.5)
MAX_DAILY_LOSS = 3.0

# =========================================================
# 🔥 ACTIVOS - ACCIONES (OPTIMIZADO)
# =========================================================
STOCKS = [
    # 🔥 TOP RENDIMIENTO (basado en backtest)
    "MSFT", "AMZN", "GOOG", "NVDA",  # +25-47%
    
    # 🔥 RENDIMIENTO MODERADO
    "META",  # +4.60%
    
    # 🔥 PENDIENTES DE BACKTEST
    "AAPL", "NFLX", "INTC", "JPM", "V", "WMT", "JNJ",
    
    # ❌ EXCLUIDOS (mal rendimiento)
    # "TSLA",  # -5.07%
    # "PG",    # No disponible en MT5
]

# =========================================================
# ACTIVOS - FOREX (EXCLUIDOS PARA AHORA)
# =========================================================
FOREX = [
    # 🔥 EXCLUIDOS - Estrategia especializada en acciones
    # "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    # "USDCHF", "NZDUSD",
    # "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "AUDNZD",
    # "EURAUD", "EURCHF", "GBPAUD", "GBPCAD", "GBPCHF",
    # "CADJPY", "CHFJPY", "NZDJPY", "NZDCAD",
]

# =========================================================
# UNIFICAR SÍMBOLOS
# =========================================================
SYMBOLS = STOCKS + FOREX

# =========================================================
# IA / ESTRATEGIA - OPTIMIZADO
# =========================================================
CONFIDENCE_THRESHOLD = 0.55  # 🔥 CAMBIADO: 0.55 (era 0.60)
USE_AI = True
USE_SCORING = True
MIN_SCORE = 35  # 🔥 CAMBIADO: 35 (era 60)

# =========================================================
# SCAN INTERVAL
# =========================================================
SCAN_INTERVAL = 60  # 1 minuto

# =========================================================
# COOLDOWN - OPTIMIZADO
# =========================================================
COOLDOWN_MINUTES = 10  # 🔥 CAMBIADO: 10 min (era 5)