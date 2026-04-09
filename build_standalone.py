"""
Script para gerar versão standalone HTML com Stlite
Cria um arquivo HTML único que roda completamente no navegador

Estrutura empacotada:
  app.py              ← entrypoint (mapeado de src/app.py)
  multipage_utils.py  ← utilitários compartilhados
  tabs/*.py           ← todas as páginas (via st.navigation)
  core/**             ← lógica de negócio
  data/**             ← dados e base de emissões
  assets/**           ← imagens e recursos estáticos
"""

import os
import json
import argparse
import re
from pathlib import Path

# Diretórios
SRC_DIR = Path("src")
CORE_DIR = Path("core")
DATA_DIR = Path("data")
ASSETS_DIR = Path("assets")
OUTPUT_FILE = Path("calculadora_emissoes_standalone.html")

# Dependências padrão (compatíveis com ambiente browser/Pyodide)
DEFAULT_REQUIREMENTS = [
    "numpy",
    "pandas",
    "plotly",
    "networkx",
    "openpyxl",
    "python-calamine",
]

# Pacotes que NÃO funcionam (ou são pesados demais) no Pyodide/WASM.
# São removidos automaticamente da lista de dependências ao gerar o standalone.
#
#   reportlab — usa extensões C não portadas para Pyodide; causa ImportError
#               + ocupa ~30 MB na heap WASM desnecessariamente.
#   requests  — sem socket real no browser; Pyodide usa pyodide.http / fetch.
#               Manter causaria falhas silenciosas em qualquer chamada HTTP.
STANDALONE_EXCLUDE: set[str] = {
    "reportlab",
    "requests",
}

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

        // Em file:/// (origin null), alguns navegadores bloqueiam pushState/replaceState.
        // Isso evita erro recorrente de "Bad message format" no standalone.
        if (window.location.protocol === "file:" && window.history) {{
            const _pushState = window.history.pushState.bind(window.history);
            const _replaceState = window.history.replaceState.bind(window.history);

            // Sempre salva o path no hash — lido pelo Python via js.window.location.hash
            // para restaurar a página ativa após qualquer st.rerun() em file://.
            function _saveNavHash(url) {{
                if (!url) return;
                try {{
                    var path = String(url).replace(/^\/+/, '');
                    window.location.hash = path;
                }} catch (_) {{}}
            }}

            window.history.pushState = function(state, title, url) {{
                _saveNavHash(url);
                try {{ return _pushState(state, title, url); }} catch (_) {{}}
            }};

            window.history.replaceState = function(state, title, url) {{
                _saveNavHash(url);
                try {{ return _replaceState(state, title, url); }} catch (_) {{}}
            }};
        }}
        
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
        # Evita fechamento prematuro da tag <script> no HTML gerado.
        content = re.sub(r"</script", r"<\\/script", content, flags=re.IGNORECASE)
        return content
    except UnicodeDecodeError:
        print(f"Aviso: Arquivo binário ou encoding inválido ignorado: {filepath}")
        return None
    except Exception as e:
        print(f"Erro ao ler {filepath}: {e}")
        return None


def load_requirements(requirements_file: Path):
    """Lê requirements.txt com fallback de encoding e retorna lista limpa."""
    if not requirements_file.exists():
        print(f"Aviso: arquivo de requirements não encontrado: {requirements_file}")
        return DEFAULT_REQUIREMENTS

    encodings = ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]
    text = None
    for enc in encodings:
        try:
            text = requirements_file.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Aviso: falha ao ler {requirements_file} com encoding {enc}: {e}")

    if text is None:
        print("Aviso: não foi possível interpretar requirements, usando padrão")
        return DEFAULT_REQUIREMENTS

    parsed = []

    def _extract_pkg_name(spec: str):
        """Extrai o nome base de um requirement (PEP 508 simplificado)."""
        # Remove environment marker, ex.: pkg>=1.0; python_version>="3.11"
        spec = spec.split(";", 1)[0].strip()
        if not spec:
            return None

        # Ignora referências diretas por URL/path
        if "@" in spec and ("://" in spec or spec.startswith((".", "/"))):
            return None

        # Remove extras: pacote[extra] -> pacote
        spec = spec.split("[", 1)[0].strip()

        # Isola nome antes de operadores de versão/comparação
        name = re.split(r"\s*(?:==|!=|~=|>=|<=|>|<)\s*", spec, maxsplit=1)[0].strip()
        if not name:
            return None
        return name

    # Pacotes resolvidos pelo runtime do stlite (não instalar via micropip)
    runtime_managed = {"streamlit"}

    # Pacotes conhecidos do ecossistema Pyodide: manter sem pin de versão
    pyodide_managed = {"numpy", "pandas"}

    seen = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Remove comentário inline e marcadores/flags básicos
        line = line.split(" #", 1)[0].strip()
        if line.startswith(("-r", "--")):
            continue

        pkg_name = _extract_pkg_name(line)
        if not pkg_name:
            continue

        normalized = pkg_name.lower()
        if normalized in runtime_managed:
            continue

        # Evita pinos para pacotes nativos do Pyodide (ex.: numpy==2.x)
        if normalized in pyodide_managed:
            line = normalized
        else:
            # Usa apenas o nome base para evitar resolução de wheel não compatível
            line = normalized

        if line not in seen:
            seen.add(line)
            parsed.append(line)

    if not parsed:
        print("Aviso: requirements vazio, usando padrão")
        return DEFAULT_REQUIREMENTS

    # Mantém apenas dependências realmente usadas no standalone
    safe_requirements = {
        "numpy",
        "pandas",
        "plotly",
        "networkx",
        "openpyxl",
        "requests",
    }
    filtered = [r for r in parsed if r in safe_requirements]
    return filtered or DEFAULT_REQUIREMENTS

