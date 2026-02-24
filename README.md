# Calculadora de Emissões de Carbono - CMP

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-0.2.0--beta-orange.svg?style=for-the-badge)](https://github.com/tpessotti/calculadora_emissoes)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

## 🌐 Acesso Rápido

**🚀 [Acesse o aplicativo online](https://cmp-tool.streamlit.app/)** - Versão com servidor Streamlit

**🌐 Versão Standalone (Sem Servidor)** - Roda completamente no navegador!
- Gere seu próprio arquivo HTML com: `python build_standalone.py`
- Hospede em GitHub Pages, Netlify ou qualquer CDN
- Funciona offline após primeiro carregamento

O aplicativo está disponível gratuitamente no Streamlit Cloud e pode ser acessado diretamente pelo navegador.

> ⚠️ **Versão Beta (v0.3.0-beta)**: Este aplicativo está em desenvolvimento ativo. Algumas funcionalidades podem estar em fase de testes e melhorias contínuas são realizadas regularmente. Feedback e sugestões são muito bem-vindos!

## 📋 Sobre o Projeto

A **Calculadora de Emissões de Carbono - CMP** é uma ferramenta de análise e simulação desenvolvida para auxiliar indústrias, especialmente de pequeno e médio porte, na quantificação e gestão de emissões de gases de efeito estufa (GEE) ao longo de cadeias produtivas. 

Este aplicativo representa uma abordagem democratizante ao tema de contabilidade de carbono, oferecendo uma interface intuitiva e de baixo nível de entrada técnica, permitindo que organizações com recursos limitados possam realizar análises complexas de emissões e avaliar estratégias de mitigação através da simulação de troca de tecnologias.

### Contexto Acadêmico

O sistema implementa metodologias de Avaliação de Ciclo de Vida (ACV) simplificadas e princípios de contabilidade de carbono baseados em escopos (Escopo 1, 2 e 3), alinhados com protocolos internacionais como o GHG Protocol. A ferramenta foi desenvolvida com foco em:

- **Acessibilidade**: Interface web responsiva sem necessidade de instalações complexas
- **Democratização**: Redução de barreiras técnicas e financeiras para análise de emissões
- **Flexibilidade**: Modelagem de cadeias produtivas com diferentes níveis de complexidade
- **Transparência**: Cálculos baseados em fatores de emissão configuráveis e auditáveis
- **Tomada de Decisão**: Simulação de cenários alternativos para avaliação de investimentos em tecnologias limpas

## 🎯 Funcionalidades Principais

### 1. **Modelagem de Cadeias Produtivas**
- Criação de unidades produtivas com definição de insumos e produtos
- Conexão entre unidades para representar fluxos de massa e energia
- Suporte a múltiplos estágios de processamento
- Visualização interativa de fluxos através de grafos

### 2. **Cálculo de Emissões**
- Cálculo automático de intensidade de emissão (tCO2e/t produto)
- Segregação por escopos (1, 2 e 3)
- Pegada de carbono absoluta e específica
- Propagação de emissões através da cadeia produtiva

### 3. **Gestão de Fatores de Emissão**
- Biblioteca de fatores de emissão personalizável
- Importação/exportação de bases de dados em JSON
- Classificação por tipo de consumível e escopo
- Suporte a diferentes unidades de medida

### 4. **Simulação de Tecnologias Alternativas**
- Definição de tecnologias com diferentes perfis de consumo
- Comparação lado a lado de cenários
- Análise de sensibilidade e limites operacionais
- Avaliação de impacto de substituição tecnológica

### 5. **Visualização Avançada**
- **Diagramas de Sankey**: Visualização de fluxos de emissões com dimensões configuráveis
  - Análise por localização, tecnologia, escopo
  - Detalhamento por tipo de consumível
  - Filtros interativos e agregações dinâmicas
- **Tabelas Interativas**: Exportação de dados para análise externa
- **Grafos de Rede**: Representação visual da cadeia produtiva

### 6. **💾 Sistema de Persistência**
- Auto-save de sessões em arquivo JSON
- Auto-restore silencioso ao fazer login
- Botão "Salvar Sessão" na sidebar
- Armazenamento persistente de configurações do chatbot
- Base de dados de sessões por usuário

### 7. **🎨 Interface Profissional**
- Landing page com identidade visual CMP
- Modal de login integrado
- Cards informativos sobre funcionalidades
- Design responsivo e harmonioso
- Footer com links úteis e informações de versão

### 8. **🤖 Assistente de IA**
- Chatbot inteligente integrado com OpenRouter API
- Conversa sobre processos industriais e emissões
- Sugestões personalizadas de melhorias e otimizações
- Análise contextual baseada nos dados do projeto
- Suporte a múltiplos modelos de IA gratuitos:
  - Llama 3.3 8B Instruct
  - Llama 4 Scout
  - Qwen3 4B
  - DeepSeek R1 Qwen3 8B

## 🚀 Instalação e Configuração

### Pré-requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes Python)

### Opção 1: Instalação Local (Desenvolvimento)

Para executar o aplicativo localmente com todas as funcionalidades:

1. Clone o repositório:
```bash
git clone https://github.com/tpessotti/calculadora_emissoes.git
cd calculadora_emissoes
```

2. Crie um ambiente virtual (recomendado):
```bash
python -m venv venv
```

3. Ative o ambiente virtual:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Execução

**Método 1 - Script de execução (Recomendado):**
```bash
python run.py
```

**Método 2 - Streamlit direto:**
```bash
streamlit run src/app.py
```

**Método 3 - Versão Standalone (Sem Servidor):**
```bash
# Gerar arquivo HTML standalone
python build_standalone.py

# Depois abra calculadora_emissoes_standalone.html no navegador
# Ou hospede em qualquer servidor estático
```

O build standalone empacota automaticamente:
- `src/` (aplicação Streamlit)
- `core/` (contexto, parser de períodos, IO e validações)
- `data/` (bases JSON)
- `assets/` (arquivos de apoio)

Além disso, o script garante defaults mínimos quando ausentes:
- `data/user_sessions.json`
- `data/json_db/database.json` (com `anos_disponiveis` padrão)
- `data/fatores_emissao.json`

O aplicativo estará disponível em `http://localhost:8501` (métodos 1 e 2)

### Opção 2: Versão Standalone (Deploy sem Servidor)

Para criar uma versão que roda completamente no navegador:

1. Gere o arquivo HTML:
```bash
python build_standalone.py
```

2. O arquivo `calculadora_emissoes_standalone.html` será criado (~0.2 MB)

3. Deploy options:
   - **GitHub Pages**: Faça commit e push do arquivo HTML
   - **Netlify**: Arraste e solte o arquivo
   - **Vercel**: Deploy com um clique
   - **Qualquer servidor HTTP**: Sirva o arquivo HTML

4. Abra o arquivo no navegador ou acesse via URL hospedada

**Vantagens da versão standalone:**
- ✅ Sem necessidade de servidor Python
- ✅ Funciona offline após primeiro carregamento  
- ✅ Deploy gratuito e simples
- ✅ URL personalizada

**Limitações:**
- ⚠️ Primeira carga baixa ~50-100MB (Pyodide)
- ⚠️ Chatbot não disponível (incompatível com Stlite)
- ⚠️ Algumas bibliotecas podem ter comportamento diferente

Consulte `docs/STLITE_DEPLOYMENT.md` para mais detalhes.

## 📁 Estrutura do Projeto

```
calculadora_emissoes/
│
├── src/                        # Código-fonte principal
│   ├── app.py                  # Aplicação principal Streamlit
│   ├── database.py             # Gerenciamento de dados e modelos
│   ├── calculations.py         # Lógica de cálculo de emissões
│   ├── utils.py                # Utilitários e componentes UI
│   ├── config.py               # Configurações globais
│   ├── version.py              # Informações de versão
│   │
│   └── tabs/                   # Módulos de interface
│       ├── Home.py             # Landing page e dashboard
│       ├── Unidades.py         # Gestão de unidades e fluxos
│       ├── Fluxo.py            # Visualização de grafos
│       ├── FatoresEmissao.py   # Gestão de fatores de emissão
│       ├── Tecnologias.py      # Simulação de tecnologias
│       ├── Tabela.py           # Visualização tabular (deprecated)
│       ├── Sankey.py           # Diagramas de Sankey
│       └── Chatbot.py          # Assistente de IA
│
├── data/                       # Arquivos de dados
│   ├── fatores_emissao.json    # Base de fatores de emissão
│   ├── config_fatores.json     # Configurações de fatores
│   ├── user_sessions.json      # Sessões salvas dos usuários
│   └── *.xlsx                  # Planilhas de importação
│
├── docs/                       # Documentação
│   └── STLITE_DEPLOYMENT.md    # Guia de deployment standalone
│
├── .streamlit/                 # Configurações do Streamlit
├── requirements.txt            # Dependências do projeto
├── run.py                      # Script de execução
├── build_standalone.py         # Gera versão HTML standalone
├── README.md                   # Este arquivo
├── CHANGELOG.md                # Histórico de mudanças
└── .gitignore                  # Arquivos ignorados pelo Git
```

## 📖 Guia de Uso

### 1. Login e Configuração Inicial
- Acesse a landing page e clique em "Entrar"
- Identifique-se com um nome de usuário
- Use `admin` para acessar recursos administrativos extras
- Sua sessão será automaticamente restaurada nos próximos acessos

### 2. Configuração de Dados Base
- **Fatores de Emissão**: Configure ou importe fatores na aba correspondente
- **Unidades Produtivas**: Crie unidades definindo insumos, produtos e consumos
- **Fluxos**: Conecte unidades para estabelecer a cadeia produtiva

### 3. Gerenciamento de Unidades e Fluxos
- **Tab "Unidades Produtivas"**:
  - Clique em "➕ Criar Nova Unidade" para adicionar unidades
  - Use botões "Editar" ou "Remover" diretamente na tabela
  - Visualize métricas resumidas (total de unidades, conexões, emissões)
  
- **Tab "Gerenciar Fluxos"**:
  - Crie arcos entre unidades (massa automática da origem)
  - Exclua fluxos existentes
  - Importe/exporte dados em JSON

### 4. Análise e Visualização
- **Diagrama de Fluxo**: Visualize o grafo da cadeia produtiva
- **Análise de Emissões**: Explore diagramas de Sankey com diferentes dimensões
- **Tecnologias**: Simule cenários alternativos de tecnologia
- **🤖 Assistente IA**: Converse sobre seu processo e receba sugestões

### 5. Gestão de Sessões
- **Auto-save**: Suas alterações são salvas automaticamente
- **Botão "Salvar Sessão"**: Forçar salvamento manual (sidebar)
- **Exportar/Importar**: Use modais na página inicial para backup/restore
- **API Key do Chatbot**: Configurada uma vez, salva automaticamente

## 🏗️ Arquitetura do Sistema

### Tecnologias Utilizadas

- **Frontend**: Streamlit 1.50.0 (framework web responsivo)
- **Visualização**: Plotly (Sankey), NetworkX (grafos), streamlit-agraph
- **Processamento**: Pandas, NumPy
- **IA**: OpenRouter API (acesso a múltiplos modelos LLM)
- **Persistência**: JSON (arquivos locais)
- **Linguagem**: Python 3.9+

### Componentes Principais

1. **app.py**: Aplicação principal, roteamento e controle de acesso
2. **database.py**: Modelos de dados (UnidadeProdutiva, Conexao, Tecnologia)
3. **calculations.py**: Motor de cálculo de emissões
4. **utils.py**: Componentes de UI e utilitários
5. **tabs/**: Módulos de interface organizados por funcionalidade

### Fluxo de Dados

```
Usuário → Streamlit UI → DatabaseManager → Cálculos → Visualizações
                ↓
          Session State (temporário)
                ↓
          user_sessions.json (persistente)
```

## 📁 Estrutura do Projeto

```
calculadora_emissoes/
│
├── app.py                      # Aplicação principal Streamlit
├── database.py                 # Gerenciamento de dados e modelos
├── calculations.py             # Lógica de cálculo de emissões
├── utils.py                    # Utilitários e componentes UI
├── config.py                   # Configurações globais
│
├── tabs/                       # Módulos de interface
│   ├── Home.py                 # Página inicial e login
│   ├── Unidades.py             # Gestão de unidades produtivas
│   ├── Fluxo.py                # Visualização de grafos
│   ├── FatoresEmissao.py       # Gestão de fatores de emissão
│   ├── Tecnologias.py          # Simulação de tecnologias
│   ├── Tabela.py               # Visualização tabular
│   ├── Sankey.py               # Diagramas de Sankey
│   └── Chatbot.py              # Assistente de IA
│
├── requirements.txt            # Dependências do projeto
└── README.md                   # Este arquivo
```

### Principais Dependências (11 bibliotecas)

- **Streamlit** (1.50.0): Framework de interface web
- **Pandas**: Manipulação e análise de dados
- **NumPy**: Computação numérica
- **Plotly**: Visualizações interativas (Sankey)
- **NetworkX**: Análise de grafos
- **streamlit-agraph**: Visualização de redes
- **openpyxl**: Importação de dados Excel
- **requests**: Comunicação com APIs (OpenRouter)
- **openai-whisper**: Suporte a IA (futuro)
- **pydub**: Processamento de áudio (futuro)
- **tqdm**: Barras de progresso

> 📦 **Otimização v0.2.0**: Redução de 90% nas dependências (110 → 11 bibliotecas)

## 📊 Metodologia de Cálculo

### Intensidade de Emissão

A intensidade de emissão de uma unidade produtiva é calculada como:

```
IE = Σ(FC_i × FE_i × M_output) / M_output
```

Onde:
- `IE`: Intensidade de emissão (tCO2e/t produto)
- `FC_i`: Fator de consumo do insumo i (t/t produto)
- `FE_i`: Fator de emissão do insumo i (tCO2e/t insumo)
- `M_output`: Massa de produto (t)

### Escopos de Emissão

- **Escopo 1**: Emissões diretas de fontes controladas pela organização
- **Escopo 2**: Emissões indiretas de energia adquirida
- **Escopo 3**: Outras emissões indiretas da cadeia de valor

### Propagação de Emissões

As emissões são propagadas através da cadeia produtiva considerando:
- Fluxos de massa entre unidades
- Intensidade acumulada de emissões
- Conectividade da rede produtiva

## 🎓 Aplicações e Casos de Uso

### Indústrias de Pequeno e Médio Porte
- Diagnóstico inicial de emissões sem necessidade de consultoria especializada
- Priorização de investimentos em eficiência energética
- Preparação para futuras regulações de carbono

### Análise de Viabilidade de Projetos
- Avaliação de impacto de troca de combustíveis
- Análise de eletrificação de processos
- Comparação de rotas tecnológicas alternativas

### Educação e Capacitação
- Ferramenta didática para ensino de contabilidade de carbono
- Simulador para workshops e treinamentos
- Demonstração de conceitos de ACV simplificada

### Suporte à Tomada de Decisão
- Análise de sensibilidade de emissões a mudanças operacionais
- Identificação de pontos críticos (hotspots) na cadeia
- Quantificação de benefícios de medidas de mitigação

## 🔄 Roadmap e Desenvolvimentos Futuros

### Histórico de Versões

Para um histórico completo de mudanças, consulte o [CHANGELOG.md](CHANGELOG.md).

#### v0.2.0-beta (Novembro 2025)
- 🎨 Landing page profissional com identidade CMP
- 💾 Sistema de persistência automática de sessões
- 📊 Interface consolidada de gerenciamento (Unidades & Fluxos)
- ➕ Criação/exclusão de fluxos com interface simplificada
- 🗂️ Reorganização completa da estrutura do projeto
- 📦 Otimização de dependências (90% de redução)
- 🐛 Correções de bugs de UI e modais

#### v0.1.0-beta (Novembro 2025)
- ✅ Sistema de login e gestão de sessões
- ✅ Cálculo de emissões por escopo (1, 2, 3)
- ✅ Modelagem de cadeias produtivas
- ✅ Diagramas de Sankey multi-dimensionais
- ✅ Simulação de tecnologias alternativas
- ✅ 🤖 Assistente de IA com OpenRouter
- ✅ Importação de fluxos via Excel (admin)
- ✅ Exportação/importação de sessões

### Próximas Versões

- [ ] **v0.3.0**: Integração com bases públicas de fatores de emissão
- [ ] **v0.4.0**: Análise de incertezas e propagação de erros
- [ ] **v0.5.0**: Cálculo de custos de carbono (carbon pricing)
- [ ] **v0.6.0**: Exportação de relatórios em PDF
- [ ] **v0.7.0**: API para integração com outros sistemas
- [ ] **v0.8.0**: Análise de conformidade com CBAM
- [ ] **v0.9.0**: Suporte multilíngue
- [ ] **v1.0.0**: Sistema de autenticação avançado com banco de dados

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👥 Autores

- **Tiago Pessotti** - *Desenvolvimento e Conceituação* - [@tpessotti](https://github.com/tpessotti)
- **Marcos Coelho** - *Desenvolvimento e Conceituação* - [@Marcostcc](https://github.com/Marcostcc)
- **Henrique Maranhão** - *Conceituação e Testes*
- **Karine Bueno** - *Conceituação e Testes*

## 📧 Contato

Para questões, sugestões ou parcerias, entre em contato através das issues do GitHub.

**Feedback sobre a v0.2.0**: Reorganizamos completamente a estrutura do projeto para melhor manutenibilidade! Seu feedback é extremamente valioso. Por favor, reporte bugs, sugira melhorias ou compartilhe sua experiência através das [GitHub Issues](https://github.com/tpessotti/calculadora_emissoes/issues).

## 🙏 Agradecimentos

Este projeto foi desenvolvido com o objetivo de democratizar o acesso a ferramentas de análise de emissões de carbono, contribuindo para a transição energética e a sustentabilidade industrial.

---

**Nota**: Esta ferramenta destina-se a análises preliminares e suporte à decisão. Para inventários oficiais e relatórios regulatórios, recomenda-se validação por especialistas e uso de metodologias certificadas.
