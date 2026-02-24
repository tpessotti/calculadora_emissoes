# ERD — Diagrama de Relacionamento de Entidades

> Schema v1.1.0 · Calculadora de Emissões de Carbono

## Visão Geral

```
┌─────────────────────┐       ┌─────────────────────┐
│  FATOR_EMISSAO      │       │    TECNOLOGIA        │
├─────────────────────┤       ├─────────────────────┤
│ PK grupo_consumivel │       │ PK id               │
│ PK consumivel       │       │    nome              │
│ PK escopo           │       │    insumos[]         │
│ PK ano  (opcional)  │       │    unidades[]        │
│    fator_emissao    │       └──────────┬──────────┘
│    kgCO2e_unid      │                  │ 0..N
│    data_importacao   │                  │ referencia
└─────────────────────┘                  │
                                         ▼
┌─────────────────────┐       ┌─────────────────────┐
│     CONEXAO          │       │  UNIDADE_PRODUTIVA   │
├─────────────────────┤       ├─────────────────────┤
│ PK origem  ─────────┼──────▶│ PK ID_ELO            │
│ PK destino ─────────┼──────▶│    Nome               │
│    massa             │       │    Localizacao        │
│    label             │       │    Periodo            │
└─────────────────────┘       │    Input / MassaInput  │
                               │    Output / MassaOutput│
                               │    Consumiveis[]       │
                               │    ConsumoEspecifico[]  │
                               │    TaxacaoFronteira     │
                               │    TaxacaoLocal         │
                               │ FK Tecnologia → id     │
                               │    ConfigOperacional    │
                               │* IntensidadeEmissao     │
                               │* Pegada                 │
                               └─────────────────────┘
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

**Chave**: `ID_ELO`
**Multi-ano**: Controlado pelo campo `Periodo`.

### 2. `conexoes` (Conexao)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `origem` | `str` | ✅ | FK → `unidades.ID_ELO` |
| `destino` | `str` | ✅ | FK → `unidades.ID_ELO` |
| `massa` | `float` | ❌ | Massa transferida (toneladas) |
| `label` | `str` | ❌ | Rótulo da conexão |

**Chave composta**: `(origem, destino)`
**Restrição**: Ambos devem referenciar `ID_ELO` existentes.

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

## Metadados do Schema

```json
{
  "schema_version": "1.1.0",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "source": "app | session_export | import",
  "anos_disponiveis": [2024, 2025]
}
```

## Validações Implementadas

| Regra | Severidade | Descrição |
|-------|:----------:|-----------|
| Campos obrigatórios | Error | Todos os campos `✅` devem estar presentes |
| Massa não-negativa | Error | `MassaInput`, `MassaOutput` ≥ 0 |
| Consumiveis/CE alinhados | Error | `len(Consumiveis) == len(ConsumoEspecifico)` |
| Referência conexão→unidade | Error | `origem`/`destino` devem existir em `unidades` |
| Referência unidade→tecnologia | Warning | `Tecnologia` deve existir em `tecnologias` |
| Unicidade ID_ELO | Warning | Sem duplicatas |
| Unicidade fator (consumivel,escopo,ano) | Warning | Sem duplicatas na chave composta |
| Período válido | Warning | Parseável pelo parser de períodos |
| Fator negativo | Warning | `fator_emissao` ≥ 0 |

## CLI de Validação

```bash
python -m tools.validate_db --path data/json_db/database.json
python -m tools.validate_db --path data/json_db/database.json --strict
```
