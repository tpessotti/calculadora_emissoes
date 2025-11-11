# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

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

## [Unreleased]

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