def get_files_content():
    files = {}

    def _deve_incluir(path: Path) -> bool:
        if not path.is_file():
            return False
        if "__pycache__" in path.parts:
            return False
        if path.suffix in {".pyc", ".pyo"}:
            return False
        if path.name.startswith(".") and path.suffix in {".swp", ".tmp"}:
            return False
        if ".bak." in path.name or path.name.endswith(".bak"):
            return False
        # pasta pages/ foi removida — ignorar caso ainda exista no disco
        if "pages" in path.parts and path.parent.name == "pages":
            return False
        return True
    
    # 1. Processar arquivos de src/ (mapeados para a raiz)
    if SRC_DIR.exists():
        for path in SRC_DIR.rglob("*"):
            if _deve_incluir(path):
                # Caminho relativo dentro de src/
                rel_path = path.relative_to(SRC_DIR)
                # Converte para string com forward slashes
                str_path = str(rel_path).replace("\\", "/")
                
                content = read_file_safe(path)
                if content is not None:
                    files[str_path] = content
                    print(f"Adicionado: {str_path}")

    # Ordem estável para facilitar comparação entre builds
    files = dict(sorted(files.items(), key=lambda item: item[0]))

    # 1.1 Processar arquivos de core/ (mapeados para core/)
    if CORE_DIR.exists():
        for path in CORE_DIR.rglob("*"):
            if _deve_incluir(path):
                str_path = str(path).replace("\\", "/")

                content = read_file_safe(path)
                if content is not None:
                    files[str_path] = content
                    print(f"Adicionado: {str_path}")

    # 2. Processar arquivos de data/ (mapeados para data/)
    if DATA_DIR.exists():
        for path in DATA_DIR.rglob("*"):
            if _deve_incluir(path):
                # Caminho relativo a partir da raiz do projeto, mantendo 'data/'
                rel_path = path  # path já é data/...
                str_path = str(rel_path).replace("\\", "/")
                
                content = read_file_safe(path)
                if content is not None:
                    files[str_path] = content
                    print(f"Adicionado: {str_path}")

    # 3. Processar assets/ (mapeados para assets/)
    if ASSETS_DIR.exists():
        for path in ASSETS_DIR.rglob("*"):
            if _deve_incluir(path):
                str_path = str(path).replace("\\", "/")

                content = read_file_safe(path)
                if content is not None:
                    files[str_path] = content
                    print(f"Adicionado: {str_path}")

    # 4. Incluir .streamlit/config.toml para preservar tema e configurações
    _config_toml = Path(".streamlit") / "config.toml"
    if _config_toml.exists():
        content = read_file_safe(_config_toml)
        if content is not None:
            files[".streamlit/config.toml"] = content
            print("Adicionado: .streamlit/config.toml")
    
    # Criar user_sessions.json vazio se não existir
    if "data/user_sessions.json" not in files:
        files["data/user_sessions.json"] = "{}"

    # Garantir database master para descoberta de anos no AppContext
    if "data/json_db/database.json" not in files:
        files["data/json_db/database.json"] = json.dumps(
            {
                "schema_version": "1.2.0",
                "source": "standalone_default",
                "anos_disponiveis": [2025],
                "fatores_emissao": [],
                "unidades": [],
                "conexoes": [],
                "tecnologias": [],
            },
            ensure_ascii=False,
            indent=2,
        )

    # Garantir base de fatores
    if "data/fatores_emissao.json" not in files:
        files["data/fatores_emissao.json"] = "[]"

    return files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gera a versão standalone HTML da Calculadora de Emissões"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(OUTPUT_FILE),
        help="Arquivo HTML de saída",
    )
    parser.add_argument(
        "-r",
        "--requirements-file",
        default="requirements.txt",
        help="Arquivo requirements a ser utilizado",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    output_file = Path(args.output)
    requirements_file = Path(args.requirements_file)

    print("Iniciando build standalone...")

    # Lista de dependências — filtra pacotes incompatíveis com Pyodide
    requirements = load_requirements(requirements_file)
    excluded = [r for r in requirements if r.lower() in STANDALONE_EXCLUDE]
    requirements = [r for r in requirements if r.lower() not in STANDALONE_EXCLUDE]
    if excluded:
        print(f"Pacotes excluídos (incompatíveis com Pyodide): {', '.join(excluded)}")
    print(f"Dependências incluídas: {len(requirements)}")
    
    # Coletar arquivos
    files = get_files_content()
    
    # Gerar HTML
    html_content = HTML_TEMPLATE.format(
        requirements=json.dumps(requirements),
        files=json.dumps(files)
    )
    
    # Salvar arquivo
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nSucesso! Arquivo gerado em: {output_file.absolute()}")
    print(f"Total de arquivos empacotados: {len(files)}")

if __name__ == "__main__":
    main()
