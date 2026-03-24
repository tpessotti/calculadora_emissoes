from __future__ import annotations

from typing import List, Dict, Set, Optional
from database import UnidadeProdutiva
import streamlit as st
from core.units import (
    convert_mass, get_default_mass_unit_from_session,
    co2e_label, co2e_intensity_label, convert_co2e, normalize_unit,
)


class EmissionCalculator:
    # ═══════════════════════════════════════════════════════════════
    #  CÁLCULO POR UNIDADE
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def calcular_emissoes(unidade: UnidadeProdutiva) -> UnidadeProdutiva:
        """Calcula a intensidade de emissão por escopo e total da unidade.

        Unidades internas (canônicas):
          IntensidadeEmissao*  →  kgCO₂e por tonelada de output
          Pegada*              →  kgCO₂e por tonelada de output (lifecycle,
                                  atualizado depois de propagar_pegada)

        ConsumoEspecifico é armazenado em [unid_consumível / mass_unit].
        Escala para tonelada = convert_mass(1 t → mass_unit) garante que
        os fatores (kgCO₂e/unid_consumível) × consumo_por_t = kgCO₂e/t.

        Nota: o fator de emissão é sempre buscado ao vivo no banco de fatores
        (st.session_state.fatores_emissao) para garantir que alterações nos
        fatores se reflitam imediatamente, sem necessidade de re-salvar cada
        unidade.  O valor armazenado em Consumiveis[].fator serve apenas como
        fallback quando o consumível não é encontrado na base atual.
        """
        intensidade_escopo1 = 0.0
        intensidade_escopo2 = 0.0
        intensidade_escopo3 = 0.0

        mass_unit = get_default_mass_unit_from_session(st.session_state)
        # Quantas [mass_unit] há em 1 tonelada  (ex: kg → 1 000; t → 1; kt → 0,001)
        escala_para_ton = convert_mass(1.0, "t", mass_unit)

        # ── Índice ao vivo de fatores de emissão ──────────────────────────
        fatores_db = st.session_state.get("fatores_emissao", [])
        try:
            from core.calc.fatores import FatorIndex
            _fator_idx = FatorIndex(fatores_db) if fatores_db else None
        except Exception:
            _fator_idx = None

        try:
            ano_ref = int(float(str(unidade.Periodo).strip()))
        except (ValueError, TypeError, AttributeError):
            ano_ref = None

        for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico):
            nome_consumivel = str(c.get("nome", "")).strip()
            escopo_stored   = str(c.get("escopo", "SCOPE 1"))

            # Valor de fallback: fator salvo no consumível
            fator = float(c.get("fator", 0.0))   # kgCO₂e / unid_consumível
            escopo = escopo_stored

            # Busca ao vivo: prioriza DB atual sobre valor salvo
            if _fator_idx and nome_consumivel:
                # 1) Tenta com o escopo armazenado e o ano exato
                fator_dict = _fator_idx.get_fator_dict(nome_consumivel, escopo_stored, ano=ano_ref)
                # 2) Se não encontrou, percorre todos os escopos
                if fator_dict is None:
                    for esc_try in ["1", "2", "3"]:
                        fator_dict = _fator_idx.get_fator_dict(nome_consumivel, esc_try, ano=ano_ref)
                        if fator_dict is not None:
                            break
                if fator_dict is not None:
                    fator  = float(fator_dict.get("fator_emissao", 0.0))
                    escopo = str(fator_dict.get("escopo", escopo_stored))

            consumo_por_ton = float(e) * float(escala_para_ton)  # unid_consumível / t
            emissao = fator * consumo_por_ton                     # kgCO₂e / t

            if "1" in escopo:
                intensidade_escopo1 += emissao
            elif "2" in escopo:
                intensidade_escopo2 += emissao
            elif "3" in escopo:
                intensidade_escopo3 += emissao

        unidade.IntensidadeEmissaoEscopo1 = intensidade_escopo1
        unidade.IntensidadeEmissaoEscopo2 = intensidade_escopo2
        unidade.IntensidadeEmissaoEscopo3 = intensidade_escopo3
        unidade.IntensidadeEmissao = (
            intensidade_escopo1 + intensidade_escopo2 + intensidade_escopo3
        )
        # Pegada = intensidade própria; será sobrescrito por propagar_pegada
        unidade.Pegada = unidade.IntensidadeEmissao
        unidade.PegadaEscopo1 = intensidade_escopo1
        unidade.PegadaEscopo2 = intensidade_escopo2
        unidade.PegadaEscopo3 = intensidade_escopo3
        return unidade

    # ═══════════════════════════════════════════════════════════════
    #  PROPAGAÇÃO DE PEGADA NA CADEIA
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def propagar_pegada(
        unidades: List[UnidadeProdutiva], conexoes: List[Dict]
    ) -> List[UnidadeProdutiva]:
        """Propaga a pegada acumulada (kgCO₂e/t de output) ao longo da cadeia.

        Fórmula (lifecycle product carbon footprint):
            pegada(U) = própria_intensidade(U)
                      + Σ_pais [ pegada(P) × massa(P→U) / MassaOutput(U) ]

        Dividir por MassaOutput(U), e não por MassaInput(U), garante que o
        resultado seja kgCO₂e por tonelada de PRODUTO de U (não de insumo),
        respeitando perdas de processo.
        """
        if not unidades:
            return unidades

        mapa_unidades = {u.ID_ELO: u for u in unidades}
        grafo: Dict[str, List[str]] = {u.ID_ELO: [] for u in unidades}
        grau_entrada: Dict[str, int] = {u.ID_ELO: 0 for u in unidades}

        for c in conexoes:
            src, tgt = c.get("source"), c.get("target")
            if src in grafo and tgt in grafo:
                grafo[src].append(tgt)
                grau_entrada[tgt] += 1

        # Ordenação topológica (Kahn)
        fila = [nid for nid, grau in grau_entrada.items() if grau == 0]
        ordem: List[str] = []
        while fila:
            atual = fila.pop(0)
            ordem.append(atual)
            for vizinho in grafo.get(atual, []):
                grau_entrada[vizinho] -= 1
                if grau_entrada[vizinho] == 0:
                    fila.append(vizinho)

        # Inicializar todos com intensidade própria (cobre ciclos/nós isolados)
        for u in unidades:
            u.PegadaEscopo1 = u.IntensidadeEmissaoEscopo1
            u.PegadaEscopo2 = u.IntensidadeEmissaoEscopo2
            u.PegadaEscopo3 = u.IntensidadeEmissaoEscopo3
            u.Pegada = u.IntensidadeEmissao

        for elo_id in ordem:
            unidade = mapa_unidades[elo_id]
            pais_conexoes = [
                c for c in conexoes
                if c.get("target") == elo_id and c.get("source") in mapa_unidades
            ]
            if not pais_conexoes:
                # Nó raiz: pegada = intensidade própria (já inicializado)
                continue

            # Denominador: MassaOutput de U (kgCO₂e/t de produto final)
            massa_output_u = float(unidade.MassaOutput or 0.0)
            if massa_output_u <= 0:
                # Sem output definido: usar intensidade própria, sem herança
                continue

            he1 = he2 = he3 = 0.0
            for c in pais_conexoes:
                pai = mapa_unidades[c["source"]]
                # massa transferida: usa campo "massa" do edge; fallback = MassaOutput do pai
                massa_trf = float(
                    c.get("massa") or pai.MassaOutput or 0.0
                )
                proporcao = massa_trf / massa_output_u
                he1 += pai.PegadaEscopo1 * proporcao
                he2 += pai.PegadaEscopo2 * proporcao
                he3 += pai.PegadaEscopo3 * proporcao

            unidade.PegadaEscopo1 = he1 + unidade.IntensidadeEmissaoEscopo1
            unidade.PegadaEscopo2 = he2 + unidade.IntensidadeEmissaoEscopo2
            unidade.PegadaEscopo3 = he3 + unidade.IntensidadeEmissaoEscopo3
            unidade.Pegada = (
                unidade.PegadaEscopo1
                + unidade.PegadaEscopo2
                + unidade.PegadaEscopo3
            )

        return list(mapa_unidades.values())

    # ═══════════════════════════════════════════════════════════════
    #  TOTAIS CENTRALIZADOS
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def calcular_totais(
        unidades: List[UnidadeProdutiva],
        ano: Optional[str | int] = None,
        ids_selecionados: Optional[Set[str]] = None,
    ) -> Dict:
        """Calcula totais de emissão filtrando por período e/ou seleção de nós.

        Retorna valores em unidades canônicas (internas):
          - emissões : kgCO₂e
          - massa    : toneladas
          - intensidade: kgCO₂e/t

        Args:
            unidades:         lista de UnidadeProdutiva (já propagadas)
            ano:              se fornecido, filtra por u.Periodo == str(ano)
            ids_selecionados: se fornecido e não vazio, filtra por ID_ELO

        Returns:
            dict com:
              escopo1, escopo2, escopo3, total             — emissões próprias (kgCO₂e)
              lifecycle_total                               — Pegada × MassaOutput (kgCO₂e)
              massa_total                                   — soma de MassaOutput (t)
              intensidade_media                             — kgCO₂e/t (média das unidades activas)
              n_unidades
        """
        filtradas = list(unidades)

        if ano is not None:
            ano_str = str(ano)
            filtradas = [u for u in filtradas if str(u.Periodo) == ano_str]

        if ids_selecionados:
            filtradas = [u for u in filtradas if u.ID_ELO in ids_selecionados]

        e1 = sum(
            u.IntensidadeEmissaoEscopo1 * (u.MassaOutput or 0.0) for u in filtradas
        )
        e2 = sum(
            u.IntensidadeEmissaoEscopo2 * (u.MassaOutput or 0.0) for u in filtradas
        )
        e3 = sum(
            u.IntensidadeEmissaoEscopo3 * (u.MassaOutput or 0.0) for u in filtradas
        )
        total = e1 + e2 + e3
        lifecycle = sum(
            u.Pegada * (u.MassaOutput or 0.0) for u in filtradas
        )
        massa_total = sum(u.MassaOutput or 0.0 for u in filtradas)
        ints = [u.IntensidadeEmissao for u in filtradas if u.IntensidadeEmissao > 0]
        intensidade_media = sum(ints) / len(ints) if ints else 0.0

        return {
            "escopo1": e1,
            "escopo2": e2,
            "escopo3": e3,
            "total": total,
            "lifecycle_total": lifecycle,
            "massa_total": massa_total,
            "intensidade_media": intensidade_media,
            "n_unidades": len(filtradas),
        }

    @staticmethod
    def calcular_totais_display(
        unidades: List[UnidadeProdutiva],
        mass_unit: Optional[str] = None,
        ano: Optional[str | int] = None,
        ids_selecionados: Optional[Set[str]] = None,
    ) -> Dict:
        """Como calcular_totais, mas converte para a unidade de exibição.

        Chama calcular_totais internamente e aplica convert_co2e / convert_mass
        aos resultados, devolvendo também rótulos prontos para UI.

        Returns:
            dict igual a calcular_totais com valores convertidos, mais:
              co2e_lbl  — ex. "tCO₂e", "kgCO₂e", "MtCO₂e"
              int_lbl   — ex. "tCO₂e/t", "kgCO₂e/kg"
              mass_unit — chave normalizada da unidade (ex. "t", "kg")
        """
        raw = EmissionCalculator.calcular_totais(
            unidades, ano=ano, ids_selecionados=ids_selecionados
        )
        mu = normalize_unit(mass_unit or "t")

        return {
            "escopo1":          convert_co2e(raw["escopo1"], mu),
            "escopo2":          convert_co2e(raw["escopo2"], mu),
            "escopo3":          convert_co2e(raw["escopo3"], mu),
            "total":            convert_co2e(raw["total"], mu),
            "lifecycle_total":  convert_co2e(raw["lifecycle_total"], mu),
            "massa_total":      convert_mass(raw["massa_total"], "t", mu),
            "intensidade_media":convert_co2e(raw["intensidade_media"], mu),
            "n_unidades":       raw["n_unidades"],
            # rótulos prontos para UI
            "co2e_lbl":  co2e_label(mu),
            "int_lbl":   co2e_intensity_label(mu),
            "mass_unit": mu,
        }

    # ═══════════════════════════════════════════════════════════════
    #  HELPERS LEGADOS (mantidos por compatibilidade)
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def calcular_pegada_total(unidades: List[UnidadeProdutiva]) -> float:
        """Pegada acumulada total em kgCO₂e (Pegada [kgCO₂e/t] × MassaOutput [t])."""
        return sum(
            u.Pegada * (u.MassaOutput or 0.0) for u in unidades
        )

    @staticmethod
    def calcular_emissoes_por_localizacao(unidades: List[UnidadeProdutiva]) -> Dict:
        """Emissões próprias totais (kgCO₂e) agrupadas por localização."""
        emissoes: Dict[str, float] = {}
        for u in unidades:
            loc = u.Localizacao or "Sem local"
            emissoes[loc] = (
                emissoes.get(loc, 0.0)
                + u.IntensidadeEmissao * (u.MassaOutput or 0.0)
            )
        return emissoes

    @staticmethod
    def gerar_dados_grafico(unidades: List[UnidadeProdutiva]) -> Dict:
        return {
            "labels":   [u.ID_ELO for u in unidades],
            "emissoes": [
                u.IntensidadeEmissao * (u.MassaOutput or 0.0) for u in unidades
            ],
        }

    @staticmethod
    def determinar_ordem_fluxo(unidades, conexoes):
        """Ordenação topológica das unidades segundo o grafo de fluxo."""
        grafo = {u.ID_ELO: [] for u in unidades}
        grau_entrada = {u.ID_ELO: 0 for u in unidades}
        for conexao in conexoes:
            grafo[conexao["source"]].append(conexao["target"])
            grau_entrada[conexao["target"]] += 1
        fila = [n for n in grafo if grau_entrada[n] == 0]
        ordem = []
        while fila:
            node = fila.pop(0)
            ordem.append(node)
            for viz in grafo[node]:
                grau_entrada[viz] -= 1
                if grau_entrada[viz] == 0:
                    fila.append(viz)
        return ordem