import pandas as pd
import py7zr
import os
import urllib.request # <--- Mudança principal: biblioteca nativa para FTP
import ssl
import streamlit as st

# Configuração do FTP do Governo
BASE_URL = "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED"

def baixar_e_processar_caged(ano, mes):
    mes_str = str(mes).zfill(2)
    ano_str = str(ano)
    filename_7z = f"CAGEDMOV{ano_str}{mes_str}.7z"
    filename_txt = f"CAGEDMOV{ano_str}{mes_str}.txt"
    
    # URL do FTP
    url = f"{BASE_URL}/{ano_str}/{ano_str}{mes_str}/{filename_7z}"
    
    local_dir = "data"
    local_7z = os.path.join(local_dir, filename_7z)

    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    # 1. Download (Usando urllib que aceita FTP)
    if not os.path.exists(local_7z):
        st.info(f"⏳ Baixando CAGED ({mes_str}/{ano_str})... Aguarde.")
        try:
            # Ignora verificação SSL se necessário (comum em sites do governo)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(url, context=ctx) as response, open(local_7z, 'wb') as out_file:
                out_file.write(response.read())
                
            st.success("Download concluído!")
        except Exception as e:
            st.error(f"Erro no download FTP: {e}")
            return None

    # 2. Extração
    try:
        # Verifica se já foi extraído
        arquivos_txt = [f for f in os.listdir(local_dir) if f.endswith('.txt') and f"{ano_str}{mes_str}" in f]
        
        if not arquivos_txt:
            st.info("📦 Descompactando...")
            with py7zr.SevenZipFile(local_7z, mode='r') as z:
                z.extractall(path=local_dir)
            st.success("Descompactado!")
            
        # Pega o arquivo descompactado
        arquivos_txt = [f for f in os.listdir(local_dir) if f.endswith('.txt') and f"{ano_str}{mes_str}" in f]
        arquivo_final = os.path.join(local_dir, arquivos_txt[0])

        # 3. Leitura Otimizada (Lê só o necessário)
        st.info("📖 Lendo dados...")
        
        # Colunas principais para economizar memória
        # Adapte conforme o layout exato do CAGED novo
        df = pd.read_csv(
            arquivo_final, 
            sep=';', 
            encoding='utf-8', 
            dtype=str, 
            nrows=100000 # Limitando para não travar seu PC
        )
        return df

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return None