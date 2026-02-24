"""
Resolução de fatores de emissão com suporte a ano.

Implementa busca de fator por (consumível, escopo, ano) com fallback
configurável para fator global (sem ano).

Estratégia de resolução:
  1. Buscar fator exato: (consumivel, escopo, ano)
  2. Fallback: fator sem campo "ano" (global)
  3. Se nenhum encontrado: retorna 0.0

O fallback é habilitado por padrão — pode ser desabilitado
via ``strict=True`` para forçar exigência de fatores por ano.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Índice de fatores (cache por sessão)
# ═══════════════════════════════════════════════════════════════════

class FatorIndex:
    """Índice para busca rápida de fatores de emissão.

    Estrutura interna:
        _idx[(consumivel, escopo, ano)] → dict do fator
        _idx[(consumivel, escopo, None)] → dict do fator (global)
    """

    def __init__(self, fatores: List[Dict[str, Any]]) -> None:
        self._fatores = fatores
        self._idx: Dict[Tuple[str, str, Optional[int]], Dict[str, Any]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Constrói o índice a partir da lista de fatores."""
        for f in self._fatores:
            consumivel = str(f.get("consumivel", "")).strip().upper()
            escopo = _normalizar_escopo(str(f.get("escopo", "")))
            ano_raw = f.get("ano", None)
            ano: Optional[int] = None
            if ano_raw is not None:
                try:
                    ano = int(ano_raw)
                except (ValueError, TypeError):
                    pass

            key = (consumivel, escopo, ano)
            if key not in self._idx:
                self._idx[key] = f
            # Não sobrescreve se já existe (primeiro encontrado ganha)

    def get_fator(
        self,
        consumivel: str,
        escopo: str,
        ano: Optional[int] = None,
        strict: bool = False,
    ) -> float:
        """Busca o fator de emissão para um consumível/escopo/ano.

        Args:
            consumivel: Nome do consumível (case-insensitive).
            escopo: Escopo GHG (normalizado para "1", "2" ou "3").
            ano: Ano específico (None para busca global).
            strict: Se True, não faz fallback para fator global.

        Returns:
            Valor do fator de emissão, ou 0.0 se não encontrado.
        """
        cons_upper = consumivel.strip().upper()
        esc_norm = _normalizar_escopo(escopo)

        # 1. Busca exata com ano
        if ano is not None:
            key_exact = (cons_upper, esc_norm, ano)
            if key_exact in self._idx:
                return float(self._idx[key_exact].get("fator_emissao", 0.0))

        # 2. Fallback para fator global (sem ano)
        if not strict:
            key_global = (cons_upper, esc_norm, None)
            if key_global in self._idx:
                fv = float(self._idx[key_global].get("fator_emissao", 0.0))
                if ano is not None:
                    logger.debug(
                        "Fallback global para %s/%s ano=%d (fator=%.4f)",
                        consumivel, escopo, ano, fv,
                    )
                return fv

        return 0.0

    def get_fator_dict(
        self,
        consumivel: str,
        escopo: str,
        ano: Optional[int] = None,
        strict: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Similar a get_fator mas retorna o dict completo do fator."""
        cons_upper = consumivel.strip().upper()
        esc_norm = _normalizar_escopo(escopo)

        if ano is not None:
            key_exact = (cons_upper, esc_norm, ano)
            if key_exact in self._idx:
                return self._idx[key_exact]

        if not strict:
            key_global = (cons_upper, esc_norm, None)
            if key_global in self._idx:
                return self._idx[key_global]

        return None

    def listar_anos_disponiveis(self, consumivel: str, escopo: str) -> List[int]:
        """Lista anos com fatores específicos para um consumível/escopo."""
        cons_upper = consumivel.strip().upper()
        esc_norm = _normalizar_escopo(escopo)
        anos = []
        for (c, e, a), _ in self._idx.items():
            if c == cons_upper and e == esc_norm and a is not None:
                anos.append(a)
        return sorted(anos)

    def __len__(self) -> int:
        return len(self._idx)


# ═══════════════════════════════════════════════════════════════════
#  Funções auxiliares
# ═══════════════════════════════════════════════════════════════════

def _normalizar_escopo(escopo: str) -> str:
    """Normaliza strings de escopo para '1', '2' ou '3'.

    Aceita: "1", "SCOPE 1", "Escopo 1", "scope1" etc.
    """
    s = escopo.strip().upper().replace("SCOPE", "").replace("ESCOPO", "").strip()
    if "1" in s:
        return "1"
    elif "2" in s:
        return "2"
    elif "3" in s:
        return "3"
    return s


def resolver_fator_consumivel(
    consumivel_nome: str,
    escopo: str,
    ano: Optional[int],
    fatores: List[Dict[str, Any]],
    strict: bool = False,
) -> float:
    """Função de conveniência para resolver fator sem instanciar FatorIndex.

    Para chamadas únicas. Para múltiplas resoluções, use FatorIndex diretamente.

    Args:
        consumivel_nome: Nome do consumível.
        escopo: Escopo GHG.
        ano: Ano (ou None para global).
        fatores: Lista de fatores de emissão.
        strict: Não usar fallback global.

    Returns:
        Valor do fator.
    """
    idx = FatorIndex(fatores)
    return idx.get_fator(consumivel_nome, escopo, ano, strict=strict)


def fatores_para_ano(
    fatores: List[Dict[str, Any]],
    ano: int,
) -> List[Dict[str, Any]]:
    """Filtra/resolve fatores para um ano específico.

    Para cada combinação (consumivel, escopo):
      - Se existe fator com ano=<ano>, usa esse.
      - Senão, usa o fator global (sem ano).

    Args:
        fatores: Lista completa de fatores.
        ano: Ano alvo.

    Returns:
        Lista de fatores resolvidos para o ano (sem duplicatas).
    """
    idx = FatorIndex(fatores)
    vistos: set[Tuple[str, str]] = set()
    resultado: list[Dict[str, Any]] = []

    for f in fatores:
        cons = str(f.get("consumivel", "")).strip().upper()
        esc = _normalizar_escopo(str(f.get("escopo", "")))
        key = (cons, esc)

        if key in vistos:
            continue
        vistos.add(key)

        # Buscar melhor fator para o ano
        fator_dict = idx.get_fator_dict(cons, esc, ano=ano)
        if fator_dict is not None:
            resultado.append(fator_dict)

    return resultado
