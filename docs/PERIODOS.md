# PERIODOS.md — Parser e Normalização de Períodos

> Módulo: `core/periodos.py` · v1.1.0

## Visão Geral

O parser de períodos converte expressões textuais em listas de anos,
suportando intervalos, listas, e wildcards.

## Sintaxe Suportada

| Expressão | Resultado | Descrição |
|-----------|-----------|-----------|
| `"2025"` | `[2025]` | Ano único |
| `"2020-2025"` | `[2020, 2021, 2022, 2023, 2024, 2025]` | Intervalo inclusivo |
| `"2020-2022; 2025"` | `[2020, 2021, 2022, 2025]` | Intervalo + ano isolado |
| `"2020, 2022, 2025"` | `[2020, 2022, 2025]` | Lista separada por vírgulas |
| `"2020-2022; 2025, 2030"` | `[2020, 2021, 2022, 2025, 2030]` | Misto |
| `"*"` ou `"todos"` | todos os anos disponíveis | Wildcard (requer contexto) |

## Regras

1. **Intervalo válido**: 1900–2100
2. **Intervalos invertidos são rejeitados**: `"2025-2020"` → `PeriodoError`
3. **Separadores**: `;` e `,` são equivalentes
4. **Deduplicação automática**: `"2020-2022; 2021-2023"` → `[2020, 2021, 2022, 2023]`
5. **Resultado sempre ordenado**
6. **Wildcard requer `anos_disponiveis`**: sem contexto → `PeriodoError`

## Funções Disponíveis

### `parse_periodo(expr, anos_disponiveis=None) → List[int]`

Parser principal. Converte expressão textual em lista de anos.

```python
from core.periodos import parse_periodo

parse_periodo("2020-2023; 2025")
# [2020, 2021, 2022, 2023, 2025]

parse_periodo("*", anos_disponiveis=[2020, 2025])
# [2020, 2025]
```

### `normalizar_periodo_unidade(periodo_str) → List[int]`

Normaliza o campo `Periodo` de uma `UnidadeProdutiva`. Nunca lança exceção —
retorna `[]` em caso de falha.

```python
from core.periodos import normalizar_periodo_unidade

normalizar_periodo_unidade("2020-2022")  # [2020, 2021, 2022]
normalizar_periodo_unidade("abc")         # []
normalizar_periodo_unidade(2025)          # [2025]
```

### `expandir_registros_por_ano(registros, campo_periodo="Periodo") → List[dict]`

Expande registros que cobrem múltiplos anos em 1 registro por ano.

```python
from core.periodos import expandir_registros_por_ano

registros = [{"Periodo": "2020-2022", "Nome": "Fábrica A", "valor": 100}]
expandir_registros_por_ano(registros)
# [
#   {"Periodo": "2020", "Nome": "Fábrica A", "valor": 100},
#   {"Periodo": "2021", "Nome": "Fábrica A", "valor": 100},
#   {"Periodo": "2022", "Nome": "Fábrica A", "valor": 100},
# ]
```

### `format_periodo(anos) → str`

Formata lista de anos de volta para notação compacta.

```python
from core.periodos import format_periodo

format_periodo([2020, 2021, 2022, 2025, 2030])
# "2020-2022; 2025; 2030"
```

### `periodo_contem_ano(periodo_str, ano) → bool`

Verifica se uma expressão de período contém um determinado ano.

```python
from core.periodos import periodo_contem_ano

periodo_contem_ano("2020-2025", 2022)  # True
periodo_contem_ano("2020-2025", 2030)  # False
```

## Integração com o Contexto

O `AppContext` (em `core/context.py`) utiliza o parser para:

1. **Descoberta de anos**: `_discover_anos()` usa `normalizar_periodo_unidade()` no campo `Periodo`
2. **Seletor multi-ano**: O modo comparativo aceita expressões via `parse_periodo()`
3. **Filtro por ano**: `filtrar_unidades_por_ano()` em `core/io/json_io.py` usa o parser

## Resolução de Fatores por Ano

O módulo `core/calc/fatores.py` implementa resolução de fatores de emissão
com suporte a ano:

1. Busca exata: `(consumivel, escopo, ano)`
2. Fallback: fator global (sem campo `ano`)
3. Se nenhum: retorna 0.0

```python
from core.calc.fatores import FatorIndex

idx = FatorIndex(fatores_emissao)
fator = idx.get_fator("DIESEL", "SCOPE 1", ano=2025)  # busca por ano
fator = idx.get_fator("DIESEL", "SCOPE 1")             # busca global
```

## Testes

```bash
python -m pytest tests/test_periodos.py -v   # 45 testes
python -m pytest tests/test_fatores.py -v    # 20 testes
```
