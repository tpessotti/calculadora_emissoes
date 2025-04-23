from typing import List, Dict
from database import UnidadeProdutiva

class EmissionCalculator:
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