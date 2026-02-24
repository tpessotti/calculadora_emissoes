# Calculadora de Emissões de Carbono — CMP
## Documentação Completa de Funcionalidades

**Aplicativo:** Carbon Metrics Project (CMP)  
**Versão:** 0.4.0-beta  
**Status:** Beta  
**Tecnologia:** Python · Streamlit  
**Autor:** Tiago Pessotti  
**Data de referência:** Fevereiro 2026  

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura e Estrutura do Projeto](#2-arquitetura-e-estrutura-do-projeto)
3. [Autenticação e Gestão de Sessão](#3-autenticação-e-gestão-de-sessão)
4. [Navegação e Interface Principal](#4-navegação-e-interface-principal)
5. [Módulo: Unidades & Fluxos](#5-módulo-unidades--fluxos)
6. [Módulo: Diagrama de Fluxo](#6-módulo-diagrama-de-fluxo)
7. [Módulo: Fatores de Emissão](#7-módulo-fatores-de-emissão)
8. [Módulo: Tecnologias Alternativas](#8-módulo-tecnologias-alternativas)
9. [Módulo: Análise de Emissões e Reportes](#9-módulo-análise-de-emissões-e-reportes)
10. [Módulo: Assistente de IA (Chatbot)](#10-módulo-assistente-de-ia-chatbot)
11. [Motor de Cálculo de Emissões](#11-motor-de-cálculo-de-emissões)
12. [Gestão de Contexto e Período de Análise](#12-gestão-de-contexto-e-período-de-análise)
13. [Importação e Exportação de Dados](#13-importação-e-exportação-de-dados)
14. [Validação de Dados](#14-validação-de-dados)
15. [Banco de Dados e Persistência](#15-banco-de-dados-e-persistência)
16. [Configurações Globais](#16-configurações-globais)

---

## 1. Visão Geral

O **Carbon Metrics Project (CMP)** é uma aplicação web desenvolvida em Python com Streamlit, voltada para a **quantificação, modelagem e análise de emissões de gases de efeito estufa (GEE)** em cadeias produtivas. A plataforma democratiza o acesso a ferramentas de inventário climático, permitindo que empresas de todos os portes modelem seus processos industriais, calculem emissões por escopo e gerem relatórios alinhados a padrões internacionais.

### Principais objetivos

- **Modelagem de processos:** representação de cadeias produtivas por meio de unidades produtivas interconectadas.
- **Cálculo automático de emissões:** intensidade de emissão por Escopo 1, 2 e 3, e propagação de pegada de carbono ao longo da cadeia.
- **Visualização interativa:** diagramas de fluxo, grafos de rede, diagramas de Sankey e gráficos analíticos.
- **Relatórios normativos:** inventário GEE conforme o GHG Protocol e relatórios alinhados a IFRS S1/S2.
- **Simulação de alternativas:** avaliação de impacto de tecnologias alternativas em emissões.
- **Assistente de IA:** suporte conversacional inteligente para análise do processo.

---

## 2. Arquitetura e Estrutura do Projeto

```
calculadora_emissoes/
├── src/                        # Código principal da aplicação
│   ├── app.py                  # Ponto de entrada — orquestrador principal
│   ├── calculations.py         # Motor de cálculo de emissões
│   ├── config.py               # Configurações de canvas, cores e layouts
│   ├── database.py             # Modelos de dados e DatabaseManager
│   ├── utils.py                # Componentes de UI reutilizáveis
│   ├── version.py              # Informações de versão
│   └── tabs/                   # Módulos de cada página/aba
│       ├── Home.py             # Landing page, login e dashboard do usuário
│       ├── Unidades.py         # Cadastro e edição de unidades produtivas
│       ├── FluxoPlotly.py      # Diagrama de fluxo interativo (Plotly + NetworkX)
│       ├── FatoresEmissao.py   # Gestão de fatores de emissão
│       ├── Tecnologias.py      # Cadastro de tecnologias alternativas
│       ├── Reports.py          # Análises, Sankey, Inventário GEE, IFRS S1/S2
│       └── Chatbot.py          # Assistente de IA (OpenRouter)
├── core/                       # Módulos reutilizáveis independentes de UI
│   ├── context.py              # Contexto global (ano ativo, caminhos, modo multi-ano)
│   ├── periodos.py             # Parser e normalização de períodos
│   ├── calc/
│   │   ├── comparativo.py      # Análise comparativa multi-ano
│   │   ├── fatores.py          # Lógica de fatores de emissão
│   │   └── cache.py            # Cache de cálculos
│   ├── io/
│   │   ├── excel_io.py         # Geração de template Excel e importação
│   │   └── json_io.py          # Persistência JSON (sessões, fatores, DB)
│   └── validation/
│       └── schema.py           # Schema e validação de dados
├── data/
│   ├── fatores_emissao.json    # Base de fatores de emissão
│   ├── user_sessions.json      # Sessões salvas de usuários
│   └── json_db/
│       └── database.json       # Banco de dados master (multi-ano)
└── tests/                      # Testes unitários
```

### Modelos de dados principais

| Classe | Descrição |
|--------|-----------|
| `UnidadeProdutiva` | Representa um elo da cadeia produtiva com consumíveis, massas de input/output, emissões calculadas por escopo e pegada acumulada. |
| `Conexao` | Ligação direcional entre duas unidades produtivas, com massa transferida e rótulo. |
| `Tecnologia` | Tecnologia alternativa com insumos, fatores de consumo e limites de aplicação por unidade. |
| `DatabaseManager` | Gerenciador de estado em `st.session_state`, responsável por CRUD de unidades e conexões, exportação/importação JSON e propagação de pegada. |

---

## 3. Autenticação e Gestão de Sessão

### 3.1 Sistema de Login

O aplicativo utiliza um sistema de autenticação baseado em nome de usuário (sem senha), com as seguintes características:

- **Landing page pública:** exibida sem necessidade de login, apresentando o produto, funcionalidades e links institucionais.
- **Botão "Entrar →":** aciona um modal de login construído com `@st.dialog`.
- **Identificação por nome:** o usuário informa seu nome; o registro alimenta `st.session_state.usuario_logado` e persiste durante toda a sessão.
- **Modo Admin:** o usuário com nome `admin` tem acesso a funcionalidades administrativas adicionais.
- **Data e hora de login** são registradas automaticamente.

### 3.2 Restauração Automática de Sessão

Ao fazer login, o sistema verifica automaticamente se existe uma sessão salva para o usuário e a restaura, carregando unidades produtivas, conexões, fatores de emissão e tecnologias armazenados.

### 3.3 Salvar Sessão

O botão **"Salvar Sessão"** na barra lateral exporta o estado atual para `data/user_sessions.json`. A sessão inclui:

- Unidades produtivas cadastradas (com todos os campos calculados)
- Conexões de fluxo
- Fatores de emissão
- Tecnologias alternativas
- Metadados: usuário, data/hora e versão da aplicação

### 3.4 Exportar e Importar Sessão

**Exportar:** modal que exibe estatísticas da sessão atual (total de unidades, conexões, tecnologias) e gera um arquivo `.json` com timestamp para download.

**Importar:** modal que aceita upload de um arquivo `.json` de sessão. Valida a estrutura, exibe prévia do conteúdo e, após confirmação do usuário, substitui todos os dados da sessão atual pelos importados, recalculando emissões e propagando pegadas.

---

## 4. Navegação e Interface Principal

### 4.1 Sidebar Contextual

Após o login, a barra lateral fornece:

- **Identificação do usuário** logado
- **Botão "Salvar Sessão"** com feedback via toast
- **Menu de navegação** por radio buttons com 7 destinos:
  1. Início
  2. Diagrama de Fluxo
  3. Unidades & Fluxos
  4. Fatores de Emissão
  5. Tecnologias
  6. Análise de Emissões
  7. Assistente IA
- **Seletor de período de análise** (ano único ou modo comparativo multi-ano)
- **Template de Importação** — botão para download do template Excel
- **Validação da Base** — executa validação de integridade e exibe relatório

### 4.2 Seletor de Período

Permite alternar entre dois modos:

| Modo | Descrição |
|------|-----------|
| **Ano único** | Selectbox com lista de anos disponíveis; ao trocar o ano, invalida caches e re-renderiza o grafo. |
| **Modo comparativo** | Multiselect de múltiplos anos + campo de expressão de período textual (ex: `2020-2025; 2030`). Permite análises comparativas entre anos no módulo de Reportes. |

A expressão de período suporta:
- Ano único: `2025`
- Intervalo: `2020-2025`
- Lista: `2020, 2022, 2024`
- Todos: `*`

---

## 5. Módulo: Unidades & Fluxos

### 5.1 Aba: Unidades Produtivas

#### Visualização em Tabela

Exibe todas as unidades cadastradas em uma tabela interativa com as colunas:

| Coluna | Descrição |
|--------|-----------|
| ID ELO | Identificador único da unidade |
| Nome | Nome descritivo |
| Localização | Região/localidade |
| Período | Ano(s) de referência |
| Input / Output | Insumo de entrada e produto de saída |
| Emissão (CO₂) | Emissão absoluta total (tCO₂e) |
| Intensidade (tCO₂/t) | Intensidade de emissão por tonelada de output |
| Int. Escopo 1/2/3 | Intensidade por escopo (tCO₂/t) |
| Pegada (CO₂/t produto) | Pegada acumulada de carbono |
| Pegada Escopo 1/2/3 | Pegada por escopo |
| Tax. Fronteira / Tax. Local | Flags de tributação |

**Métricas resumidas** no topo: total de unidades, total de conexões e emissão total.

#### Criar Nova Unidade

Formulário completo com os campos:

- **ID_ELO\*:** identificador único
- **Nome\*:** nome descritivo
- **Localização\*:** cidade, estado ou região
- **Período\*:** ano de referência (ou expressão de período)
- **Input:** nome do insumo de entrada
- **Massa Input\* (t):** quantidade de insumo de entrada em toneladas
- **Output:** nome do produto de saída
- **Massa Output\* (t):** quantidade de produto de saída em toneladas
- **Consumíveis:** lista de consumíveis (selecionados a partir dos fatores de emissão cadastrados)
- **Consumo Específico:** fator de consumo por consumível (tCO₂/t produto)
- **Taxação de Fronteira:** flag para indicar tributação de carbono na fronteira (CBAM)
- **Taxação Local:** flag para indicar tributação de carbono local
- **Tecnologia:** tecnologia alternativa associada (opcional)
- **Configuração Operacional:** configuração de operação padrão

Ao salvar, as emissões são calculadas automaticamente.

#### Editar Unidade

Ao clicar em editar na tabela, o formulário acima é preenchido com os valores existentes. Ao salvar, recalcula emissões, propaga pegadas em toda a cadeia e atualiza a visualização.

#### Remover Unidade

Remove a unidade e todas as conexões associadas a ela, com confirmação por toast.

### 5.2 Aba: Fluxos

#### Criar Novo Fluxo (Arco)

- Seleciona unidade de origem e destino via selectbox
- A massa do fluxo é automaticamente preenchida com `MassaOutput` da unidade de origem
- Permite definir um rótulo textual
- Valida duplicidade (conexão já existente entre o mesmo par origem→destino)

#### Excluir Fluxo Existente

- Exibe lista de fluxos no formato `Origem → Destino (X ton)`
- Seleciona por índice e remove com atualização automática

---

## 6. Módulo: Diagrama de Fluxo

Implementado em `FluxoPlotly.py` usando **Plotly** e **NetworkX**.

### 6.1 Layout do Diagrama

O diagrama ocupa a parte principal da tela, com um painel lateral colapsável à direita.

**Algoritmos de layout disponíveis:**

| Algoritmo | Descrição |
|-----------|-----------|
| **Hierárquico (Sugiyama)** | Ordenação topológica com minimização de cruzamentos de arestas pelo método barycenter (4 passadas forward+backward). Centraliza nós pais sobre os filhos. |
| **Árvore simples** | Posicionamento em camadas por grau de entrada, sem otimização de cruzamentos. |
| **Forças (Spring)** | Layout baseado em forças usando `nx.spring_layout` do NetworkX; adequado para grafos não-hierárquicos. |

**Controles de espaçamento:**
- Slider para espaçamento horizontal (150–800 px)
- Slider para espaçamento vertical (100–500 px)

### 6.2 Nós (Unidades Produtivas)

Cada unidade é representada como um nó no grafo com:

**Modos de rótulo:**
| Modo | Conteúdo exibido |
|------|-----------------|
| **Compacto** | Apenas ID |
| **Médio** (padrão) | Nome + Pegada de carbono |
| **Detalhado** | Nome + Input/Output + Escopos de emissão |

**Tooltip (hover):** sempre exibe todas as informações disponíveis da unidade.

**Cores dos nós:**
- Azul: nó padrão
- Verde: nó selecionado
- Vermelho: nó com taxação (fronteira ou local)

### 6.3 Arestas (Conexões)

Representadas como setas direcionadas com:
- Cor cinza (padrão) ou âmbar (selecionada)
- Rótulo com a massa transferida (t)
- Seta na ponta indicando direção do fluxo

### 6.4 Interações com o Grafo

- **Seleção de nós:** clique simples para selecionar/deselecionar
- **Seleção de arestas:** clique na aresta para selecioná-la
- **Limpar seleção:** botão na sidebar
- **Criação de conexão:** selecionar dois nós e usar o painel de ações ("Conectar selecionados")
- **Exclusão com confirmação:** diálogo de confirmação antes de excluir nós ou arestas selecionados

### 6.5 Painel Lateral (Busca e Preview)

- Dropdown de busca de unidades no formato `ID – Nome`
- Ao selecionar, o nó correspondente é destacado no grafo
- Abre automaticamente o painel de edição da unidade selecionada

### 6.6 Painel de Ações (Abaixo do Grafo)

Quando há seleção ativa, exibe ações contextualmente:

- **Nó(s) selecionado(s):** editar unidade, excluir unidade, conectar dois nós selecionados
- **Aresta selecionada:** editar massa da conexão, excluir conexão

### 6.7 Exportação do Diagrama

Disponível na seção "Exportar" da sidebar:
- **JSON completo** — exporta todo o estado da aplicação (unidades, conexões, tecnologias) como arquivo `.json` para download

---

## 7. Módulo: Fatores de Emissão

### 7.1 Importação via Planilha Excel

Aceita upload de arquivo `.xlsx` com as colunas:
- `grupo_consumivel`, `consumivel`, `escopo`, `fator_emissao`, `kgCO2e_unid`

**Política de duplicados:** o usuário escolhe entre "Substituir" (atualiza o fator existente) ou "Descartar" (ignora o registro já existente).

Salva automaticamente no arquivo `data/fatores_emissao.json`.

### 7.2 Tabela com Filtros

Exibe todos os fatores cadastrados em um `st.data_editor` editável, com filtros na sidebar:

- **Grupo do Consumível** (selectbox)
- **Escopo** (selectbox: 1, 2 ou 3)
- **Busca por nome** do consumível (texto livre, case-insensitive)

Ao editar diretamente na tabela e clicar em "Salvar Alterações", persiste as mudanças no JSON.

### 7.3 Adição Manual

Formulário com:
- **Grupo do Consumível\*:** categoria (ex: Combustíveis, Eletricidade)
- **Nome do Consumível\*:** nome exato (ex: Diesel S10, Eletricidade)
- **Escopo\*:** 1, 2 ou 3
- **Fator de Emissão (kgCO₂e)\*:** valor numérico positivo
- **Unidade de consumo\*:** unidade do fator (ex: litro, kWh, kg)

Valida duplicidade por combinação (grupo + consumível + escopo) antes de salvar.

---

## 8. Módulo: Tecnologias Alternativas

### 8.1 Lista de Tecnologias Registradas

Exibe cada tecnologia cadastrada em um expander com:
- ID e nome da tecnologia
- Lista de insumos com fatores de consumo (tCO₂e/t consumível)
- Unidades associadas e limites de aplicação (% inferior e superior)
- Botão de remoção (🗑️) ao lado de cada tecnologia
- Formulário de edição integrado ao expander (modo edit inline)

### 8.2 Criar Nova Tecnologia

Formulário com dois painéis:

**Painel esquerdo — Insumos:**
- ID da Tecnologia\*
- Multiselect de insumos (populado pelos fatores de emissão cadastrados)
- Input de fator de consumo para cada insumo selecionado

**Painel direito — Unidades e Limites:**
- Nome da Tecnologia\*
- Multiselect de unidades produtivas (associação opcional)
- Para cada unidade: limite inferior (%) e limite superior (%) de aplicação

**Validações:**
- ID único (não permite duplicatas)
- ID e nome obrigatórios
- Pelo menos um insumo selecionado

### 8.3 Editar e Substituir

Modo inline dentro do expander, com botão "Substituir Tecnologia" que localiza a tecnologia pelo ID e a substitui completamente no estado da sessão.

---

## 9. Módulo: Análise de Emissões e Reportes

Este é o módulo mais rico do sistema, organizado em 7 sub-abas:

### 9.1 Painel Geral

Dashboard com KPIs e visualizações de alto nível. Exibe:
- Emissão total, intensidade média, total de unidades
- Gráficos de barras e séries temporais das emissões
- Tabela resumo com todos os dados calculados

### 9.2 Diagrama Sankey

Diagrama de fluxo de Sankey interativo (Plotly) que representa:
- **Fluxo de massa** entre as unidades produtivas
- **Fluxo de emissões** propagadas ao longo da cadeia
- Espessura dos links proporcional à quantidade de CO₂e ou de massa
- Cores por escopo (vermelho=1, amarelo=2, azul=3)

### 9.3 Inventário GEE (GHG Protocol)

Inventário corporativo completo seguindo o **GHG Protocol Corporate Accounting and Reporting Standard**:

**Estrutura do inventário:**
- Cabeçalho com entidade, período, abordagem de consolidação e setor
- KPIs: Escopo 1, Escopo 2, Escopo 3, Total GEE, Intensidade (tCO₂e/t)
- Tabela-resumo GHG Protocol com percentuais por escopo e número de fontes

**Detalhamento por escopo** em expansores separados:
- Tabela de fontes de emissão com: unidade, fonte, gás, fator, consumo específico, massa, emissão
- Gráfico de barras horizontais com top 5 fontes por escopo
- Notas metodológicas (GHG Protocol, ISO 14064-1:2018)

**Resumo por unidade produtiva**: tabela ordenada por emissão total com todos os escopos.

**Exportações disponíveis:**
| Formato | Conteúdo |
|---------|----------|
| **Excel (XLSX)** | Aba Resumo + abas Escopo 1, 2 e 3 com formatação profissional (cores por escopo, bordas, auto-width) |
| **PDF** | Relatório formatado (via ReportLab) |
| **JSON** | Dados brutos do inventário |

### 9.4 Questionário IFRS S1/S2

Questionário estruturado de 8 seções, alinhado aos padrões de divulgação climática **IFRS S1** e **IFRS S2**:

| Seção | Conteúdo |
|-------|----------|
| **1. Identificação da Entidade** | Nome, CNPJ, setor (NACE/CNAE), país, responsável, cargo, e-mail, moeda, período, abordagem de consolidação |
| **2. Governança Climática (§5–12)** | Órgão responsável, frequência de supervisão, comitê de sustentabilidade, competências, integração estratégica, remuneração vinculada |
| **3. Estratégia Climática (§13–22)** | Riscos físicos, riscos de transição, horizontes temporais (curto/médio/longo prazo), análise de cenários, impacto financeiro estimado, oportunidades |
| **4. Gestão de Riscos (§23–24)** | Processo de identificação, frequência de avaliação, integração com ERM, ações de mitigação |
| **5. Metas Climáticas (§33–36)** | Tipo de meta (absoluta/intensidade), ano-base, ano-alvo, percentual de redução, validação SBTi, net zero, marcos intermediários |
| **6. Plano de Transição (§14)** | Ações previstas, investimento, tecnologias planejadas, dependências |
| **7. Verificação e Asseguração** | Asseguração por terceiros, tipo (limitada/razoável), organismo verificador, norma utilizada |
| **8. Informações Adicionais** | Compensações de carbono (offsets), preço interno de carbono, notas adicionais |

**Barra de progresso:** indica o percentual de campos preenchidos com feedback contextual.

### 9.5 Reporte IFRS S1/S2

Gera um relatório narrativo completo, combinando os dados do questionário com os resultados quantitativos do inventário GEE, estruturado conforme as exigências de divulgação dos padrões IFRS S1 (riscos e oportunidades relacionados à sustentabilidade) e IFRS S2 (riscos e oportunidades relacionados ao clima).

**Exportações do relatório:**
- **PDF** (via ReportLab) com capa, seções narrativas e tabelas de dados
- **Excel (XLSX)** com múltiplas abas estruturadas

### 9.6 Análise por Unidade

Análise detalhada de cada unidade individualmente:
- Seletor de unidade
- Detalhamento dos consumíveis e emissões por fonte
- Pegada acumulada por escopo
- Comparação com a cadeia completa (participação percentual)
- Gráficos de composição das emissões

### 9.7 Comparativo Multi-Ano

Análise temporal cruzando múltiplos anos de dados (requer modo comparativo ativado na sidebar):

**Métricas geradas:**
- Pivot table de emissões por unidade × ano
- Deltas absolutos entre anos consecutivos (Δ ano1→ano2)
- Variações percentuais entre anos consecutivos (% ano1→ano2)
- Resumo comparativo geral (totais, médias, pegada, massa por ano)

**Algoritmos do módulo `core/calc/comparativo.py`:**
- `pivot_emissoes_por_ano()` — cria DataFrame pivotado por unidade e ano
- `pivot_intensidade()` — pivot por métrica selecionada
- `calcular_deltas()` — variações absolutas entre períodos
- `calcular_variacao_pct()` — variações percentuais entre períodos
- `resumo_comparativo()` — sumariza totais e tendências

---

## 10. Módulo: Assistente de IA (Chatbot)

### 10.1 Configuração

Utiliza a API **OpenRouter** para acessar modelos de linguagem. O usuário informa sua **API Key** e seleciona o modelo desejado:

| Modelo | Descrição |
|--------|-----------|
| `meta-llama/llama-3.3-8b-instruct:free` | Llama 3.3 8B Instruct (gratuito) |
| `meta-llama/llama-4-scout:free` | Llama 4 Scout (gratuito) |
| `qwen/qwen3-4b:free` | Qwen3 4B (gratuito) |
| `deepseek/deepseek-r1-0528-qwen3-8b:free` | DeepSeek R1 Qwen3 8B (gratuito) |

### 10.2 Interface de Chat

- Histórico de mensagens em formato chat interativo (`st.chat_message`)
- Input de texto flutuante para envio de perguntas
- Spinner de "Pensando..." durante geração da resposta
- Persistência do histórico durante a sessão
- Limitação a **últimas 10 mensagens** no contexto enviado à API (controle de tokens)

### 10.3 Contexto do Processo (Sidebar)

Exibe métricas resumidas do processo atual:
- Total de unidades produtivas
- Emissão total (tCO₂e)
- Intensidade média (tCO₂e/t)
- Total de fatores de emissão cadastrados

**Opção de contexto detalhado:** quando ativada, inclui no prompt do sistema os dados das primeiras 5 unidades (nome, localização, massa, intensidade, consumíveis), enriquecendo as respostas do modelo.

### 10.4 Sistema de Prompt

O assistente recebe um **system prompt** especializado que o identifica como:
> *"Assistente especializado em análise de emissões de carbono e processos industriais."*

Com capacidades declaradas de:
- Analisar dados de emissões por escopo (1, 2, 3)
- Sugerir melhorias e tecnologias alternativas
- Explicar cálculos de intensidade de emissão e pegada de carbono
- Interpretar fluxos de massa e energia
- Recomendar boas práticas de redução de emissões

### 10.5 Gerenciamento da Sessão de Chat

- **Limpar Conversa:** reinicia o histórico mantendo a configuração
- **Remover API Key:** desconecta e retorna à tela de configuração
- **Trocar Modelo:** selectbox para alternar entre modelos disponíveis

---

## 11. Motor de Cálculo de Emissões

### 11.1 `EmissionCalculator.calcular_emissoes()`

Calcula a intensidade de emissão de uma unidade produtiva isolada:

```
Para cada consumível i:
    emissao_i = fator_emissao[i] × ConsumoEspecifico[i]
    
    Se escopo contém "1" → IntensidadeEmissaoEscopo1 += emissao_i
    Se escopo contém "2" → IntensidadeEmissaoEscopo2 += emissao_i
    Se escopo contém "3" → IntensidadeEmissaoEscopo3 += emissao_i

IntensidadeEmissao = E1 + E2 + E3  [tCO₂e / t_output]
Pegada = IntensidadeEmissao × MassaOutput  [tCO₂e]
```

### 11.2 `EmissionCalculator.propagar_pegada()`

Propaga a pegada de carbono acumulada ao longo da cadeia usando **ordenação topológica (algoritmo de Kahn)**:

```
1. Construir grafo dirigido das conexões
2. Ordenação topológica (Kahn's BFS)
3. Para cada unidade na ordem topológica:
   - Se não tem predecessores: Pegada própria = Intensidade própria
   - Se tem predecessores:
       Para cada conexão pai → unidade:
           proporção = massa_conexão / MassaInput_unidade
       
       pegada_herdada_escopo_N += Pegada_pai_N × proporção
       PegadaEscopo_N = pegada_herdada_N + IntensidadeEscopo_N
       
4. Pegada = PegadaEscopo1 + PegadaEscopo2 + PegadaEscopo3  [tCO₂e/t produto]
```

### 11.3 Outros métodos

| Método | Retorno |
|--------|---------|
| `calcular_pegada_total(unidades)` | Soma de `Pegada` de todas as unidades |
| `calcular_emissoes_por_localizacao(unidades)` | Dict `{localizacao: emissao_total}` |
| `determinar_ordem_fluxo(unidades, conexoes)` | Lista de IDs em ordem topológica |
| `gerar_dados_grafico(unidades)` | Dict com labels e emissões para gráficos |

---

## 12. Gestão de Contexto e Período de Análise

### 12.1 `AppContext` (Singleton)

O contexto da aplicação é armazenado em `st.session_state["app_context"]` e gerencia:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `ano_ativo` | `int` | Ano atualmente selecionado (padrão: 2025) |
| `anos_disponiveis` | `List[int]` | Anos descobertos no banco de dados |
| `anos_selecionados` | `List[int]` | Anos selecionados para análise comparativa |
| `modo_comparacao` | `bool` | Indica se múltiplos anos estão selecionados |
| `base_carregada` | `bool` | Indica se os dados foram carregados da base |
| `data_dir` | `str` | Caminho para o diretório de dados |

**Descoberta automática de anos:** ao inicializar, o contexto varre:
1. `data/json_db/database.json` — campo `anos_disponiveis`
2. Subpastas com nome de 4 dígitos em `json_db/`
3. Campo `Periodo` das unidades em `st.session_state`

**Invalidação de cache ao trocar de ano:**
- `refresh_canvas = True` (força redesenho do diagrama)
- Limpa `_pegada_propagada` e `_calc_cache_key`

### 12.2 Parser de Períodos (`core/periodos.py`)

Normaliza expressões de período para listas de anos inteiros:
- `"2025"` → `[2025]`
- `"2020-2025"` → `[2020, 2021, 2022, 2023, 2024, 2025]`
- `"2020, 2022, 2024"` → `[2020, 2022, 2024]`
- `"*"` → todos os anos disponíveis

---

## 13. Importação e Exportação de Dados

### 13.1 Template Excel (`core/io/excel_io.py`)

Gera um arquivo `.xlsx` estruturado com 5 abas:

| Aba | Cor | Conteúdo |
|-----|-----|----------|
| **README** | Verde | Instruções de preenchimento, regras e legenda |
| **Unidades** | Azul | Campos de unidades produtivas com exemplos |
| **Conexoes** | Laranja | Origem, destino, massa e rótulo |
| **Tecnologias** | Roxo | ID, nome, insumos e fatores de consumo |
| **Fatores_Emissao** | Verde escuro | Referência dos fatores disponíveis |

**Campos obrigatórios** destacados com fundo laranja claro; opcionais com fundo verde claro. Validação de drop-down para campos `TRUE/FALSE`.

### 13.2 Exportação JSON

O `DatabaseManager.export_to_json()` serializa o estado completo:
```json
{
  "unidades": [...],
  "conexoes": [...],
  "tecnologias_alternativas": [...]
}
```

### 13.3 Importação JSON

O `DatabaseManager.import_from_json()`:
1. Processa tecnologias (mapeia IDs para objetos)
2. Alerta sobre insumos sem fator de emissão cadastrado (usa 0.0 como fallback)
3. Reconstrói objetos `UnidadeProdutiva` e `Conexao`
4. Recalcula emissões de cada unidade
5. Restaura valores calculados previamente salvos
6. Propaga pegada em toda a cadeia

### 13.4 Persistência JSON (`core/io/json_io.py`)

Funções de leitura/escrita:
- `load_fatores_emissao(path)` — carrega fatores de emissão
- `save_fatores_emissao(path, fatores)` — persiste fatores de emissão
- `export_session_to_database(session, path)` — exporta sessão para banco
- `save_database(data, path)` — salva banco de dados master

---

## 14. Validação de Dados

### 14.1 Engine de Validação (`core/validation/schema.py`)

#### Schema (versão 1.1.0)

Define campos obrigatórios e tipos esperados para cada entidade:

| Entidade | Campos obrigatórios |
|----------|---------------------|
| **unidade** | ID_ELO, Nome, Localizacao, Periodo, Input, MassaInput, Output, MassaOutput, Consumiveis, ConsumoEspecifico |
| **conexao** | origem, destino |
| **tecnologia** | id, nome, insumos |
| **fator_emissao** | grupo_consumivel, consumivel, escopo, fator_emissao, kgCO2e_unid |

#### Validações específicas por entidade

**Unidade produtiva:**
- Massas não podem ser negativas
- `len(Consumiveis)` deve ser igual a `len(ConsumoEspecifico)`
- Campo `Periodo` deve ser parseável pelo módulo de períodos

**Fator de emissão:**
- Valor do fator não pode ser negativo

#### `ValidationReport`

Objeto de resultado com:
- `erros`: lista de `ValidationError` (impeditivos)
- `avisos`: lista de `ValidationError` (não-impeditivos)
- `total_registros` e `registros_validos`
- Propriedade `is_valid` (True se sem erros)
- Método `summary()` com texto formatado

### 14.2 Integração na Interface

Botão **"Validar Base"** na sidebar executa validação em tempo real e exibe:
- ✅ Base válida com contagem de registros
- ⚠️ Avisos expansíveis com localização do campo problemático
- ❌ Erros expansíveis com entidade, índice e mensagem detalhada

---

## 15. Banco de Dados e Persistência

### 15.1 Armazenamento em `st.session_state`

A aplicação utiliza o `session_state` do Streamlit como camada de estado em memória durante a sessão ativa:

| Chave | Tipo | Conteúdo |
|-------|------|----------|
| `unidades` | `List[UnidadeProdutiva]` | Unidades produtivas cadastradas |
| `conexoes` | `List[Conexao]` | Conexões entre unidades |
| `tecnologias_alternativas` | `List[Tecnologia]` | Tecnologias alternativas |
| `fatores_emissao` | `List[Dict]` | Fatores de emissão carregados |
| `edges` | `List[Dict]` | Arcos no formato `{source, target, massa}` para o grafo |
| `usuario_logado` | `str` | Nome do usuário autenticado |
| `app_context` | `AppContext` | Contexto global (ano, modo, etc.) |
| `ifrs_questionario` | `Dict` | Dados do questionário IFRS S1/S2 |
| `chat_history` | `List[Dict]` | Histórico do chatbot |

### 15.2 Persistência em Arquivo

| Arquivo | Conteúdo |
|---------|----------|
| `data/fatores_emissao.json` | Base de fatores de emissão (editável pela UI) |
| `data/user_sessions.json` | Sessões salvas automaticamente por usuário |
| `data/json_db/database.json` | Banco de dados master multi-ano |

---

## 16. Configurações Globais

### 16.1 Canvas (`src/config.py`)

```python
CANVAS_CONFIG = {
    "width": 1920, "height": 1080,
    "directed": True,
    "node": {
        "shape": "box", "font": {"size": 12},
        "margin": 10, "borderWidth": 2, "color": "#e6f3ff"
    },
    "physics": {"enabled": True},
    "backgroundColor": "#ffffff",
}
```

### 16.2 Paleta de Cores

| Identificador | Cor | Uso |
|---------------|-----|-----|
| `primary` | `#0066cc` | Ações primárias |
| `scope1` | `#EF4444` | Emissões Escopo 1 (vermelho) |
| `scope2` | `#F59E0B` | Emissões Escopo 2 (amarelo) |
| `scope3` | `#3B82F6` | Emissões Escopo 3 (azul) |
| `success` | `#059669` | Confirmações e acertos |
| `warning` | `#D97706` | Alertas |
| `danger` | `#DC2626` | Erros e exclusões |

### 16.3 Layouts do Diagrama

| Layout | Algoritmo |
|--------|-----------|
| **Hierárquico** | Sugiyama (LR, sortMethod=directed, nodeSpacing=300) |
| **Ordenado por Fluxo** | Hierárquico por hubsize |
| **Circular** | Layout aleatório melhorado |

---

## Referências Normativas

O CMP aplica ou referencia os seguintes padrões:

| Padrão | Aplicação |
|--------|-----------|
| **GHG Protocol Corporate Standard** (WRI/WBCSD) | Inventário GEE, definição de escopos 1/2/3, categorias de fontes |
| **GHG Protocol Scope 3 Standard** | Emissões indiretas na cadeia de valor |
| **ISO 14064-1:2018** | Quantificação e reporte de GEE em organizações |
| **IFRS S1** | Divulgação de riscos e oportunidades de sustentabilidade |
| **IFRS S2** | Divulgação de riscos e oportunidades relacionados ao clima |
| **ISO 14064-3 / ISAE 3410 / AA1000AS** | Asseguração de inventários GEE |
| **SBTi (Science Based Targets initiative)** | Validação de metas climáticas |

---

*Documento gerado com base no código-fonte da versão 0.4.0-beta (Fevereiro 2026).*
