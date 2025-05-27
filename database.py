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
                input_insumo: str, massa_input: float,
                output_insumo: str, massa_output: float,
                consumiveis: list[dict], consumo_especifico: list[float],
                taxacao_fronteira: bool = False, taxacao_local: bool = False):
        
        self.ID_ELO = id_elo
        self.Nome = nome
        self.Localizacao = localizacao
        self.Periodo = periodo

        self.Input = input_insumo
        self.MassaInput = massa_input
        self.Output = output_insumo
        self.MassaOutput = massa_output

        self.Consumiveis = consumiveis
        self.ConsumoEspecifico = consumo_especifico

        # Valores calculados (inicialmente zerados)
        self.IntensidadeEmissaoEscopo1 = 0.0
        self.IntensidadeEmissaoEscopo2 = 0.0
        self.IntensidadeEmissaoEscopo3 = 0.0
        self.IntensidadeEmissao = 0.0

        self.PegadaEscopo1 = 0.0
        self.PegadaEscopo2 = 0.0
        self.PegadaEscopo3 = 0.0
        self.Pegada = 0.0

        self.TaxacaoFronteira = taxacao_fronteira
        self.TaxacaoLocal = taxacao_local

    def to_dict(self):
        return {
            "ID_ELO": self.ID_ELO,
            "Nome": self.Nome,
            "Localizacao": self.Localizacao,
            "Periodo": self.Periodo,
            "Input": self.Input,
            "MassaInput": self.MassaInput,
            "Output": self.Output,
            "MassaOutput": self.MassaOutput,
            "Consumiveis": self.Consumiveis,
            "ConsumoEspecifico": self.ConsumoEspecifico,
            "IntensidadeEmissao": self.IntensidadeEmissao,
            "IntensidadeEmissaoEscopo1": self.IntensidadeEmissaoEscopo1,
            "IntensidadeEmissaoEscopo2": self.IntensidadeEmissaoEscopo2,
            "IntensidadeEmissaoEscopo3": self.IntensidadeEmissaoEscopo3,
            "Pegada": self.Pegada,
            "PegadaEscopo1": self.PegadaEscopo1,
            "PegadaEscopo2": self.PegadaEscopo2,
            "PegadaEscopo3": self.PegadaEscopo3,
            "TaxacaoFronteira": self.TaxacaoFronteira,
            "TaxacaoLocal": self.TaxacaoLocal,
            "ConfigOperacional": getattr(self, "ConfigOperacional", "Padrão")
        }

from typing import List, Dict
import streamlit as st
import pandas as pd
import json
from database import UnidadeProdutiva, Conexao
from calculations import EmissionCalculator

