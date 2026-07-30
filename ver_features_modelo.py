# ver_features_modelo.py
import joblib
import pandas as pd

def ver_features_modelo():
    """Muestra las features que usa el modelo"""
    
    print("\n" + "="*60)
    print("🔍 ANALIZANDO FEATURES DEL MODELO")
    print("="*60)
    
    # Cargar modelo
    modelo = joblib.load('data/models/GOOG_model.joblib')
    
    print(f"\n🤖 Modelo: {type(modelo).__name__}")
    
    # Verificar si tiene el atributo feature_names
    if hasattr(modelo, 'feature_names_in_'):
        print("\n📊 FEATURES QUE ESPERA EL MODELO:")
        print("-"*40)
        for i, feature in enumerate(modelo.feature_names_in_):
            print(f"  {i+1}. {feature}")
        
        print(f"\n✅ Total: {len(modelo.feature_names_in_)} features")
    else:
        print("\n⚠️ El modelo no tiene feature_names_in_")
        print("Intentando obtener de otra forma...")
        
        # Intentar con el scaler
        try:
            scaler = joblib.load('data/models/GOOG_scaler.joblib')
            if hasattr(scaler, 'feature_names_in_'):
                print("\n📊 FEATURES DEL SCALER:")
                for i, feature in enumerate(scaler.feature_names_in_):
                    print(f"  {i+1}. {feature}")
        except:
            print("❌ No se pudo obtener información de features")

if __name__ == "__main__":
    ver_features_modelo()