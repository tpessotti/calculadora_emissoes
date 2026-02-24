import streamlit as st
import json
import re
from typing import List, Dict
import pandas as pd
#from database import Tecnologia
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any

@dataclass
class Conexao:
    """Classe que representa uma conexão entre unidades produtivas"""
    origem: str
    destino: str
    id: str = ""
    massa: float = 0.0  # Massa transferida na conexão
    label: str = "Fluxo"
    periodo: str = ""   # Período/ano da conexão

    def to_dict(self):
        return asdict(self)

@dataclass
class Tecnologia:
    """Classe que representa uma tecnologia alternativa"""
    id: str
    nome: str
    insumos: List[Dict[str, float]]  # [{"nome": str, "fator_consumo": float}]
    unidades: List[Dict[str, Any]] = field(default_factory=list)
    # [{"unidade": str, "limite_inferior": float, "limite_superior": float}]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "insumos": self.insumos,
            "unidades": self.unidades
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Tecnologia":
        return Tecnologia(
            id=data.get("id", ""),
            nome=data.get("nome", ""),
            insumos=data.get("insumos", []),
            unidades=data.get("unidades", [])
        )

class UnidadeProdutiva:
    def __init__(self, id_elo: str, nome: str, localizacao: str, periodo: str, 
                input_insumo: str, massa_input: float,
                output_insumo: str, massa_output: float,
                consumiveis: list[dict], consumo_especifico: list[float],
                taxacao_fronteira: bool = False, taxacao_local: bool = False,
                tecnologia=None, conexao: 'Conexao' = None):  # novo parâmetro
        
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

        self.TaxacaoFronteira = taxacao_fronteira
        self.TaxacaoLocal = taxacao_local

        # Valores calculados
        self.IntensidadeEmissaoEscopo1 = 0.0
        self.IntensidadeEmissaoEscopo2 = 0.0
        self.IntensidadeEmissaoEscopo3 = 0.0
        self.IntensidadeEmissao = 0.0

        self.PegadaEscopo1 = 0.0
        self.PegadaEscopo2 = 0.0
        self.PegadaEscopo3 = 0.0
        self.Pegada = 0.0

        # Propriedades adicionais
        self.Tecnologia = tecnologia
        self.Conexao = conexao  # Instância de Conexao que sai desta unidade

    def to_dict(self):
        # Converter Tecnologia para ID se for um objeto
        tecnologia_valor = None
        if self.Tecnologia:
            if isinstance(self.Tecnologia, Tecnologia):
                tecnologia_valor = self.Tecnologia.id
            else:
                tecnologia_valor = self.Tecnologia
        
        # Converter Conexao para dict se existir
        conexao_valor = None
        if hasattr(self, 'Conexao') and self.Conexao:
            if isinstance(self.Conexao, Conexao):
                conexao_valor = self.Conexao.to_dict()
            else:
                conexao_valor = self.Conexao
        
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
            "Tecnologia": tecnologia_valor,
            "ConfigOperacional": getattr(self, "ConfigOperacional", "Padrão"),
            "Conexao": conexao_valor
        }


