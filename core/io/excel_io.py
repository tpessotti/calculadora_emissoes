"""
Leitura/escrita de arquivos Excel — migração e template.

Responsável por:
- Converter Excel → JSON DB (migração)
- Gerar template Excel de input
"""
from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from openpyxl import Workbook
    from openpyxl.styles import (
        Alignment, Border, Font, PatternFill, Side,
    )
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════
#  ESTILOS COMUNS
# ═══════════════════════════════════════════════════════════════════
if OPENPYXL_AVAILABLE:
    _HDR_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    _HDR_FILL = PatternFill(start_color="4c8061", end_color="4c8061", fill_type="solid")
    _OPT_FILL = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
    _REQ_FILL = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
    _THIN_BORDER = Border(
        left=Side(style="thin", color="D0D0D0"),
        right=Side(style="thin", color="D0D0D0"),
        top=Side(style="thin", color="D0D0D0"),
        bottom=Side(style="thin", color="D0D0D0"),
    )
    _CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


# ═══════════════════════════════════════════════════════════════════
#  GERAÇÃO DE TEMPLATE EXCEL
# ═══════════════════════════════════════════════════════════════════

def gerar_template_excel(
    ano: Optional[int] = None,
    fatores_emissao: Optional[List[Dict]] = None,
) -> bytes:
    """Gera template Excel em memória para input de dados.

    Args:
        ano: Ano padrão a incluir.
        fatores_emissao: Lista de fatores para preencher dropdown.

    Returns:
        Conteúdo do arquivo .xlsx como bytes.

    Raises:
        ImportError: Se openpyxl não estiver instalado.
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl é necessário para gerar templates Excel.")

    wb = Workbook()
    ano = ano or datetime.now().year

    # ─── ABA README ─────────────────────────────────────────────
    ws_readme = wb.active
    ws_readme.title = "README"
    ws_readme.sheet_properties.tabColor = "4c8061"

    readme_content = [
        ["TEMPLATE DE IMPORTAÇÃO — Calculadora de Emissões CMP"],
        [""],
        ["Este arquivo contém as abas necessárias para importar dados"],
        ["na Calculadora de Emissões de Carbono - CMP."],
        [""],
        ["INSTRUÇÕES:"],
        ["1. Preencha a aba 'Unidades' com as unidades produtivas da cadeia."],
        ["2. Preencha a aba 'Conexoes' com os fluxos entre unidades."],
        ["3. Preencha a aba 'Tecnologias' com tecnologias alternativas (opcional)."],
        ["4. A aba 'Fatores_Emissao' é referência; importe-a separadamente se necessário."],
        [""],
        ["CAMPOS OBRIGATÓRIOS estão marcados com (*) na linha de cabeçalho."],
        ["Campos com fundo laranja claro são obrigatórios."],
        ["Campos com fundo verde claro são opcionais."],
        [""],
        ["REGRAS:"],
        ["- ID_ELO deve ser único por unidade produtiva."],
        ["- Periodo deve ser um ano (ex: 2025)."],
        ["- Massas em toneladas (t)."],
        ["- Consumíveis e ConsumoEspecifico são listas separadas por ';'."],
        ["  Exemplo Consumíveis: DIESEL S10 (BRASIL);ELETRICIDADE"],
        ["  Exemplo ConsumoEspecifico: 0.5;1.2"],
        ["- Origem e Destino em Conexoes devem corresponder a ID_ELO existentes."],
        [""],
        [f"Ano padrão: {ano}"],
        [f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"],
        ["Versão do template: 1.0"],
    ]

    for i, row in enumerate(readme_content):
        cell = ws_readme.cell(row=i + 1, column=1, value=row[0] if row else "")
        if i == 0:
            cell.font = Font(name="Calibri", bold=True, size=14, color="4c8061")
        elif row and row[0].startswith("INSTRUÇÕES") or (row and row[0].startswith("REGRAS")):
            cell.font = Font(name="Calibri", bold=True, size=12, color="333333")

    ws_readme.column_dimensions["A"].width = 80

    # ─── ABA UNIDADES ───────────────────────────────────────────
    ws_u = wb.create_sheet("Unidades")
    ws_u.sheet_properties.tabColor = "0066CC"

    unidades_headers = [
        ("ID_ELO *", True),
        ("Nome *", True),
        ("Localizacao *", True),
        ("Periodo *", True),
        ("Input", False),
        ("MassaInput (t) *", True),
        ("Output", False),
        ("MassaOutput (t) *", True),
        ("Consumiveis", False),
        ("ConsumoEspecifico", False),
        ("TaxacaoFronteira", False),
        ("TaxacaoLocal", False),
        ("Tecnologia", False),
    ]
    _write_headers(ws_u, unidades_headers)

    # Exemplo de dados
    exemplo_unidade = [
        "U001", "Mina de Ferro", "Minas Gerais", str(ano),
        "Minério ROM", 1000.0, "Concentrado Fe", 500.0,
        "DIESEL S10 (BRASIL);ELETRICIDADE", "0.5;1.2",
        "FALSE", "FALSE", "",
    ]
    _write_example_row(ws_u, 3, exemplo_unidade)
    _auto_width(ws_u)

    # Validação para TaxacaoFronteira e TaxacaoLocal
    dv_bool = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=True)
    dv_bool.error = "Valor deve ser TRUE ou FALSE"
    dv_bool.errorTitle = "Valor inválido"
    ws_u.add_data_validation(dv_bool)
    dv_bool.add(f"K2:L1000")

    # ─── ABA CONEXÕES ───────────────────────────────────────────
    ws_c = wb.create_sheet("Conexoes")
    ws_c.sheet_properties.tabColor = "CC6600"

    conexoes_headers = [
        ("Origem (ID_ELO) *", True),
        ("Destino (ID_ELO) *", True),
        ("Massa (t)", False),
        ("Label", False),
    ]
    _write_headers(ws_c, conexoes_headers)

    exemplo_conexao = ["U001", "U002", 500.0, "Fluxo Concentrado"]
    _write_example_row(ws_c, 3, exemplo_conexao)
    _auto_width(ws_c)

    # ─── ABA TECNOLOGIAS ────────────────────────────────────────
    ws_t = wb.create_sheet("Tecnologias")
    ws_t.sheet_properties.tabColor = "7C3AED"

    tec_headers = [
        ("ID *", True),
        ("Nome *", True),
        ("Insumos (nome1;nome2;...)", True),
        ("Fator_Consumo (fc1;fc2;...)", True),
    ]
    _write_headers(ws_t, tec_headers)

    exemplo_tec = ["TEC001", "Processo Convencional", "DIESEL S10 (BRASIL);ELETRICIDADE", "0.5;1.2"]
    _write_example_row(ws_t, 3, exemplo_tec)
    _auto_width(ws_t)

    # ─── ABA FATORES DE EMISSÃO (referência) ────────────────────
    ws_f = wb.create_sheet("Fatores_Emissao")
    ws_f.sheet_properties.tabColor = "059669"

    fatores_headers = [
        ("Grupo_Consumivel *", True),
        ("Consumivel *", True),
        ("Escopo *", True),
        ("Fator_Emissao *", True),
        ("kgCO2e_Unid *", True),
    ]
    _write_headers(ws_f, fatores_headers)

    # Preencher com fatores existentes se disponíveis
    if fatores_emissao:
        for i, f in enumerate(fatores_emissao[:200]):  # Limitar a 200 linhas
            row = i + 2
            ws_f.cell(row=row, column=1, value=f.get("grupo_consumivel", ""))
            ws_f.cell(row=row, column=2, value=f.get("consumivel", ""))
            ws_f.cell(row=row, column=3, value=f.get("escopo", ""))
            ws_f.cell(row=row, column=4, value=f.get("fator_emissao", 0.0))
            ws_f.cell(row=row, column=5, value=f.get("kgCO2e_unid", ""))
            for col in range(1, 6):
                ws_f.cell(row=row, column=col).border = _THIN_BORDER
    else:
        exemplo_fator = ["LAND TRANSPORTATION", "DIESEL S10 (BRASIL)", "SCOPE 1", 2.35, "L"]
        _write_example_row(ws_f, 3, exemplo_fator)

    # Validação de escopo
    dv_escopo = DataValidation(
        type="list",
        formula1='"SCOPE 1,SCOPE 2,SCOPE 3"',
        allow_blank=True,
    )
    ws_f.add_data_validation(dv_escopo)
    dv_escopo.add(f"C2:C1000")

    _auto_width(ws_f)

    # ─── SALVAR ─────────────────────────────────────────────────
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
#  MIGRAÇÃO EXCEL → JSON
# ═══════════════════════════════════════════════════════════════════

def excel_to_json_db(filepath_or_bytes: Any) -> Dict[str, Any]:
    """Converte um arquivo Excel (template) para o formato JSON DB.

    Args:
        filepath_or_bytes: Caminho do arquivo ou bytes/BytesIO.

    Returns:
        Dict no formato do schema do banco de dados.
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas é necessário para migração Excel → JSON.")

    from core.validation.schema import SCHEMA_VERSION

    sheets = pd.read_excel(filepath_or_bytes, sheet_name=None)

    result: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "source": "excel_import",
        "anos_disponiveis": [],
        "fatores_emissao": [],
        "unidades": [],
        "conexoes": [],
        "tecnologias": [],
    }

    # Processar aba Fatores_Emissao
    if "Fatores_Emissao" in sheets:
        df = sheets["Fatores_Emissao"].dropna(how="all")
        col_map = {
            "Grupo_Consumivel": "grupo_consumivel",
            "Consumivel": "consumivel",
            "Escopo": "escopo",
            "Fator_Emissao": "fator_emissao",
            "kgCO2e_Unid": "kgCO2e_unid",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        # Remover linhas com cabeçalho duplicado ou exemplo na row 2
        df = df[df.get("grupo_consumivel", pd.Series(dtype=str)).notna()]
        result["fatores_emissao"] = df.to_dict(orient="records")

    # Processar aba Unidades
    anos_encontrados = set()
    if "Unidades" in sheets:
        df = sheets["Unidades"].dropna(subset=["ID_ELO"] if "ID_ELO" in sheets["Unidades"].columns else [])
        # Normalizar nomes das colunas (remover * e espaços)
        df.columns = [c.replace(" *", "").replace("*", "").strip() for c in df.columns]
        col_map = {
            "ID_ELO": "ID_ELO",
            "Nome": "Nome",
            "Localizacao": "Localizacao",
            "Periodo": "Periodo",
            "Input": "Input",
            "MassaInput (t)": "MassaInput",
            "MassaInput": "MassaInput",
            "Output": "Output",
            "MassaOutput (t)": "MassaOutput",
            "MassaOutput": "MassaOutput",
            "TaxacaoFronteira": "TaxacaoFronteira",
            "TaxacaoLocal": "TaxacaoLocal",
            "Tecnologia": "Tecnologia",
            "Consumiveis": "Consumiveis",
            "ConsumoEspecifico": "ConsumoEspecifico",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        for _, row in df.iterrows():
            # Parse consumíveis (formato: "item1;item2")
            consumiveis_raw = str(row.get("Consumiveis", ""))
            consumo_raw = str(row.get("ConsumoEspecifico", ""))

            consumiveis = []
            consumo_especifico = []
            if consumiveis_raw and consumiveis_raw != "nan":
                nomes = [n.strip() for n in consumiveis_raw.split(";") if n.strip()]
                ces = [c.strip() for c in consumo_raw.split(";") if c.strip()] if consumo_raw != "nan" else []

                for i, nome in enumerate(nomes):
                    ce = float(ces[i]) if i < len(ces) else 0.0
                    # Buscar fator nos fatores importados
                    fator = 0.0
                    escopo = "1"
                    for f in result["fatores_emissao"]:
                        if f.get("consumivel") == nome:
                            fator = f.get("fator_emissao", 0.0)
                            escopo = f.get("escopo", "1")
                            break
                    consumiveis.append({"nome": nome, "fator": fator, "escopo": escopo})
                    consumo_especifico.append(ce)

            try:
                periodo = str(int(float(row.get("Periodo", datetime.now().year))))
            except (ValueError, TypeError):
                periodo = str(datetime.now().year)
            anos_encontrados.add(int(periodo))

            unidade = {
                "ID_ELO": str(row.get("ID_ELO", "")),
                "Nome": str(row.get("Nome", "")),
                "Localizacao": str(row.get("Localizacao", "")),
                "Periodo": periodo,
                "Input": str(row.get("Input", "")),
                "MassaInput": float(row.get("MassaInput", 0)),
                "Output": str(row.get("Output", "")),
                "MassaOutput": float(row.get("MassaOutput", 0)),
                "Consumiveis": consumiveis,
                "ConsumoEspecifico": consumo_especifico,
                "TaxacaoFronteira": _parse_bool(row.get("TaxacaoFronteira")),
                "TaxacaoLocal": _parse_bool(row.get("TaxacaoLocal")),
                "Tecnologia": str(row.get("Tecnologia", "")) if pd.notna(row.get("Tecnologia")) else None,
            }
            result["unidades"].append(unidade)

    # Processar aba Conexoes
    if "Conexoes" in sheets:
        df = sheets["Conexoes"].dropna(how="all")
        df.columns = [c.replace(" *", "").replace("*", "").replace("(ID_ELO) ", "").replace("(ID_ELO)", "").strip() for c in df.columns]
        col_map = {
            "Origem": "origem",
            "Destino": "destino",
            "Massa (t)": "massa",
            "Massa": "massa",
            "Label": "label",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        for _, row in df.iterrows():
            if pd.notna(row.get("origem")) and pd.notna(row.get("destino")):
                result["conexoes"].append({
                    "origem": str(row["origem"]).strip(),
                    "destino": str(row["destino"]).strip(),
                    "massa": float(row.get("massa", 0)),
                    "label": str(row.get("label", "Fluxo")),
                })

    # Processar aba Tecnologias
    if "Tecnologias" in sheets:
        df = sheets["Tecnologias"].dropna(how="all")
        df.columns = [c.replace(" *", "").replace("*", "").strip() for c in df.columns]
        for _, row in df.iterrows():
            insumos_raw = str(row.get("Insumos (nome1;nome2;...)", row.get("Insumos", "")))
            fc_raw = str(row.get("Fator_Consumo (fc1;fc2;...)", row.get("Fator_Consumo", "")))

            insumos = []
            if insumos_raw and insumos_raw != "nan":
                nomes = [n.strip() for n in insumos_raw.split(";") if n.strip()]
                fcs = [c.strip() for c in fc_raw.split(";") if c.strip()] if fc_raw != "nan" else []
                for i, nome in enumerate(nomes):
                    fc = float(fcs[i]) if i < len(fcs) else 1.0
                    insumos.append({"nome": nome, "fator_consumo": fc})

            tec = {
                "id": str(row.get("ID", "")),
                "nome": str(row.get("Nome", "")),
                "insumos": insumos,
                "unidades": [],
            }
            result["tecnologias"].append(tec)

    result["anos_disponiveis"] = sorted(anos_encontrados) if anos_encontrados else [datetime.now().year]
    return result


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def _parse_bool(val: Any) -> bool:
    """Parse boolean de vários formatos."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().upper() in ("TRUE", "1", "SIM", "YES", "✅")
    return False


def _write_headers(ws: Any, headers: list) -> None:
    """Escreve cabeçalhos com formatação."""
    for col_idx, (label, required) in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = _HDR_FONT
        cell.fill = _HDR_FILL
        cell.alignment = _CENTER
        cell.border = _THIN_BORDER

        # Linha de dica (row 2)
        hint_cell = ws.cell(row=2, column=col_idx, value="(obrigatório)" if required else "(opcional)")
        hint_cell.font = Font(name="Calibri", italic=True, size=9, color="888888")
        hint_cell.fill = _REQ_FILL if required else _OPT_FILL
        hint_cell.alignment = _CENTER
        hint_cell.border = _THIN_BORDER


def _write_example_row(ws: Any, row: int, values: list) -> None:
    """Escreve linha de exemplo com formatação."""
    for col_idx, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col_idx, value=val)
        cell.font = Font(name="Calibri", italic=True, color="999999", size=10)
        cell.border = _THIN_BORDER


def _auto_width(ws: Any) -> None:
    """Ajusta largura das colunas automaticamente."""
    for col_cells in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 4, 45)
