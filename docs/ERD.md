# ERD — Diagrama de Relacionamento de Entidades

> Schema v1.2.0 · Calculadora de Emissões de Carbono

## Visão Geral

```
┌──────────────────┐       ┌──────────────────────────┐
│   Tecnologia     │       │   FatorEmissao           │
│──────────────────│       │──────────────────────────│
│ PK: id           │       │ PK: (consumivel, escopo, │
│    nome           │       │      ano)               │
│    insumos[]      │       │    grupo_consumivel      │
│    unidades[]     │       │    fator_emissao         │
└────────┬─────────┘       │    kgCO2e_unid           │
         │ 0..N            └────────────┬─────────────┘
         │                              │ 0..N
         │ FK: Tecnologia              │ Consumiveis[].nome
┌────────▼─────────────────┐            │
│   Unidade                │◄───────────┘
│──────────────────────────│
│ PK: (ID_ELO, Periodo)   │
│    Nome                  │
│    Localizacao           │
│    Input, MassaInput     │
│    Output, MassaOutput   │
│ FK: Tecnologia → Tec.id │
│    Consumiveis[]         │
│    ConsumoEspecifico[]   │
│    TaxacaoFronteira      │
│    TaxacaoLocal          │
│* IntensidadeEmissao      │
│* Pegada                  │
└──────┬──────┬────────────┘
       │      │
       │ 0..N │ 0..N
       │FK:origem FK:destino
┌──────▼──────▼────────────┐
│   Conexao                │
│──────────────────────────│
│ PK: (origem, destino,    │
│      periodo)            │
│ FK: origem  → Unidade.ID │
│ FK: destino → Unidade.ID │
│    massa                 │
│    label                 │
└──────────────────────────┘
```

_Campos marcados com `*` são calculados automaticamente._

## Entidades

### 1. `unidades` (UnidadeProdutiva)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `ID_ELO` | `str` | ✅ | Identificador único (PK) |
| `Nome` | `str` | ✅ | Nome descritivo |
| `Localizacao` | `str` | ✅ | Local geográfico |
| `Periodo` | `str` | ✅ | Ano ou expressão de período (`"2025"`, `"2020-2025"`) |
| `Input` | `str` | ✅ | Nome do insumo de entrada |
| `MassaInput` | `float` | ✅ | Massa de entrada (toneladas) |
| `Output` | `str` | ✅ | Nome do produto de saída |
| `MassaOutput` | `float` | ✅ | Massa de saída (toneladas) |
| `Consumiveis` | `list[dict]` | ✅ | Lista de consumíveis `{nome, fator, escopo}` |
| `ConsumoEspecifico` | `list[float]` | ✅ | Consumos específicos (mesma ordem de Consumiveis) |
| `TaxacaoFronteira` | `bool` | ❌ | CBAM / taxação de fronteira |
| `TaxacaoLocal` | `bool` | ❌ | Sujeito a tributação local de carbono |
| `Tecnologia` | `str` | ❌ | FK → `tecnologias.id` |
| `ConfigOperacional` | `str` | ❌ | Configuração operacional |
| `IntensidadeEmissao` | `float` | calc | Intensidade total (tCO₂/t) |
| `IntensidadeEmissaoEscopo1` | `float` | calc | Intensidade Escopo 1 |
| `IntensidadeEmissaoEscopo2` | `float` | calc | Intensidade Escopo 2 |
| `IntensidadeEmissaoEscopo3` | `float` | calc | Intensidade Escopo 3 |
| `Pegada` | `float` | calc | Pegada acumulada (tCO₂/t) |
| `PegadaEscopo1..3` | `float` | calc | Pegada por escopo |

**Chave composta**: `(ID_ELO, Periodo)`
**Multi-ano**: Cada combinação `(ID_ELO, Periodo)` é um registro distinto.

### 2. `conexoes` (Conexao)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `origem` | `str` | ✅ | FK → `unidades.ID_ELO` |
| `destino` | `str` | ✅ | FK → `unidades.ID_ELO` |
| `massa` | `float` | ❌ | Massa transferida (toneladas) |
| `label` | `str` | ❌ | Rótulo da conexão |
| `periodo` | `str` | ✅ | Período/ano da conexão (deve ser consistente com as unidades) |

