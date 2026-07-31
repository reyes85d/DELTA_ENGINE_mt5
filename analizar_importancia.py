# analizar_importancia.py
import joblib
import pandas as pd
import matplotlib.pyplot as plt

def analizar_modelo(symbol="MSFT"):  # Usa el símbolo que quieras
    # Cargar el modelo
    model = joblib.load(f"data/models/{symbol}_model.joblib")
    
    # Verificar si el modelo tiene el atributo feature_importances_
    if hasattr(model, 'feature_importances_'):
        features = ['return_1', 'return_5', 'sma_10', 'sma_20', 'rsi']
        importancias = model.feature_importances_
        
        # Crear DataFrame para visualizar
        df_importancia = pd.DataFrame({
            'Feature': features,
            'Importancia': importancias
        }).sort_values('Importancia', ascending=False)
        
        print(f"\n📊 Importancia de Features para {symbol}:")
        print(df_importancia.to_string(index=False))
        
        # Graficar
        plt.figure(figsize=(10, 6))
        plt.barh(df_importancia['Feature'], df_importancia['Importancia'])
        plt.xlabel('Importancia')
        plt.title(f'Importancia de Features - {symbol}')
        plt.tight_layout()
        plt.savefig(f'{symbol}_feature_importance.png')
        print(f"\n✅ Gráfico guardado: {symbol}_feature_importance.png")
    else:
        print(f"⚠️ El modelo {symbol} no tiene feature_importances_")

if __name__ == "__main__":
    # Analizar MSFT (mejor resultado en backtest)
    analizar_modelo("MSFT")