class DatabaseManager:
    def __init__(self):
        self._init_session_data()
    
    def _init_session_data(self):
        if "unidades" not in st.session_state:
            st.session_state.unidades = []
        if "conexoes" not in st.session_state:
            st.session_state.conexoes = []

    @staticmethod
    def _next_sequential_id(prefix: str, existing_ids: List[str], width: int = 3) -> str:
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
        used = set()
        max_num = -1

        for raw in existing_ids:
            sid = str(raw or "").strip()
            if not sid:
                continue
            used.add(sid.upper())
            match = pattern.match(sid)
            if not match:
                continue
            try:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue

        next_num = max_num + 1
        candidate = f"{prefix}{next_num:0{width}d}"
        while candidate.upper() in used:
            next_num += 1
            candidate = f"{prefix}{next_num:0{width}d}"
        return candidate

    def next_unidade_id(self) -> str:
        ids = [getattr(u, "ID_ELO", "") for u in st.session_state.get("unidades", [])]
        return self._next_sequential_id("E", ids)

    def next_tecnologia_id(self) -> str:
        ids = []
        for t in st.session_state.get("tecnologias_alternativas", []):
            if hasattr(t, "id"):
                ids.append(getattr(t, "id", ""))
            elif isinstance(t, dict):
                ids.append(t.get("id", ""))
        return self._next_sequential_id("T", ids)

    def next_fluxo_id(self) -> str:
        ids = []
        for c in st.session_state.get("conexoes", []):
            if hasattr(c, "id"):
                ids.append(getattr(c, "id", ""))
            elif isinstance(c, dict):
                ids.append(c.get("id", ""))
        return self._next_sequential_id("F", ids)

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
    def add_edge(self, origem: str, destino: str, massa: float = 0.0, periodo: str = "", label: str = "Fluxo", id_fluxo: str = "") -> Conexao | None:
        if not any(c.origem == origem and c.destino == destino and c.periodo == periodo for c in st.session_state.conexoes):
            fluxo_id = str(id_fluxo or "").strip() or self.next_fluxo_id()
            conexao = Conexao(id=fluxo_id, origem=origem, destino=destino, massa=massa, label=label, periodo=periodo)
            st.session_state.conexoes.append(conexao)
            return conexao
        return None
    
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
                "Int. Escopo 1": f"{unidade.IntensidadeEmissaoEscopo1:.2f}",
                "Int. Escopo 2": f"{unidade.IntensidadeEmissaoEscopo2:.2f}",
                "Int. Escopo 3": f"{unidade.IntensidadeEmissaoEscopo3:.2f}",
                "Pegada (CO₂/t produto)": f"{unidade.Pegada:.2f}",
                "Pegada Escopo 1": f"{unidade.PegadaEscopo1:.2f}",
                "Pegada Escopo 2": f"{unidade.PegadaEscopo2:.2f}",
                "Pegada Escopo 3": f"{unidade.PegadaEscopo3:.2f}",
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

    def export_to_json(self):
        data = {
            "unidades": [u.to_dict() if hasattr(u, "to_dict") else vars(u) for u in st.session_state.unidades],
            "conexoes": [c.to_dict() if hasattr(c, "to_dict") else vars(c) for c in st.session_state.get("conexoes", [])],
            "tecnologias_alternativas": [
                t.to_dict() if hasattr(t, "to_dict") else t
                for t in st.session_state.get("tecnologias_alternativas", [])
            ]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def import_from_json(self, json_str: str) -> bool:
        from calculations import EmissionCalculator
        try:
            data = json.loads(json_str)
            
            # Primeiro, processar tecnologias
            fatores_emissao = st.session_state.get("fatores_emissao", [])
            insumos_disponiveis = {f["consumivel"] for f in fatores_emissao}
            insumos_faltando = set()

            tecnologias_raw = data.get("tecnologias_alternativas")
            if tecnologias_raw is None:
                tecnologias_raw = data.get("tecnologias", [])
            tecnologias_obj = []
            tecnologias_map = {}  # Mapa ID -> objeto Tecnologia

            for t in tecnologias_raw:
                tec_id = str(t.get("id", "")).strip()
                tec_nome = str(t.get("nome", "")).strip()
                if not tec_id or not tec_nome:
                    continue

                insumos = []
                for i in t.get("insumos", []):
                    nome = i.get("nome")
                    if not nome:
                        continue
                    if nome not in insumos_disponiveis:
                        insumos_faltando.add(nome)
                        insumos.append({"nome": nome, "fator_consumo": 0.0})
                    else:
                        insumos.append({
                            "nome": nome,
                            "fator_consumo": i.get("fator_consumo", 1.0),
                        })
                
                tecnologia = Tecnologia(
                    id=tec_id,
                    nome=tec_nome,
                    insumos=insumos,
                    unidades=t.get("unidades", [])
                )
                tecnologias_obj.append(tecnologia)
                tecnologias_map[tec_id] = tecnologia

            st.session_state.tecnologias_alternativas = tecnologias_obj

            if insumos_faltando:
                st.warning(
                    f"Insumos usados em tecnologias sem fator de emissão registrado: {', '.join(sorted(insumos_faltando))}. "
                    f"O fator foi considerado como 0.0 para evitar erros."
                )
            
            # Agora processar unidades
            st.session_state.unidades = []
            st.session_state.conexoes = []

            for u_data in data.get("unidades", []):
                # Buscar tecnologia se existir
                tecnologia_id = u_data.get("Tecnologia")
                tecnologia = tecnologias_map.get(tecnologia_id) if tecnologia_id else None
                
                # Reconstruir conexão se existir
                conexao = None
                conexao_data = u_data.get("Conexao")
                if conexao_data:
                    conexao = Conexao(
                        id=conexao_data.get("id", ""),
                        origem=conexao_data.get("origem"),
                        destino=conexao_data.get("destino"),
                        massa=conexao_data.get("massa", 0.0),
                        label=conexao_data.get("label", "Fluxo"),
                        periodo=conexao_data.get("periodo", ""),
                    )
                
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
                    taxacao_local=u_data.get("TaxacaoLocal", False),
                    tecnologia=tecnologia,
                    conexao=conexao
                )

                # Calcular emissões da unidade
                EmissionCalculator.calcular_emissoes(unidade)

                # Restaurar atributos calculados, se existirem (sobrescreve o cálculo acima se houver valores salvos)
                if "IntensidadeEmissao" in u_data:
                    unidade.IntensidadeEmissao = u_data.get("IntensidadeEmissao", 0.0)
                if "Pegada" in u_data:
                    unidade.Pegada = u_data.get("Pegada", 0.0)
                if "IntensidadeEmissaoEscopo1" in u_data:
                    unidade.IntensidadeEmissaoEscopo1 = u_data.get("IntensidadeEmissaoEscopo1", 0.0)
                if "IntensidadeEmissaoEscopo2" in u_data:
                    unidade.IntensidadeEmissaoEscopo2 = u_data.get("IntensidadeEmissaoEscopo2", 0.0)
                if "IntensidadeEmissaoEscopo3" in u_data:
                    unidade.IntensidadeEmissaoEscopo3 = u_data.get("IntensidadeEmissaoEscopo3", 0.0)
                if "PegadaEscopo1" in u_data:
                    unidade.PegadaEscopo1 = u_data.get("PegadaEscopo1", 0.0)
                if "PegadaEscopo2" in u_data:
                    unidade.PegadaEscopo2 = u_data.get("PegadaEscopo2", 0.0)
                if "PegadaEscopo3" in u_data:
                    unidade.PegadaEscopo3 = u_data.get("PegadaEscopo3", 0.0)

                st.session_state.unidades.append(unidade)
                
                # Se a unidade tem uma conexão, adicionar ao session_state.conexoes
                if conexao:
                    self.add_edge(
                        conexao.origem,
                        conexao.destino,
                        massa=conexao.massa,
                        periodo=conexao.periodo,
                        label=conexao.label,
                        id_fluxo=conexao.id,
                    )

            print(f"DEBUG import_from_json: Total de conexões a importar: {len(data.get('conexoes', []))}")  # Debug
            for c_data in data.get("conexoes", []):
                print(f"DEBUG import_from_json: Importando conexão: {c_data}")  # Debug
                self.add_edge(
                    c_data["origem"],
                    c_data["destino"],
                    massa=c_data.get("massa", 0.0),
                    periodo=c_data.get("periodo", ""),
                    label=c_data.get("label", "Fluxo"),
                    id_fluxo=c_data.get("id", ""),
                )
            
            print(f"DEBUG import_from_json: Total de conexões em session_state após importação: {len(st.session_state.conexoes)}")  # Debug
            
            # Propagar a pegada após importar
            self.propagar_pegada()

            return True
        except Exception as e:
            st.error(f"Erro ao importar dados: {str(e)}")
            return False

    def get_edges_for_graph(self) -> List[Dict]:
        return [
            {
                "id": getattr(c, "id", ""),
                "source": c.origem,
                "target": c.destino,
                "massa": c.massa,
                "label": getattr(c, "label", "Fluxo"),
                "periodo": c.periodo,
            }
            for c in st.session_state.conexoes
        ]

    # --- Atualização de Pegadas ---
    def propagar_pegada(self):
        """Atualiza a pegada de todas as unidades com base nas conexões"""
        from calculations import EmissionCalculator
        EmissionCalculator.propagar_pegada(
            st.session_state.unidades,
            self.get_edges_for_graph()
        )
