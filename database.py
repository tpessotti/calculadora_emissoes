import streamlit as st
import json
from typing import List, Dict
import pandas as pd
from dataclasses import dataclass, asdict

@dataclass
class Conexao:
    """Classe que representa uma conexão entre unidades produtivas"""
    origem: str
    destino: str
    label: str = "Fluxo"

    def to_dict(self):
        return asdict(self)

class UnidadeProdutiva:
    def __init__(self, id_elo: str, nome: str, localizacao: str, periodo: str, 
                 input_insumo: str, output_insumo: str, emissao: float, pegada: float,
                 taxacao_fronteira: bool = False, taxacao_local: bool = False):
        self.ID_ELO = id_elo
        self.Nome = nome
        self.Localizacao = localizacao
        self.Periodo = periodo
        self.Input = input_insumo
        self.Output = output_insumo
        self.Emissao = emissao
        self.Pegada = pegada
        self.TaxacaoFronteira = taxacao_fronteira
        self.TaxacaoLocal = taxacao_local

    def to_dict(self):
        return {
            "ID_ELO": self.ID_ELO,
            "Nome": self.Nome,
            "Localizacao": self.Localizacao,
            "Periodo": self.Periodo,
            "Input": self.Input,
            "Output": self.Output,
            "Emissao": self.Emissao,
            "Pegada": self.Pegada,
            "TaxacaoFronteira": self.TaxacaoFronteira,
            "TaxacaoLocal": self.TaxacaoLocal
        }

class DatabaseManager:
    def __init__(self):
        self._init_session_data()
    
    def _init_session_data(self):
        """Inicializa os dados na session state se não existirem"""
        if "unidades" not in st.session_state:
            st.session_state.unidades = []
        if "conexoes" not in st.session_state:
            st.session_state.conexoes = []
    
    # Métodos para unidades produtivas
    def add_unidade(self, unidade: UnidadeProdutiva) -> None:
        """Adiciona uma nova unidade produtiva"""
        if not any(u.ID_ELO == unidade.ID_ELO for u in st.session_state.unidades):
            st.session_state.unidades.append(unidade)
    
    def remove_unidade(self, id_elo: str) -> None:
        """Remove uma unidade e suas conexões relacionadas"""
        st.session_state.unidades = [u for u in st.session_state.unidades if u.ID_ELO != id_elo]
        self._remove_connections_with_node(id_elo)
    
    def get_unidades(self) -> List[UnidadeProdutiva]:
        """Retorna todas as unidades produtivas"""
        return st.session_state.unidades
    
    def get_unidade_by_id(self, id_elo: str) -> UnidadeProdutiva:
        """Obtém uma unidade pelo ID"""
        for u in st.session_state.unidades:
            if u.ID_ELO == id_elo:
                return u
        return None

    # Métodos para conexões
    def add_edge(self, origem: str, destino: str) -> None:
        """Adiciona uma nova conexão entre unidades"""
        if not any(c.origem == origem and c.destino == destino for c in st.session_state.conexoes):
            st.session_state.conexoes.append(Conexao(origem=origem, destino=destino))
    
    def remove_edge(self, origem: str, destino: str) -> None:
        """Remove uma conexão específica"""
        st.session_state.conexoes = [
            c for c in st.session_state.conexoes 
            if not (c.origem == origem and c.destino == destino)
        ]
    
    def get_conexoes(self) -> List[Conexao]:
        """Retorna todas as conexões"""
        return st.session_state.conexoes
    
    def _remove_connections_with_node(self, node_id: str) -> None:
        """Remove todas as conexões relacionadas a um nó"""
        st.session_state.conexoes = [
            c for c in st.session_state.conexoes 
            if c.origem != node_id and c.destino != node_id
        ]

    # Métodos para visualização de dados
    def get_unidades_df(self) -> pd.DataFrame:
        """Retorna um DataFrame com todas as unidades"""
        dados = []
        for unidade in st.session_state.unidades:
            dados.append({
                "ID ELO": unidade.ID_ELO,
                "Nome": unidade.Nome,
                "Localização": unidade.Localizacao,
                "Período": unidade.Periodo,
                "Input": unidade.Input,
                "Output": unidade.Output,
                "Emissão (CO₂)": f"{unidade.Emissao:,.2f}",
                "Pegada": unidade.Pegada,
                "Tax. Fronteira": "✅" if unidade.TaxacaoFronteira else "❌",
                "Tax. Local": "✅" if unidade.TaxacaoLocal else "❌"
            })
        return pd.DataFrame(dados)
    
    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas gerais"""
        return {
            "total_unidades": len(st.session_state.unidades),
            "total_conexoes": len(st.session_state.conexoes),
            "emissao_total": sum(u.Emissao for u in st.session_state.unidades)
        }

    # Métodos para importação/exportação
    def export_to_json(self) -> str:
        """Exporta todos os dados para JSON"""
        data = {
            "unidades": [u.to_dict() for u in st.session_state.unidades],
            "conexoes": [c.to_dict() for c in st.session_state.conexoes]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def import_from_json(self, json_str: str) -> bool:
        """Importa dados de um JSON"""
        try:
            data = json.loads(json_str)
            
            # Limpa dados existentes
            st.session_state.unidades = []
            st.session_state.conexoes = []
            
            # Importa unidades
            for u_data in data.get("unidades", []):
                unidade = UnidadeProdutiva(
                    id_elo=u_data["ID_ELO"],
                    nome=u_data["Nome"],
                    localizacao=u_data["Localizacao"],
                    periodo=u_data["Periodo"],
                    input_insumo=u_data["Input"],
                    output_insumo=u_data["Output"],
                    emissao=u_data["Emissao"],
                    pegada=u_data["Pegada"],
                    taxacao_fronteira=u_data.get("TaxacaoFronteira", False),
                    taxacao_local=u_data.get("TaxacaoLocal", False)
                )
                self.add_unidade(unidade)
            
            # Importa conexões
            for c_data in data.get("conexoes", []):
                self.add_edge(c_data["origem"], c_data["destino"])
            
            return True
        except Exception as e:
            st.error(f"Erro ao importar dados: {str(e)}")
            return False
    
    def get_edges_for_graph(self) -> List[Dict]:
        """Retorna conexões no formato esperado pelo gráfico"""
        return [{"source": c.origem, "target": c.destino} for c in st.session_state.conexoes]