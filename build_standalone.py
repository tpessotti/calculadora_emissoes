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
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Escapar backticks para não quebrar template strings
        content = content.replace('`', '\\`')
        content = content.replace('${', '\\${')
        return content
    except Exception as e:
        return f"# Erro ao carregar arquivo: {e}"

def generate_standalone_html():
    """Gera arquivo HTML standalone"""
    
    print("🚀 Gerando versão standalone HTML com Stlite...")
    
    # Requirements simplificados (apenas compatíveis com Pyodide)
    requirements = [
        "pandas",
        "numpy", 
        "plotly",
        "networkx",
        "streamlit-agraph",
        "requests"
        # Removidos: openai-whisper, pydub (incompatíveis)
    ]
    
    # Arquivos Python a incluir
    files = {}
    
    # Arquivos principais
    main_files = [
        "app.py",
        "database.py",
        "calculations.py",
        "utils.py",
        "config.py",
        "version.py"
    ]
    
    print("\n📄 Processando arquivos principais...")
    for filename in main_files:
        filepath = SRC_DIR / filename
        if filepath.exists():
            files[filename] = read_file_safe(filepath)
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} (não encontrado)")
    
    # Arquivos de tabs
    tabs_files = [
        "Home.py",
        "Unidades.py",
        "Fluxo.py",
        "FatoresEmissao.py",
        "Tecnologias.py",
        "Sankey.py",
        "Chatbot.py" #(usa OpenRouter API, pode não funcionar bem)
    ]
    
    print("\n📑 Processando tabs...")
    for filename in tabs_files:
        filepath = SRC_DIR / "tabs" / filename
        if filepath.exists():
            files[f"tabs/{filename}"] = read_file_safe(filepath)
            print(f"  ✓ tabs/{filename}")
    
    # Arquivos de dados JSON
    data_files = [
        "fatores_emissao.json",
        "config_fatores.json"
    ]
    
    print("\n📊 Processando dados...")
    for filename in data_files:
        filepath = DATA_DIR / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                files[f"data/{filename}"] = json.dumps(data, ensure_ascii=False)
                print(f"  ✓ data/{filename}")
            except Exception as e:
                print(f"  ✗ data/{filename} (erro: {e})")
    
    # Criar user_sessions.json vazio
    files["data/user_sessions.json"] = "{}"
    
    # Converter files dict para formato JSON
    files_json = json.dumps(files, ensure_ascii=False, indent=2)
    requirements_json = json.dumps(requirements)
    
    # Gerar HTML final
    html_content = HTML_TEMPLATE.format(
        requirements=requirements_json,
        files=files_json
    )
    
    # Salvar arquivo
    print(f"\n💾 Salvando em {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)  # MB
    print(f"✅ Arquivo gerado com sucesso!")
    print(f"📏 Tamanho: {file_size:.2f} MB")
    print(f"📍 Local: {OUTPUT_FILE.absolute()}")
    
    print("\n" + "="*60)
    print("🎉 STANDALONE HTML GERADO!")
    print("="*60)
    print("\n📖 Como usar:")
    print("  1. Abra o arquivo HTML em um navegador moderno")
    print("  2. Aguarde o carregamento (pode levar 10-30 segundos)")
    print("  3. O app rodará completamente offline!")
    print("\n🌐 Para hospedar:")
    print("  • GitHub Pages: git push para branch gh-pages")
    print("  • Netlify: arraste e solte o arquivo")
    print("  • Qualquer servidor estático")
    print("\n⚠️  Notas:")
    print("  • Primeira carga baixa ~50-100MB (Pyodide)")
    print("  • Chatbot removido (incompatível com Stlite)")
    print("="*60)

if __name__ == "__main__":
    generate_standalone_html()
