import streamlit as st
import json
from typing import List, Dict
import pandas as pd

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

class DatabaseManager:
    def __init__(self):
        if "unidades" not in st.session_state:
            st.session_state.unidades = []
        if "edges" not in st.session_state:
            st.session_state.edges = []
    
    def add_unidade(self, unidade: UnidadeProdutiva):
        st.session_state.unidades.append(unidade)
    
    def remove_unidade(self, id_elo: str):
        st.session_state.unidades = [u for u in st.session_state.unidades if u.ID_ELO != id_elo]
        st.session_state.edges = [e for e in st.session_state.edges 
                                if e['source'] != id_elo and e['target'] != id_elo]
    
    def add_edge(self, source: str, target: str):
        st.session_state.edges.append({"source": source, "target": target, "label": "Fluxo"})
    
    def remove_edge(self, source, target):
        """Remove uma conexão entre unidades"""
        self.edges = [e for e in self.edges 
                    if not (e['source'] == source and e['target'] == target)]
        self.save_data()
        if 'edges' in st.session_state:
            st.session_state.edges = self.edges
    
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
                "Emissão (CO₂)": f"{unidade.Emissao:,.2f}",
                "Pegada": unidade.Pegada,
                "Tax. Fronteira": "✅" if unidade.TaxacaoFronteira else "❌",
                "Tax. Local": "✅" if unidade.TaxacaoLocal else "❌"
            })
        return pd.DataFrame(dados)
    
    def get_estatisticas(self) -> Dict:
        return {
            "total_unidades": len(st.session_state.unidades),
            "total_conexoes": len(st.session_state.edges),
            "emissao_total": sum(u.Emissao for u in st.session_state.unidades)
        }
        
    def export_to_json(self) -> str:
        """Exporta todos os dados para JSON"""
        data = {
            "unidades": [vars(u) for u in st.session_state.unidades],
            "edges": st.session_state.edges
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def import_from_json(self, json_str: str) -> bool:
        """Importa dados de JSON"""
        try:
            data = json.loads(json_str)
            
            # Limpa dados existentes
            st.session_state.unidades = []
            st.session_state.edges = []
            
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
            for edge in data.get("edges", []):
                self.add_edge(edge["source"], edge["target"])
            
            return True
        except Exception as e:
            st.error(f"Erro ao importar dados: {str(e)}")
            return False