"""
Configuración de logs para DELTA ENGINE MT5 - CORREGIDO
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Crear carpeta de logs
Path("logs").mkdir(parents=True, exist_ok=True)


def get_logger(name: str = "delta_mt5") -> logging.Logger:
    """Configura y devuelve un logger con soporte UTF-8"""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 🔥 FORMATO SIN EMOJIS (para evitar errores)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola con UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    # 🔥 Forzar encoding UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    logger.addHandler(console_handler)
    
    # Handler para archivo
    file_handler = logging.FileHandler(
        f"logs/delta_mt5_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger