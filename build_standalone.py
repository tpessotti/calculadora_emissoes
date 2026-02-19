"""
Script para gerar versão standalone HTML com Stlite
Cria um arquivo HTML único que roda completamente no navegador
"""

import os
import json
from pathlib import Path

# Diretórios
SRC_DIR = Path("src")
DATA_DIR = Path("data")
OUTPUT_FILE = Path("calculadora_emissoes_standalone.html")

# Template HTML base
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calculadora de Emissões CMP - Standalone</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@0.89.1/build/stlite.css"/>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        #root {{
            width: 100vw;
            height: 100vh;
        }}
        .loading {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            flex-direction: column;
            background: #EDF0E7;
        }}
        .loading h1 {{
            color: #4c8061;
            font-size: 2rem;
            margin-bottom: 1rem;
        }}
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4c8061;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div id="root">
        <div class="loading">
            <h1>Calculadora de Emissões CMP</h1>
            <div class="spinner"></div>
            <p>Carregando aplicação... (pode levar alguns segundos)</p>
        </div>
    </div>
    
    <script type="module">
        import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@0.89.1/build/stlite.js";
        
        mount({{
            requirements: {requirements},
            entrypoint: "app.py",
            files: {files},
            streamlitConfig: {{
                "theme.base": "light",
                "theme.primaryColor": "#4c8061",
                "theme.backgroundColor": "#EDF0E7",
                "theme.secondaryBackgroundColor": "#f4f4f4",
                "theme.textColor": "#262730",
                "client.toolbarMode": "viewer",
                "client.showErrorDetails": true,
                "runner.magicEnabled": false
            }}
        }}, document.getElementById("root"));
    </script>
</body>
</html>
"""

def read_file_safe(filepath):
    """Lê arquivo e retorna conteúdo ou comentário de erro"""
    try:
        # Tenta ler como texto utf-8
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Escapar backticks para não quebrar template strings
        content = content.replace('`', '\\`')
        content = content.replace('${', '\\${')
        return content
    except UnicodeDecodeError:
        print(f"Aviso: Arquivo binário ou encoding inválido ignorado: {filepath}")
        return None
    except Exception as e:
        print(f"Erro ao ler {filepath}: {e}")
        return None

def get_files_content():
    files = {}
    
    # 1. Processar arquivos de src/ (mapeados para a raiz)
    if SRC_DIR.exists():
        for path in SRC_DIR.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                # Caminho relativo dentro de src/
                rel_path = path.relative_to(SRC_DIR)
                # Converte para string com forward slashes
                str_path = str(rel_path).replace("\\", "/")
                
                content = read_file_safe(path)
                if content is not None:
                    files[str_path] = content
                    print(f"Adicionado: {str_path}")

    # 2. Processar arquivos de data/ (mapeados para data/)
    if DATA_DIR.exists():
        for path in DATA_DIR.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                # Caminho relativo a partir da raiz do projeto, mantendo 'data/'
                rel_path = path  # path já é data/...
                str_path = str(rel_path).replace("\\", "/")
                
                content = read_file_safe(path)
                if content is not None:
                    files[str_path] = content
                    print(f"Adicionado: {str_path}")
    
    # Criar user_sessions.json vazio se não existir
    if "data/user_sessions.json" not in files:
        files["data/user_sessions.json"] = "{}"

    return files

def main():
    print("Iniciando build standalone...")
    
    # Lista de dependências
    requirements = [
        "streamlit",
        "pandas",
        "numpy",
        "plotly",
        "networkx",
        "openpyxl",
        "requests"
    ]
    
    # Coletar arquivos
    files = get_files_content()
    
    # Gerar HTML
    html_content = HTML_TEMPLATE.format(
        requirements=json.dumps(requirements),
        files=json.dumps(files)
    )
    
    # Salvar arquivo
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nSucesso! Arquivo gerado em: {OUTPUT_FILE.absolute()}")
    print(f"Total de arquivos empacotados: {len(files)}")

if __name__ == "__main__":
    main()