**Chave composta**: `(origem, destino, periodo)`
**Restrição**: `origem`/`destino` devem referenciar `ID_ELO` existentes. O `periodo` deve ser consistente com o período das unidades referenciadas.

### 3. `tecnologias` (Tecnologia)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `id` | `str` | ✅ | Identificador único (PK) |
| `nome` | `str` | ✅ | Nome da tecnologia |
| `insumos` | `list[dict]` | ✅ | Perfil de insumos `{nome, fator_consumo}` |
| `unidades` | `list[dict]` | ❌ | Unidades compatíveis com limites |

**Chave**: `id`

### 4. `fatores_emissao` (FatorEmissao)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `grupo_consumivel` | `str` | ✅ | Grupo/categoria |
| `consumivel` | `str` | ✅ | Nome do consumível |
| `escopo` | `str` | ✅ | Escopo GHG (SCOPE 1/2/3) |
| `fator_emissao` | `float` | ✅ | Fator de emissão (tCO₂e/unidade) |
| `kgCO2e_unid` | `str` | ✅ | Unidade de medida |
| `ano` | `int` | ❌ | Ano específico (global se ausente) |
| `data_importacao` | `str` | ❌ | Data da importação |

**Chave composta**: `(consumivel, escopo, ano)`
**Resolução por ano**: Se `ano` for preenchido, o fator é específico para aquele ano. Caso contrário, é o fallback global.

## Relacionamentos

| Origem | Destino | Cardinalidade | Tipo | Campo FK |
|--------|---------|:-------------:|------|----------|
| `conexao.origem` | `unidade.ID_ELO` | N:1 | Obrigatória | `origem` |
| `conexao.destino` | `unidade.ID_ELO` | N:1 | Obrigatória | `destino` |
| `unidade.Tecnologia` | `tecnologia.id` | N:1 | Opcional | `Tecnologia` |
| `unidade.Consumiveis[].nome` | `fator_emissao.consumivel` | N:1 | Implícita | Via nome |
| `conexao.periodo` | `unidade.Periodo` | Consistência | Semântica | `periodo` ↔ `Periodo` |

## Metadados do Schema

```json
{
  "schema_version": "1.2.0",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "source": "app | session_export | import",
  "anos_disponiveis": [2024, 2025]
}
```

## Validações Implementadas

### Validação de Schema (schema.py)

| Regra | Severidade | Descrição |
|-------|:----------:|-----------|
| Campos obrigatórios | Error | Todos os campos `✅` devem estar presentes |
| Tipos de dados | Warning | Tipos devem corresponder ao esperado |
| Unicidade PK simples | Warning | `ID_ELO`, `tecnologia.id` sem duplicatas |
| Unicidade PK composta | Warning | `(consumivel,escopo,ano)`, `(origem,destino,periodo)` sem duplicatas |
| Referência conexão→unidade | Error | `origem`/`destino` devem existir em `unidades` |
| Período válido | Warning | Parseável pelo parser de períodos |

### Validação Relacional (relational.py)

| Regra | Severidade | Tipo | Descrição |
|-------|:----------:|------|-----------|
| PK vazia | Error | `pk_empty` | Campos de chave primária não podem estar vazios |
| PK duplicada | Error | `pk_duplicate` | Chaves primárias compostas devem ser únicas |
| FK ausente | Error | `fk_missing` | Referências devem apontar para registros existentes |
| FK nula obrigatória | Error | `fk_null` | FKs obrigatórias não podem ser nulas |
| Periodo inconsistente | Warning | `periodo_inconsistente` | Periodo da conexão deve existir nas unidades referenciadas |
| Periodo vazio | Warning | `periodo_vazio` | Conexão sem período definido |
| Consumível sem fator | Warning | `consumivel_sem_fator` | Consumível não encontrado nos fatores de emissão |
| Massa negativa | Error | `domain_positive` | MassaInput, MassaOutput, massa ≥ 0 |
| Listas desalinhadas | Error | `domain_length_match` | `len(Consumiveis) == len(ConsumoEspecifico)` |
| Unidade órfã | Info | `orfao` | Unidade sem conexões (isolada no grafo) |
| Tecnologia não usada | Info | `orfao` | Tecnologia não atribuída a nenhuma unidade |

## CLI de Validação

```bash
python -m tools.validate_db --path data/json_db/database.json
python -m tools.validate_db --path data/json_db/database.json --strict
```