class DatabaseManager:
    def __init__(self):
        self._init_session_data()
    
    def _init_session_data(self):
        if "unidades" not in st.session_state:
            st.session_state.unidades = []
        if "conexoes" not in st.session_state:
            st.session_state.conexoes = []

    # --- Unidades ---
    def add_unidade(self, unidade: UnidadeProdutiva) -> None:
        if not any(u.ID_ELO == unidade.ID_ELO for u in st.session_state.unidades):
            st.session_state.unidades.append(unidade)
    
    def remove_unidade(self, id_elo: str) -> None:
        st.session_state.unidades = [u for u in st.session_state.unidades if u.ID_ELO != id_elo]
        self._remove_connections_with_node(id_elo)
    
    def get_unidades(self) -> List[UnidadeProdutiva]:
        return st.session_state.unidades
    
    def get_unidade_by_id(self, id_elo: str) -> UnidadeProdutiva:
        return next((u for u in st.session_state.unidades if u.ID_ELO == id_elo), None)

    # --- Conexões ---
    def add_edge(self, origem: str, destino: str) -> None:
        if not any(c.origem == origem and c.destino == destino for c in st.session_state.conexoes):
            st.session_state.conexoes.append(Conexao(origem=origem, destino=destino))
    
    def remove_edge(self, origem: str, destino: str) -> None:
        st.session_state.conexoes = [
            c for c in st.session_state.conexoes if not (c.origem == origem and c.destino == destino)
        ]
    
    def get_conexoes(self) -> List[Conexao]:
        return st.session_state.conexoes
    
    def _remove_connections_with_node(self, node_id: str) -> None:
        st.session_state.conexoes = [
            c for c in st.session_state.conexoes if c.origem != node_id and c.destino != node_id
        ]

    # --- Visualização ---
    def get_unidades_df(self) -> pd.DataFrame:
        dados = []
        for unidade in st.session_state.unidades:
            dados.append({
                "ID ELO": unidade.ID_ELO,
                "Nome": unidade.Nome,
                "Localização": unidade.Localizacao,
                "Período": unidade.Periodo,
                "Input": unidade.Input,
                "Output": unidade.Output,
                "Emissão (CO₂)": f"{unidade.IntensidadeEmissao * unidade.MassaOutput:,.2f}",
                "Intensidade (tCO₂/t)": f"{unidade.IntensidadeEmissao:.2f}",
                "Pegada (CO₂/t produto)": f"{unidade.Pegada:.2f}",
                "Tax. Fronteira": "✅" if unidade.TaxacaoFronteira else "❌",
                "Tax. Local": "✅" if unidade.TaxacaoLocal else "❌"
            })
        return pd.DataFrame(dados)
    
    def get_estatisticas(self) -> Dict:
        return {
            "total_unidades": len(st.session_state.unidades),
            "total_conexoes": len(st.session_state.conexoes),
            "emissao_total": sum(u.IntensidadeEmissao * u.MassaOutput for u in st.session_state.unidades)
        }

    # --- Importação / Exportação ---
    def export_to_json(self) -> str:
        data = {
            "unidades": [u.to_dict() for u in st.session_state.unidades],
            "conexoes": [c.to_dict() for c in st.session_state.conexoes]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def import_from_json(self, json_str: str) -> bool:
        try:
            data = json.loads(json_str)
            st.session_state.unidades = []
            st.session_state.conexoes = []

            for u_data in data.get("unidades", []):
                unidade = UnidadeProdutiva(
                    id_elo=u_data["ID_ELO"],
                    nome=u_data["Nome"],
                    localizacao=u_data["Localizacao"],
                    periodo=u_data["Periodo"],
                    input_insumo=u_data["Input"],
                    massa_input=u_data.get("MassaInput", 0.0),
                    output_insumo=u_data["Output"],
                    massa_output=u_data.get("MassaOutput", 0.0),
                    consumiveis=u_data.get("Consumiveis", []),
                    consumo_especifico=u_data.get("ConsumoEspecifico", []),
                    taxacao_fronteira=u_data.get("TaxacaoFronteira", False),
                    taxacao_local=u_data.get("TaxacaoLocal", False)
                )

                # Restaurar atributos calculados, se existirem
                unidade.IntensidadeEmissao = u_data.get("IntensidadeEmissao", 0.0)
                unidade.Pegada = u_data.get("Pegada", 0.0)
                unidade.IntensidadeEmissaoEscopo1 = u_data.get("IntensidadeEmissaoEscopo1", 0.0)
                unidade.IntensidadeEmissaoEscopo2 = u_data.get("IntensidadeEmissaoEscopo2", 0.0)
                unidade.IntensidadeEmissaoEscopo3 = u_data.get("IntensidadeEmissaoEscopo3", 0.0)
                unidade.PegadaEscopo1 = u_data.get("PegadaEscopo1", 0.0)
                unidade.PegadaEscopo2 = u_data.get("PegadaEscopo2", 0.0)
                unidade.PegadaEscopo3 = u_data.get("PegadaEscopo3", 0.0)

                st.session_state.unidades.append(unidade)

            for c_data in data.get("conexoes", []):
                self.add_edge(c_data["origem"], c_data["destino"])

            # Propagar a pegada após importar
            self.propagar_pegada()

            return True
        except Exception as e:
            st.error(f"Erro ao importar dados: {str(e)}")
            return False

    def get_edges_for_graph(self) -> List[Dict]:
        return [{"source": c.origem, "target": c.destino} for c in st.session_state.conexoes]

    # --- Atualização de Pegadas ---
    def propagar_pegada(self):
        """Atualiza a pegada de todas as unidades com base nas conexões"""
        EmissionCalculator.propagar_pegada(
            st.session_state.unidades,
            self.get_edges_for_graph()
        )
