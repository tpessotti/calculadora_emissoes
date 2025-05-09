import pandas as pd

def importar_fatores_emissao():
    """
    Importa a base de dados de fatores de emissão do arquivo Excel.
    
    Retorna:
        DataFrame: Contendo os dados das linhas 23 a 509 da aba 'Fatores de Emissão'.
    """
    # Configurações do arquivo
    caminho_arquivo = "Fatores de Emissão.xlsx"
    nome_aba = "Fatores de Emissão"
    linha_inicial = 23  # Primeira linha de dados (base 1)
    linha_final = 509   # Última linha de dados (base 1)
    
    try:
        # Importar o arquivo Excel
        # Usamos header=None pois queremos ler todas as linhas brutas
        # Depois selecionamos o intervalo desejado
        df = pd.read_excel(
            caminho_arquivo,
            sheet_name=nome_aba,
            header=None,
            skiprows=linha_inicial-1,  # skiprows é base 0
            nrows=linha_final-linha_inicial+1
        )
        
        #print("Dados importados com sucesso!")
        #print(f"Shape do DataFrame: {df.shape}")
        
        return df
    
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao importar os dados: {str(e)}")
        return None

def separar_fatores_combustao_estacionaria(df_original):
    """
    Separa combustíveis fósseis (linhas 24-68) e biomassa (linhas 71-89),
    usando as 3 primeiras linhas de cada bloco para formar os cabeçalhos.
    
    Retorna:
        tuple: (df_fosseis, df_biomassa) com cabeçalhos no formato "Linha1 - Linha2 (Linha3)".
    """
    try:
        # ========================================================
        # 1. COMBUSTÍVEIS FÓSSEIS (Excel: linhas 24-68 → df_original[1:46])
        # ========================================================
        df_fosseis = df_original.iloc[1:46].copy()  # Recorta bloco
        
        # Pega as 3 primeiras linhas do bloco recortado para formar cabeçalhos
        linha1 = df_fosseis.iloc[0].values  # 1ª linha do bloco (Excel linha 24)
        linha2 = df_fosseis.iloc[1].values  # 2ª linha do bloco (Excel linha 25)
        linha3 = df_fosseis.iloc[2].values  # 3ª linha do bloco (Excel linha 26)
        
        # Cria cabeçalhos no formato "Linha1 - Linha2 (Linha3)"
        cabecalhos_fosseis = [
            f"{str(linha1[i]).strip()} - {str(linha2[i]).strip()} ({str(linha3[i]).strip()})"
            for i in range(len(linha1))
        ]
        
        # Aplica cabeçalhos e remove as 3 linhas usadas
        df_fosseis.columns = cabecalhos_fosseis
        df_fosseis = df_fosseis.iloc[3:].reset_index(drop=True)
        
        # ========================================================
        # 2. BIOMASSA (Excel: linhas 71-89 → df_original[48:67])
        # ========================================================
        df_biomassa = df_original.iloc[48:67].copy()  # Recorta bloco
        
        # Repete o processo para biomassa
        linha1_bio = df_biomassa.iloc[0].values  # 1ª linha do bloco (Excel linha 71)
        linha2_bio = df_biomassa.iloc[1].values  # 2ª linha do bloco (Excel linha 72)
        linha3_bio = df_biomassa.iloc[2].values  # 3ª linha do bloco (Excel linha 73)
        
        cabecalhos_biomassa = [
            f"{str(linha1_bio[i]).strip()} - {str(linha2_bio[i]).strip()} ({str(linha3_bio[i]).strip()})"
            for i in range(len(linha1_bio))
        ]
        
        df_biomassa.columns = cabecalhos_biomassa
        df_biomassa = df_biomassa.iloc[3:].reset_index(drop=True)
        
        # ========================================================
        # 3. LIMPEZA FINAL (remove colunas/linhas vazias)
        # ========================================================
        for df in [df_fosseis, df_biomassa]:
            df.dropna(axis=1, how='all', inplace=True)  # Colunas vazias
            df.dropna(axis=0, how='all', inplace=True)  # Linhas vazias
        
        print("✔ Tabelas separadas com sucesso!")
        print(f"→ Combustíveis fósseis: {df_fosseis.shape[0]} linhas, {df_fosseis.shape[1]} colunas")
        print(f"→ Biomassa: {df_biomassa.shape[0]} linhas, {df_biomassa.shape[1]} colunas")
        
        return df_fosseis, df_biomassa
    
    except Exception as e:
        print(f"✖ Erro ao separar tabelas: {e}")
        return None, None

# Exemplo de uso:
df_fatores = importar_fatores_emissao()
if df_fatores is not None:
    combustiveis_fosseis, biomassa = separar_fatores_combustao_estacionaria(df_fatores)
    # Aqui você pode continuar com o processamento dos DataFrames combustiveis_fosseis e biomassa
    