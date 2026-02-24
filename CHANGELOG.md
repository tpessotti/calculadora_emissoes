# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Alterado
- **Standalone build (`build_standalone.py`) revisado para mudanças recentes**
  - Empacota também `core/` (AppContext, períodos, IO e validações), além de `src/` e `data/`
  - Inclui `assets/` no bundle HTML quando presente
  - Filtra melhor arquivos não suportados (`__pycache__`, `.pyc`, `.pyo`)
  - Garante defaults de runtime para evitar falhas em ambiente limpo:
    - `data/user_sessions.json`
    - `data/json_db/database.json` (com `anos_disponiveis`)
    - `data/fatores_emissao.json`

### Documentação
- `README.md` atualizado com detalhes do novo algoritmo de build standalone e artefatos mínimos gerados automaticamente.

## [0.3.0-beta] - 2025-01

### Adicionado
- **🏗️ Camada `core/` — nova arquitetura modular**
  - `core/context.py` — AppContext com ano ativo, paths centralizados e invalidação de cache
  - `core/io/json_io.py` — Loader/exporter JSON com `st.cache_data`, load/save de database e fatores
  - `core/io/excel_io.py` — Geração de template Excel com 5 abas (README, Unidades, Conexões, Tecnologias, Fatores), migração Excel → JSON DB
  - `core/validation/schema.py` — Schema v1.0.0, validação de entidades, integridade referencial, relatórios de erros/avisos
  - `core/calc/cache.py` — Memoização de cálculos com hash MD5 para evitar recálculos
  
- **📅 Sistema Multi-Ano**
  - Seletor de ano global na sidebar (selectbox)
  - Descoberta automática de anos a partir do JSON DB e session_state
  - Invalidação de caches ao trocar de ano
  - Status bar com ano ativo e estado da base
  
- **💾 JSON DB — Persistência estruturada**
  - Arquivo master `data/json_db/database.json` com schema versionado
  - Exportação automática do session_state para JSON DB ao salvar sessão
  - Funções de filtragem por ano (`filtrar_unidades_por_ano`)
  
- **📥 Template de Importação Excel**
  - Botão de download na sidebar com template gerado dinamicamente
  - Template inclui fatores de emissão pré-preenchidos do sistema
  - Validação de dados com Data Validation (escopo, booleanos)
  - Abas com formatação visual (cabeçalhos, linhas de dica, cores)
  
- **🧪 Testes unitários**
  - `tests/test_calculations.py` com 12+ testes
  - Testes golden-result para propagação de pegada em cadeia linear
  - Testes de validação de schema e integridade referencial
  - Testes de geração de template Excel
  - Testes de JSON I/O (load/save/round-trip)

- **📄 Documentação**
  - `docs/JSON_SCHEMA.md` — Documentação completa do schema JSON DB

### Alterado
- **app.py** — Usa `load_fatores_emissao()` com cache em vez de leitura direta; integra contexto de ano e template download
- **database.py** — Removidas importações circulares (`from database import ...`); imports de `EmissionCalculator` movidos para dentro dos métodos
- **FatoresEmissao.py** — Usa `AppContext` para caminhos e `save_fatores_emissao()` centralizado
- **Home.py** — Salva sessão também no JSON DB; refresh de anos disponíveis ao restaurar sessão
- **Unidades.py**, **Reports.py** — Importam `AppContext` para acesso ao contexto de ano
- **version.py** — Atualizado para v0.3.0-beta

### Corrigido
- Importação circular em `database.py` (linha ~130) que importava de si mesmo

---

## [0.2.0-beta] - 2025-11-11

