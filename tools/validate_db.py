"""
CLI para validação do banco de dados JSON.

Uso:
    python -m tools.validate_db --path data/json_db/database.json
    python -m tools.validate_db --path data/json_db/database.json --strict
    python -m tools.validate_db  # usa caminho padrão

Saída:
    Relatório de validação com erros e avisos.
    Exit code: 0 se válido, 1 se inválido.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Ajustar path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, "src")
sys.path.insert(0, _root)
sys.path.insert(0, _src)


DEFAULT_PATH = os.path.join(_root, "data", "json_db", "database.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validador do banco de dados JSON da Calculadora de Emissões.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python -m tools.validate_db\n"
            "  python -m tools.validate_db --path meu_banco.json\n"
            "  python -m tools.validate_db --path data/json_db/database.json --strict\n"
        ),
    )
    parser.add_argument(
        "--path", "-p",
        type=str,
        default=DEFAULT_PATH,
        help=f"Caminho do arquivo JSON a validar (padrão: {DEFAULT_PATH})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Tratar avisos (warnings) como erros.",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Saída em formato JSON em vez de texto.",
    )
    args = parser.parse_args()

    filepath = os.path.abspath(args.path)

    # Carregar arquivo
    if not os.path.exists(filepath):
        print(f"ERRO: Arquivo não encontrado: {filepath}", file=sys.stderr)
        return 1

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERRO: JSON inválido em {filepath}: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERRO: Não foi possível ler {filepath}: {e}", file=sys.stderr)
        return 1

    # Validar
    from core.validation.schema import validar_database, ValidationReport

    report: ValidationReport = validar_database(data)

    # Saída
    if args.json_output:
        output = {
            "arquivo": filepath,
            "valido": report.is_valid,
            "total_registros": report.total_registros,
            "registros_validos": report.registros_validos,
            "erros": [
                {
                    "entidade": e.entidade,
                    "indice": e.indice,
                    "campo": e.campo,
                    "mensagem": e.mensagem,
                    "severidade": e.severidade,
                }
                for e in report.erros
            ],
            "avisos": [
                {
                    "entidade": w.entidade,
                    "indice": w.indice,
                    "campo": w.campo,
                    "mensagem": w.mensagem,
                    "severidade": w.severidade,
                }
                for w in report.avisos
            ],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"╔══════════════════════════════════════════╗")
        print(f"║  Validação: {filepath}")
        print(f"╚══════════════════════════════════════════╝")
        print()
        print(report.summary())
        print()

        if report.avisos:
            print(f"Avisos ({len(report.avisos)}):")
            for w in report.avisos:
                print(f"  ⚠️  {w}")
            print()

    # Determinar exit code
    is_fail = not report.is_valid
    if args.strict and report.avisos:
        is_fail = True
        if not args.json_output:
            print("⚠️  Modo --strict: avisos tratados como erros.")

    if not args.json_output:
        if is_fail:
            print("❌ VALIDAÇÃO FALHOU")
        else:
            print("✅ VALIDAÇÃO OK")

    return 1 if is_fail else 0


if __name__ == "__main__":
    sys.exit(main())
