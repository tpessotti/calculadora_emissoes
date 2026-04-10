"""
Emission factor importers.

Supports JSON (from existing fatores_emissao.json format) and
Excel (using python-calamine for fast reading, matching config_fatores.json mapping).

Fixes P14: the Excel row-offset mapping is now version-pinned and validated
rather than silently breaking when the template changes.
"""
from __future__ import annotations

import json
import logging
from typing import IO, Tuple

from django.db import transaction

from .models import FatorEmissao

logger = logging.getLogger(__name__)

EXPECTED_EXCEL_HEADERS = {"consumivel", "fator_emissao", "escopo", "kgco2e_unid"}


@transaction.atomic
def importar_fatores_json(json_text: str) -> Tuple[int, int]:
    """Import factors from a JSON string.

    Returns (imported_count, skipped_count).
    Skips rows that already exist (same consumivel+escopo+ano).
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("JSON deve ser uma lista de objetos.")

    imported = 0
    skipped = 0

    for row in data:
        ano_raw = row.get("ano")
        ano = int(ano_raw) if ano_raw is not None else None

        _, created = FatorEmissao.objects.get_or_create(
            consumivel=str(row.get("consumivel", "")).strip(),
            escopo=str(row.get("escopo", "")).strip(),
            ano=ano,
            defaults={
                "grupo_consumivel": row.get("grupo_consumivel", ""),
                "fator_emissao": float(row.get("fator_emissao") or 0),
                "kgco2e_unid": float(row.get("kgCO2e_unid") or row.get("kgco2e_unid") or 0),
                "unidade": row.get("unidade", ""),
                "fonte": row.get("fonte", ""),
            },
        )
        if created:
            imported += 1
        else:
            skipped += 1

    return imported, skipped


@transaction.atomic
def importar_fatores_excel(file_obj: IO[bytes]) -> Tuple[int, int]:
    """Import factors from an Excel file object.

    Uses python-calamine for fast reading.
    Expects headers in row 1: consumivel, grupo_consumivel, escopo,
    fator_emissao, kgCO2e_unid, unidade, ano (optional), fonte (optional).
    """
    try:
        from python_calamine import CalamineWorkbook
    except ImportError:
        raise ImportError("python-calamine is required for Excel import. Run: pip install python-calamine")

    wb = CalamineWorkbook.from_filelike(file_obj)
    sheet = wb.get_sheet_by_index(0)
    rows = list(sheet.to_python())

    if not rows:
        raise ValueError("Planilha vazia.")

    headers = [str(h).strip().lower().replace(" ", "_") for h in rows[0]]
    missing = EXPECTED_EXCEL_HEADERS - set(headers)
    if missing:
        raise ValueError(
            f"Colunas obrigatórias ausentes na planilha: {', '.join(sorted(missing))}. "
            "Verifique se está usando o template correto."
        )

    imported = 0
    skipped = 0

    for i, row in enumerate(rows[1:], start=2):
        if len(row) < len(headers):
            row = list(row) + [None] * (len(headers) - len(row))
        record = dict(zip(headers, row))

        consumivel = str(record.get("consumivel") or "").strip()
        escopo = str(record.get("escopo") or "").strip()
        if not consumivel or not escopo:
            logger.debug("Linha %d ignorada: consumível ou escopo vazio.", i)
            skipped += 1
            continue

        ano_raw = record.get("ano")
        try:
            ano = int(ano_raw) if ano_raw is not None and str(ano_raw).strip() else None
        except (ValueError, TypeError):
            ano = None

        _, created = FatorEmissao.objects.get_or_create(
            consumivel=consumivel,
            escopo=escopo,
            ano=ano,
            defaults={
                "grupo_consumivel": str(record.get("grupo_consumivel") or ""),
                "fator_emissao": float(record.get("fator_emissao") or 0),
                "kgco2e_unid": float(record.get("kgco2e_unid") or 0),
                "unidade": str(record.get("unidade") or ""),
                "fonte": str(record.get("fonte") or ""),
            },
        )
        if created:
            imported += 1
        else:
            skipped += 1

    return imported, skipped