### Adicionado
- **🎨 Landing Page CMP Profissional**
  - Design com identidade visual CMP (#4c8061, #EDF0E7, #f4b266)
  - Modal de login integrado
  - Carrossel de features (6 cards informativos)
  - Header oculto na landing, visível após login
  
- **💾 Sistema de Persistência Automática**
  - Auto-save de sessões em `user_sessions.json`
  - Auto-restore silencioso ao fazer login
  - Botão "Salvar Sessão" na sidebar
  - Armazenamento de API key do chatbot
  
- **📊 Interface de Gerenciamento Consolidada**
  - Página "Unidades & Fluxos" reorganizada em 2 tabs
  - Tab "Unidades Produtivas" com criação/edição inline
  - Tab "Gerenciar Fluxos" para criar/excluir arcos
  - Botão "Criar Nova Unidade" com formulário inline
  - Edição de unidades inline (sem tab separada)
  - Criação de fluxos com massa automática da origem
  - Exclusão de fluxos com interface simplificada

- **🗂️ Reorganização do Projeto**
  - Estrutura de pastas profissional (`src/`, `data/`, `docs/`)
  - Código-fonte movido para `src/`
  - Dados movidos para `data/`
  - `.gitignore` completo
  - Script `run.py` para facilitar execução

- **🌐 Versão Standalone HTML com Stlite**
  - Aplicativo roda completamente no navegador (sem servidor)
  - Script `build_standalone.py` para gerar HTML único
  - Deploy fácil em GitHub Pages, Netlify, etc.
  - Funciona offline após primeiro carregamento
  - Documentação completa em `docs/STLITE_DEPLOYMENT.md`

### Modificado
- **🏠 Página Inicial Pós-Login**
  - Layout harmonioso com cards de boas-vindas
  - Modais para exportação/importação de sessões
  - Estatísticas de sessão em tempo real
  - Links úteis movidos para o footer
  - Informações de versão no rodapé

- **🎯 Navegação Simplificada**
  - Reduzido de 8 para 7 páginas principais
  - "Tabela de Unidades" integrada em "Unidades & Fluxos"
  - Sidebar visível apenas após login
  - Controle de acesso aprimorado

- **📦 Dependências Otimizadas**
  - Limpeza de requirements.txt (110 → 11 bibliotecas)
  - Remoção de dependências não utilizadas
  - Redução de 90% no tamanho das dependências

### Corrigido
- Bug de modais abrindo automaticamente ao carregar página
- Conflito de keys de elementos duplicados
- Caminhos de arquivos JSON após reorganização
- Imports após mudança de estrutura de pastas

### Técnico
- Paths relativos atualizados para nova estrutura
- Sistema de imports com `sys.path`
- Separação clara entre código, dados e documentação
- Melhor organização para versionamento Git

## [0.1.0-beta] - 2025-11-10

### Adicionado
- Sistema de login simples para identificação de usuários
- Recursos administrativos específicos para usuário "admin"
- Exportação de sessões de trabalho completas em JSON
- Importação de sessões anteriores
- Cálculo de emissões segregado por escopos (1, 2, 3)
- Modelagem de cadeias produtivas com unidades e fluxos
- Diagramas de Sankey multi-dimensionais com 7+ dimensões de análise
- Simulação de tecnologias alternativas
- Importação de fluxos via Excel (exclusivo para admin)
- Visualização de grafos de rede interativos
- Gestão de fatores de emissão personalizável
- Tabelas interativas com exportação de dados
- Limpeza automática de sessão ao fazer logout
- Versionamento da aplicação
- README completo com documentação acadêmica
- **🤖 Assistente de IA com OpenRouter API**
  - Chat inteligente sobre processos industriais
  - Contexto automático do projeto atual
  - Suporte a 4 modelos de IA gratuitos
  - Sugestões personalizadas de melhorias
  - Histórico de conversas
  - Configuração de API key via interface

### Características
- Interface web responsiva com Streamlit
- Análise de sensibilidade de emissões
- Filtros dinâmicos por múltiplas dimensões
- Visualização com cores personalizadas por tipo
- Cálculos baseados em metodologia GHG Protocol
- Baixo nível de entrada técnica
- Democratização de acesso a análise de emissões

### Técnico
- Python 3.9+
- Streamlit 1.50.0
- Plotly para visualizações
- Pandas para manipulação de dados
- NetworkX para análise de grafos

## [Roadmap]

### Planejado para v0.3.0
- Integração com bases de dados públicas de fatores de emissão
- Validação aprimorada de dados de entrada
- Melhorias de performance para grandes cadeias
- Testes automatizados

### Planejado para v0.4.0
- Análise de incertezas
- Propagação de erros
- Intervalos de confiança

### Planejado para v0.5.0
- Cálculo de custos de carbono
- Diferentes cenários de precificação
- Análise de ROI de investimentos em tecnologias limpas

---

[0.2.0-beta]: https://github.com/tpessotti/calculadora_emissoes/releases/tag/v0.2.0-beta
[0.1.0-beta]: https://github.com/tpessotti/calculadora_emissoes/releases/tag/v0.1.0-beta
