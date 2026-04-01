"""
Script de migração para o modelo multi-input/multi-output.

Uso:
    C:/calculadora_emissoes/venv/Scripts/python.exe -m tools.migrate_multi_io
    C:/calculadora_emissoes/venv/Scripts/python.exe -m tools.migrate_multi_io --path data/json_db/database.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
sys.path.insert(0, _root)
sys.path.insert(0, _src)

from core.io.json_io import migrate_database_payload, save_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra database.json para inputs/outputs em lista.")
    parser.add_argument(
        "--path",
        "-p",
        default=os.path.join(_root, "data", "json_db", "database.json"),
        help="Caminho do database.json",
    )
    args = parser.parse_args()

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"ERRO: arquivo não encontrado: {path}")
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    migrated, changed = migrate_database_payload(data)
    if not changed:
        print("Nenhuma migração necessária. Arquivo já está no formato novo.")
        return 0

    backup_name = f"{path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, backup_name)

    ok = save_database(path, migrated)
    if not ok:
        print("ERRO: falha ao salvar arquivo migrado.")
        return 1

    print(f"Migração concluída: {path}")
    print(f"Backup criado em: {backup_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
