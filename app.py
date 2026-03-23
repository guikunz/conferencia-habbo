import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import concurrent.futures
import time

st.title("🕵️‍♂️ Conferência de Soldados (DIC)")
st.write("O sistema buscará os nicks diretamente da sua planilha do Google Sheets.")

# CONFIGURAÇÃO DIRETA DO GOOGLE SHEETS
SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
ABA = "INICIO"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx&sheet={ABA}"

if st.button("Iniciar Verificação Agora", type="primary"):
    
    with st.spinner('Puxando dados da nuvem e verificando nicks...'):
        try:
            # Lê o Google Sheets diretamente como Excel (mais estável para o Streamlit)
            df = pd.read_excel(url_excel)
            
            # Pega os nicks da segunda coluna (índice 1), pulando o cabeçalho
            nicks_para_verificar = df.iloc[1:, 1].dropna().tolist()
            
            st.info(f"Total de {len(nicks_para_verificar)} nicks encontrados na planilha.")

            ausentes, outras_orgs, sem_requisitos = [], [], []
            modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado = [], [], [], []

            # Processamento paralelo (3 trabalhadores para evitar bloqueio)
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                resultados = list(executor.map(verificar_nick, nicks_para_verificar))

            for res in resultados:
                if not res: continue
                nick = res["nick"]
                
                if res["inexistente"]: nick_inexistente.append(nick); continue
                if res["inapropriado"]: nick_inapropriado.append(nick)
                if res["visibilidade_off"]: visibilidade_off.append(nick)
                if res["modo_offline"]: modo_offline.append(nick)
                if res["ausente"]: ausentes.append(res["ausente"])
                if res["outra_org"]: outras_orgs.append(res["outra_org"])
                if res["sem_requisitos"]: sem_requisitos.append(nick)

            data_hoje = datetime.now().strftime("%d/%m/%Y")
            def listar(lista): return "\n".join(lista) if lista else "Nenhum"

            total = sum(map(len, [ausentes, outras_orgs, sem_requisitos, modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado]))

            relatorio = f"""Conferência de Soldados\nData: {data_hoje}\nQuantidade total de irregulares: {total}\n
----------------------------------------\nAusentes 20+ dias: [{len(ausentes)}]\n{listar(ausentes)}\n
----------------------------------------\nOutras organizações: [{len(outras_orgs)}]\n{listar(outras_orgs)}\n
----------------------------------------\nModo offline: [{len(modo_offline)}]\n{listar(modo_offline)}\n
----------------------------------------\nSem requisitos: [{len(sem_requisitos)}]\n{listar(sem_requisitos)}\n
----------------------------------------\nVisibilidade desativada: [{len(visibilidade_off)}]\n{listar(visibilidade_off)}\n
----------------------------------------\nNick inexistente: [{len(nick_inexistente)}]\n{listar(nick_inexistente)}\n
----------------------------------------\nNick inapropriado: [{len(nick_inapropriado)}]\n{listar(nick_inapropriado)}\n
----------------------------------------\nAtenciosamente,"""

            st.success("Verificação concluída!")
            st.text_area("Relatório Gerado (Copie abaixo):", relatorio, height=400)
            
            st.download_button(
                label="📥 Baixar Relatório .txt",
                data=relatorio,
                file_name=f"relatorio_{datetime.now().strftime('%d_%m_%Y')}.txt"
            )

        except Exception as e:
            st.error(f"Erro ao conectar com o Google Sheets. Verifique se a planilha está com acesso 'Qualquer pessoa com o link'.\nErro: {e}")