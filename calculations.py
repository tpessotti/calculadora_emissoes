from typing import List, Dict
from database import UnidadeProdutiva
import streamlit as st

class EmissionCalculator:
    @staticmethod
    def calcular_emissoes(unidade: UnidadeProdutiva) -> UnidadeProdutiva:
        """Calcula a intensidade de emissão (tCO₂/t) e pegada total da unidade"""
        intensidade = 0.0
        for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico):
            fator = c.get("fator", 0.0)
            intensidade += fator * e
        
        unidade.IntensidadeEmissao = intensidade
        unidade.Pegada = intensidade * unidade.MassaOutput if unidade.MassaOutput else 0.0
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
                unidade.Pegada = unidade.IntensidadeEmissao
                continue

            # Validação da consistência
            massa_total = sum(c.get("massa", mapa_unidades[c["source"]].MassaOutput) for c in pais_conexoes)
            if abs(massa_total - unidade.MassaInput) > 0.01:
                st.warning(
                    f"[Inconsistência de Massa] A soma das massas conectadas ao elo '{elo_id}' "
                    f"({massa_total:.2f}) é diferente da MassaInput ({unidade.MassaInput:.2f}). Pegada não atualizada."
                )
                unidade.Pegada = float("nan")
                continue

            pegada_herdada = 0.0
            for c in pais_conexoes:
                pai = mapa_unidades[c["source"]]
                massa_contribuida = c.get("massa", pai.MassaOutput)
                proporcao = massa_contribuida / unidade.MassaInput
                pegada_herdada += pai.Pegada * proporcao

            unidade.Pegada = pegada_herdada + unidade.IntensidadeEmissao

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
            emissoes[u.Localizacao] += u.Emissao
        return emissoes
    
    @staticmethod
    def calcular_emissoes(unidade: UnidadeProdutiva) -> UnidadeProdutiva:
        total = 0.0
        for c, e in zip(unidade.Consumiveis, unidade.ConsumoEspecifico):
            total += c.get("fator", 0) * e
        unidade.IntensidadeEmissao = total
        unidade.Pegada = total * unidade.MassaOutput if unidade.MassaOutput else 0
        return unidade
    
    @staticmethod
    def gerar_dados_grafico(unidades: List[UnidadeProdutiva]) -> Dict:
        # Pode ser implementado para gráficos futuros
        return {
            "labels": [u.ID_ELO for u in unidades],
            "emissoes": [u.Emissao for u in unidades]
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