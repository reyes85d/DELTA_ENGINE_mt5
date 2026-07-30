"""
DELTA ENGINE MT5 - Punto de entrada
"""

from engine.mt5_engine import MT5Engine
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("🚀 DELTA ENGINE para MetaTrader 5")
    logger.info("=" * 70)
    
    engine = MT5Engine()
    
    if not engine.health_check():
        logger.error("❌ Health Check fallido.")
        return
    
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.warning("Interrupción del usuario.")
    except Exception as e:
        logger.exception(f"Error: {e}")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()