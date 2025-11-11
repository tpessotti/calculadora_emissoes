"""
Script de execução da Calculadora de Emissões CMP
Facilita a inicialização do aplicativo Streamlit
"""
import sys
import os

# Adicionar diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    # Importar e executar o app
    os.system("streamlit run src/app.py")
