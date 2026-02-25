from typing import List, Dict
from database import UnidadeProdutiva
import streamlit as st
from core.units import convert_mass, get_default_mass_unit_from_session

class EmissionCalculator:
    @staticmethod
    def calcular_emissoes(unidade: UnidadeProdutiva) -> UnidadeProdutiva:
        """Calcula a intensidade de emissão (tCO₂/t) por escopo e total da unidade"""
        intensidade_escopo1 = 0.0
        intensidade_escopo2 = 0.0
        intensidade_escopo3 = 0.0
        mass_unit = get_default_mass_unit_from_session(st.session_state)
        escala_para_ton = convert_mass(1.0, "t", mass_unit)
        
        for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico):
            fator = c.get("fator", 0.0)
            escopo = str(c.get("escopo", "1")).upper()
            consumo_por_ton = float(e) * float(escala_para_ton)
            emissao = fator * consumo_por_ton
            
            # Aceita tanto "1", "SCOPE 1", "SCOPE1" etc
            if "1" in escopo:
                intensidade_escopo1 += emissao
            elif "2" in escopo:
                intensidade_escopo2 += emissao
            elif "3" in escopo:
                intensidade_escopo3 += emissao
        
        unidade.IntensidadeEmissaoEscopo1 = intensidade_escopo1
        unidade.IntensidadeEmissaoEscopo2 = intensidade_escopo2
        unidade.IntensidadeEmissaoEscopo3 = intensidade_escopo3
        unidade.IntensidadeEmissao = intensidade_escopo1 + intensidade_escopo2 + intensidade_escopo3
        unidade.Pegada = unidade.IntensidadeEmissao * unidade.MassaOutput if unidade.MassaOutput else 0.0
        return unidade
    
    @staticmethod
    def propagar_pegada(unidades: List[UnidadeProdutiva], conexoes: List[Dict]) -> List[UnidadeProdutiva]:
        """
        Propaga a pegada acumulada (tCO₂/t) ao longo da cadeia,
        ponderando pela massa transferida em cada conexão.
        """
        mapa_unidades = {u.ID_ELO: u for u in unidades}
        grafo = {u.ID_ELO: [] for u in unidades}
        grau_entrada = {u.ID_ELO: 0 for u in unidades}

        for c in conexoes:
            grafo[c["source"]].append(c["target"])
            grau_entrada[c["target"]] += 1

        # Ordenação topológica
        fila = [node for node in grau_entrada if grau_entrada[node] == 0]
        ordem = []

        while fila:
            atual = fila.pop(0)
            ordem.append(atual)
            for vizinho in grafo[atual]:
                grau_entrada[vizinho] -= 1
                if grau_entrada[vizinho] == 0:
                    fila.append(vizinho)

        # Propagação da pegada
        for elo_id in ordem:
            unidade = mapa_unidades[elo_id]
            pais_conexoes = [c for c in conexoes if c["target"] == elo_id]

            if not pais_conexoes:
                # Unidade inicial: pegada = intensidade própria
                unidade.PegadaEscopo1 = unidade.IntensidadeEmissaoEscopo1
                unidade.PegadaEscopo2 = unidade.IntensidadeEmissaoEscopo2
                unidade.PegadaEscopo3 = unidade.IntensidadeEmissaoEscopo3
                unidade.Pegada = unidade.IntensidadeEmissao
                continue

            # Propagar pegada por escopo
            pegada_herdada_escopo1 = 0.0
            pegada_herdada_escopo2 = 0.0
            pegada_herdada_escopo3 = 0.0
            
            for c in pais_conexoes:
                pai = mapa_unidades[c["source"]]
                massa_contribuida = c.get("massa", pai.MassaOutput)
                proporcao = massa_contribuida / unidade.MassaInput
                pegada_herdada_escopo1 += pai.PegadaEscopo1 * proporcao
                pegada_herdada_escopo2 += pai.PegadaEscopo2 * proporcao
                pegada_herdada_escopo3 += pai.PegadaEscopo3 * proporcao

            unidade.PegadaEscopo1 = pegada_herdada_escopo1 + unidade.IntensidadeEmissaoEscopo1
            unidade.PegadaEscopo2 = pegada_herdada_escopo2 + unidade.IntensidadeEmissaoEscopo2
            unidade.PegadaEscopo3 = pegada_herdada_escopo3 + unidade.IntensidadeEmissaoEscopo3
            unidade.Pegada = unidade.PegadaEscopo1 + unidade.PegadaEscopo2 + unidade.PegadaEscopo3

        return list(mapa_unidades.values())

    @staticmethod
    def calcular_pegada_total(unidades: List[UnidadeProdutiva]) -> float:
        return sum(u.Pegada for u in unidades)
    
    @staticmethod
    def calcular_emissoes_por_localizacao(unidades: List[UnidadeProdutiva]) -> Dict:
        emissoes = {}
        for u in unidades:
            if u.Localizacao not in emissoes:
                emissoes[u.Localizacao] = 0
            emissoes[u.Localizacao] += u.IntensidadeEmissao * u.MassaOutput
        return emissoes
    
    @staticmethod
    def gerar_dados_grafico(unidades: List[UnidadeProdutiva]) -> Dict:
        # Pode ser implementado para gráficos futuros
        return {
            "labels": [u.ID_ELO for u in unidades],
            "emissoes": [u.IntensidadeEmissao * u.MassaOutput for u in unidades]
        }

    @staticmethod
    def determinar_ordem_fluxo(unidades, conexoes):
        """Analisa as conexões para determinar a ordem correta do fluxo"""
        grafo = {u.ID_ELO: [] for u in unidades}
        grau_entrada = {u.ID_ELO: 0 for u in unidades}
        
        # Construir grafo e calcular graus de entrada
        for conexao in conexoes:
            grafo[conexao['source']].append(conexao['target'])
            grau_entrada[conexao['target']] += 1
        
        # Ordenação topológica (Kahn's algorithm)
        fila = [node for node in grafo if grau_entrada[node] == 0]
        ordem = []
        
        while fila:
            node = fila.pop(0)
            ordem.append(node)
            for vizinho in grafo[node]:
                grau_entrada[vizinho] -= 1
                if grau_entrada[vizinho] == 0:
                    fila.append(vizinho)
        
        return ordem