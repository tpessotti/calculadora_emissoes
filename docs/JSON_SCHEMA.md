# JSON DB Schema Documentation

## Overview

The JSON DB is the canonical data storage format for the Calculadora de Emissões CMP.  
This document describes the schema structure, entity fields, and validation rules.

Schema version: **1.0.0**

---

## Master File: `data/json_db/database.json`

```json
{
  "schema_version": "1.0.0",
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T12:00:00",
  "source": "session_export | excel_import | initial_setup",
  "anos_disponiveis": [2024, 2025],
  "fatores_emissao": [...],
  "unidades": [...],
  "conexoes": [...],
  "tecnologias": [...]
}
```

### Metadata Fields

| Field             | Type       | Description                              |
|-------------------|------------|------------------------------------------|
| schema_version    | string     | Semantic version of the schema           |
| created_at        | ISO datetime | When the database was first created    |
| updated_at        | ISO datetime | Last modification timestamp            |
| source            | string     | Origin: `session_export`, `excel_import` |
| anos_disponiveis  | int[]      | List of years with data available        |

---

## Entity: `fatores_emissao`

Emission factors by consumable and GHG Protocol scope.

### Fields

| Field              | Type   | Required | Description                                    |
|--------------------|--------|----------|------------------------------------------------|
| grupo_consumivel   | string | ✅       | Consumable group (e.g., "LAND TRANSPORTATION") |
| consumivel         | string | ✅       | Consumable name (e.g., "DIESEL S10 (BRASIL)")  |
| escopo             | string | ✅       | GHG scope: "SCOPE 1", "SCOPE 2", "SCOPE 3"    |
| fator_emissao      | float  | ✅       | Emission factor (kgCO₂e per unit consumed)     |
| kgCO2e_unid        | string | ✅       | Unit of consumption (e.g., "L", "kWh")         |
| data_importacao    | string | ❌       | Import date (ISO format)                       |
| ano                | int    | ❌       | Year this factor applies to                    |

**Composite key:** (`grupo_consumivel`, `consumivel`, `escopo`)

---

## Entity: `unidades`

Production units in the value chain.

### Fields

| Field                    | Type     | Required | Description                                           |
|--------------------------|----------|----------|-------------------------------------------------------|
| ID_ELO                   | string   | ✅       | Unique identifier for the unit                        |
| Nome                     | string   | ✅       | Unit name                                             |
| Localizacao              | string   | ✅       | Location (state/region)                               |
| Periodo                  | string   | ✅       | Year of the record (e.g., "2025")                     |
| Input                    | string   | ✅       | Input material name                                   |
| MassaInput               | float    | ✅       | Input mass in tonnes                                  |
| Output                   | string   | ✅       | Output material name                                  |
| MassaOutput              | float    | ✅       | Output mass in tonnes                                 |
| Consumiveis              | object[] | ✅       | List of consumables `{nome, fator, escopo}`           |
| ConsumoEspecifico         | float[]  | ✅       | Specific consumption per consumable                   |
| TaxacaoFronteira         | bool     | ❌       | Subject to CBAM/border carbon tax                     |
| TaxacaoLocal             | bool     | ❌       | Subject to local carbon tax                           |
| Tecnologia               | string   | ❌       | Technology ID reference                               |
| ConfigOperacional        | string   | ❌       | Operational configuration label                       |
| Conexao                  | object   | ❌       | Embedded connection `{origem, destino, massa, label}` |
| IntensidadeEmissao       | float    | ❌       | Calculated: total emission intensity (tCO₂/t)        |
| IntensidadeEmissaoEscopo1| float    | ❌       | Calculated: scope 1 intensity                         |
| IntensidadeEmissaoEscopo2| float    | ❌       | Calculated: scope 2 intensity                         |
| IntensidadeEmissaoEscopo3| float    | ❌       | Calculated: scope 3 intensity                         |
| Pegada                   | float    | ❌       | Calculated: total footprint (tCO₂/t product)         |
| PegadaEscopo1            | float    | ❌       | Calculated: scope 1 footprint                         |
| PegadaEscopo2            | float    | ❌       | Calculated: scope 2 footprint                         |
| PegadaEscopo3            | float    | ❌       | Calculated: scope 3 footprint                         |

**Primary key:** `ID_ELO`  
**Multi-year support:** Field `Periodo` contains the year of the record.

### Consumiveis Structure

```json
{
  "nome": "DIESEL S10 (BRASIL)",
  "fator": 2.35,
  "escopo": "SCOPE 1"
}
```

---

## Entity: `conexoes`

Directed edges (material flows) between production units.

### Fields

| Field   | Type   | Required | Description                                   |
|---------|--------|----------|-----------------------------------------------|
| origem  | string | ✅       | Source unit ID_ELO                            |
| destino | string | ✅       | Target unit ID_ELO                            |
| massa   | float  | ❌       | Mass transferred in tonnes (default: 0)       |
| label   | string | ❌       | Flow label (default: "Fluxo")                 |

**Composite key:** (`origem`, `destino`)  
**Referential integrity:** Both `origem` and `destino` must reference existing units.

---

## Entity: `tecnologias`

Alternative technologies with consumable profiles.

### Fields

| Field    | Type     | Required | Description                                 |
|----------|----------|----------|---------------------------------------------|
| id       | string   | ✅       | Unique technology identifier                |
| nome     | string   | ✅       | Technology name                             |
| insumos  | object[] | ✅       | List of inputs `{nome, fator_consumo}`      |
| unidades | object[] | ❌       | Units using this technology                 |

**Primary key:** `id`

### Insumos Structure

```json
{
  "nome": "DIESEL S10 (BRASIL)",
  "fator_consumo": 0.5
}
```

---

## Validation Rules

1. **Required fields** must be present and non-null.
2. **Mass fields** (MassaInput, MassaOutput, massa) must be ≥ 0.
3. **Consumiveis** and **ConsumoEspecifico** arrays must have the same length.
4. **Referential integrity**: Connection origins/destinations must reference existing unit IDs.
5. **Emission factors** should have non-negative values.
6. **Escopo** values should be "SCOPE 1", "SCOPE 2", or "SCOPE 3".

---

## Multi-Year Strategy

- Each unit record has a `Periodo` field containing the year.
- The sidebar year selector filters data by this field.
- When switching years, calculation caches are invalidated.
- The `anos_disponiveis` metadata field tracks all years with data.
- Future: per-year snapshots in `data/json_db/{year}/` directories.

---

## Migration from Excel

The Excel template (`core/io/excel_io.py`) provides:
- **README** sheet with instructions
- **Unidades** sheet with all required fields
- **Conexoes** sheet for flows
- **Tecnologias** sheet for alt technologies  
- **Fatores_Emissao** sheet (pre-populated reference)

Use `excel_to_json_db()` to convert Excel → JSON DB format.
