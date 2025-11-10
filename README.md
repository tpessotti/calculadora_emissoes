# Calculadora de Emissões de Carbono - CMP

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-0.1.0--beta-orange.svg?style=for-the-badge)](https://github.com/tpessotti/calculadora_emissoes)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

## 🌐 Acesso Rápido

**🚀 [Acesse o aplicativo online](https://cmp-tool.streamlit.app/)** - Sem necessidade de instalação!

O aplicativo está disponível gratuitamente no Streamlit Cloud e pode ser acessado diretamente pelo navegador.

> ⚠️ **Versão Beta (v0.1.0-beta)**: Este aplicativo está em desenvolvimento ativo. Algumas funcionalidades podem estar em fase de testes e melhorias contínuas são realizadas regularmente. Feedback e sugestões são muito bem-vindos!

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

### 6. **Gestão de Sessões e Usuários**
- Sistema de login simples para identificação de usuários
- Exportação de sessões de trabalho completas
- Importação de projetos anteriores
- Recursos administrativos para gestão de dados

## 🚀 Instalação e Configuração

### Pré-requisitos

- Python 3.13 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

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

Execute o aplicativo com Streamlit:
```bash
streamlit run app.py
```

O aplicativo estará disponível em `http://localhost:8501`

## 📖 Guia de Uso

### 1. Login
- Acesse a aplicação e identifique-se com um nome de usuário
- Use `admin` para acessar recursos administrativos

### 2. Configuração Inicial
- **Fatores de Emissão**: Importe ou configure fatores de emissão na aba correspondente
- **Unidades**: Crie unidades produtivas definindo insumos, produtos e consumos
- **Fluxos**: Conecte unidades para estabelecer a cadeia produtiva

### 3. Análise de Emissões
- **Tabela**: Visualize métricas calculadas para todas as unidades
- **Sankey**: Explore fluxos de emissões com diferentes perspectivas
- **Tecnologias**: Simule cenários alternativos de tecnologia

### 4. Exportação de Dados
- Exporte sua sessão de trabalho para continuar posteriormente
- Gere relatórios e dados para análise externa

## 🏗️ Arquitetura do Sistema

### Estrutura de Diretórios

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
│   └── Sankey.py               # Diagramas de Sankey
│
├── requirements.txt            # Dependências do projeto
└── README.md                   # Este arquivo
```

### Principais Dependências

- **Streamlit**: Framework de interface web
- **Pandas**: Manipulação e análise de dados
- **Plotly**: Visualizações interativas (Sankey)
- **NetworkX**: Análise de grafos
- **streamlit-agraph**: Visualização de redes
- **openpyxl**: Importação de dados Excel

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

#### v0.1.0-beta (Novembro 2025)
- ✅ Sistema de login e gestão de sessões
- ✅ Cálculo de emissões por escopo (1, 2, 3)
- ✅ Modelagem de cadeias produtivas
- ✅ Diagramas de Sankey multi-dimensionais
- ✅ Simulação de tecnologias alternativas
- ✅ Importação de fluxos via Excel (admin)
- ✅ Exportação/importação de sessões

### Próximas Versões

- [ ] **v0.2.0**: Exportação de relatórios em PDF
- [ ] **v0.3.0**: Análise de incertezas e propagação de erros
- [ ] **v0.4.0**: Cálculo de custos de carbono (carbon pricing)
- [ ] **v0.5.0**: Integração com bases de dados públicas de fatores de emissão
- [ ] **v0.6.0**: API para integração com outros sistemas
- [ ] **v0.7.0**: Análise de conformidade com CBAM (Carbon Border Adjustment Mechanism)
- [ ] **v0.8.0**: Suporte multilíngue
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

**Feedback sobre a versão Beta**: Como estamos em desenvolvimento ativo, seu feedback é extremamente valioso! Por favor, reporte bugs, sugira melhorias ou compartilhe sua experiência através das [GitHub Issues](https://github.com/tpessotti/calculadora_emissoes/issues).

## 🙏 Agradecimentos

Este projeto foi desenvolvido com o objetivo de democratizar o acesso a ferramentas de análise de emissões de carbono, contribuindo para a transição energética e a sustentabilidade industrial.

---

**Nota**: Esta ferramenta destina-se a análises preliminares e suporte à decisão. Para inventários oficiais e relatórios regulatórios, recomenda-se validação por especialistas e uso de metodologias certificadas.
