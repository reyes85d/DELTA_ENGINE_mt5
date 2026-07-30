"""
Dashboard web para DELTA ENGINE MT5
"""

from flask import Flask, render_template, jsonify
import MetaTrader5 as mt5
import time
from datetime import datetime

app = Flask(__name__)


@app.route('/')
def index():
    """Página principal del dashboard"""
    return render_template('dashboard.html')


@app.route('/api/positions')
def get_positions():
    """API para posiciones en tiempo real"""
    if not mt5.initialize():
        return jsonify({'error': 'MT5 no conectado'})
    
    positions = mt5.positions_get()
    data = []
    
    if positions:
        for pos in positions:
            data.append({
                'symbol': pos.symbol,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL'
            })
    
    mt5.shutdown()
    return jsonify(data)


@app.route('/api/account')
def get_account():
    """API para información de cuenta"""
    if not mt5.initialize():
        return jsonify({'error': 'MT5 no conectado'})
    
    account = mt5.account_info()
    data = {
        'balance': account.balance if account else 0,
        'equity': account.equity if account else 0,
        'margin_free': account.margin_free if account else 0,
        'profit': account.profit if account else 0
    }
    
    mt5.shutdown()
    return jsonify(data)


@app.route('/api/status')
def get_status():
    """API para estado del motor"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'positions': len(mt5.positions_get() if mt5.initialize() else [])
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)