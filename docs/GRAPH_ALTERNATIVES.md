# Alternativas ao streamlit-agraph para Stlite

## Problema

O `streamlit-agraph` não é compatível com Stlite (Pyodide/WebAssembly) porque depende de bibliotecas JavaScript específicas que não funcionam bem no ambiente do navegador.

## Soluções Disponíveis

### 1. **Plotly Graph Objects (Recomendado) ✅**

**Vantagens:**
- ✅ 100% compatível com Stlite/Pyodide
- ✅ Já está nos requirements (usado para Sankey)
- ✅ Interativo e responsivo
- ✅ Exportação de imagens integrada
- ✅ Suporta hover, zoom, pan
- ✅ Customização completa de cores, tamanhos, formas

**Limitações:**
- ⚠️ Seleção de nós requer lógica customizada
- ⚠️ Não tem layout automático de grafos (precisa calcular posições)

**Implementação:**
Arquivo `FluxoPlotly.py` foi criado com implementação completa usando Plotly.

**Features implementadas:**
- Nós como markers quadrados com texto
- Setas direcionais entre nós
- Cores diferentes para nós selecionados e taxados
- Hover text com informações detalhadas
- Grid de fundo
- Exportação para PNG via botão

---

### 2. **Cytoscape.js via streamlit-cytoscapejs** 

**Vantagens:**
- Layout automático de grafos
- Muito interativo
- Bibliotecas JavaScript mature

**Limitações:**
- ❌ Não testado com Stlite
- ❌ Pode ter problemas de compatibilidade
- ❌ Requer componente customizado

---

### 3. **NetworkX + Matplotlib**

**Vantagens:**
- ✅ NetworkX é compatível com Pyodide
- ✅ Matplotlib também funciona
- ✅ Layout automático de grafos (spring, hierarchical, etc.)

**Limitações:**
- ❌ Não é interativo (imagem estática)
- ❌ Sem hover, sem zoom nativo
- ❌ Performance ruim para grafos grandes

**Exemplo de código:**
```python
import networkx as nx
import matplotlib.pyplot as plt

G = nx.DiGraph()
for edge in edges:
    G.add_edge(edge['source'], edge['target'])

pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color='lightblue', 
        node_size=1500, arrows=True)
st.pyplot(plt)
```

---

### 4. **Plotly Network Graph (Alternativa mais simples)**

Implementação mais básica usando apenas scatter plots:

```python
import plotly.graph_objects as go

# Edges
edge_traces = []
for edge in edges:
    x0, y0 = pos[edge['source']]
    x1, y1 = pos[edge['target']]
    
    edge_traces.append(go.Scatter(
        x=[x0, x1], y=[y0, y1],
        mode='lines',
        line=dict(width=2, color='gray'),
        hoverinfo='none'
    ))

# Nodes
node_trace = go.Scatter(
    x=[pos[node][0] for node in nodes],
    y=[pos[node][1] for node in nodes],
    mode='markers+text',
    text=nodes,
    marker=dict(size=20, color='lightblue'),
    textposition='top center'
)

fig = go.Figure(data=edge_traces + [node_trace])
st.plotly_chart(fig)
```

---

## Comparação de Features

| Feature | streamlit-agraph | Plotly | NetworkX+MPL | Cytoscape |
|---------|------------------|--------|--------------|-----------|
| Stlite Compatible | ❌ | ✅ | ✅ | ❓ |
| Interativo | ✅ | ✅ | ❌ | ✅ |
| Layout Auto | ✅ | ❌ | ✅ | ✅ |
| Hover Info | ✅ | ✅ | ❌ | ✅ |
| Click Selection | ✅ | Custom | ❌ | ✅ |
| Exportação PNG | ✅ | ✅ | ✅ | ✅ |
| Customização | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## Recomendação Final

### Para Versão Stlite: **Plotly** ✅

**Razões:**
1. Zero dependências extras (já temos Plotly)
2. 100% compatível com Pyodide
3. Muito customizável
4. Exportação integrada
5. Performance excelente

**Trade-offs:**
- Precisa calcular posições manualmente (já fazemos isso)
- Seleção de nós requer lógica custom (já implementado)

### Implementação

**Opção A: Manter ambas as versões**
```python
# src/tabs/Fluxo.py - versão com streamlit-agraph
# src/tabs/FluxoPlotly.py - versão com Plotly

# Em app.py, detectar ambiente:
try:
    from streamlit_agraph import agraph
    from tabs.Fluxo import FluxoTab
except ImportError:
    from tabs.FluxoPlotly import FluxoTab
```

**Opção B: Substituir completamente** (Recomendado)
```bash
# Substituir Fluxo.py pela versão Plotly
mv src/tabs/FluxoPlotly.py src/tabs/Fluxo.py

# Remover streamlit-agraph dos requirements
# Editar requirements.txt
```

---

## Próximos Passos

1. ✅ Implementação Plotly criada (`FluxoPlotly.py`)
2. ⬜ Testar em ambiente local
3. ⬜ Testar em versão Stlite
4. ⬜ Substituir ou manter dual-mode
5. ⬜ Atualizar documentação
6. ⬜ Rebuild standalone HTML

---

## Código para Integração

### Detecção automática de ambiente:

```python
# Em src/app.py ou utils.py

import sys

def is_stlite_environment():
    """Detecta se está rodando em Stlite/Pyodide"""
    return 'pyodide' in sys.modules or 'micropip' in sys.modules

def get_flow_tab():
    """Retorna FluxoTab apropriado para o ambiente"""
    if is_stlite_environment():
        from tabs.FluxoPlotly import FluxoTab
    else:
        try:
            from tabs.Fluxo import FluxoTab
        except ImportError:
            from tabs.FluxoPlotly import FluxoTab
    return FluxoTab
```

---

## Melhorias Futuras

1. **Layout automático com NetworkX**
   ```python
   import networkx as nx
   
   G = nx.DiGraph(edges)
   pos = nx.spring_layout(G)  # ou hierarchical_layout
   # Converter pos para Plotly
   ```

2. **Seleção de nós por click**
   - Usar `plotly_events` (se disponível no Stlite)
   - Ou usar `st.session_state` com botões

3. **Animações**
   - Transições suaves ao mover nós
   - Highlight animado ao selecionar

4. **3D Graph**
   - Plotly suporta grafos 3D
   - Útil para cadeias muito complexas
