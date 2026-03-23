import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import concurrent.futures
import time

# --- INTERFACE DO SITE ---
st.title("🕵️‍♂️ Conferência de Soldados (DIC)")
st.write("O sistema buscará os nicks da planilha e gerará um relatório direto no Google Docs.")

SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
ABA = "INICIO"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# COLOQUE AQUI A URL DO APP DA WEB QUE VOCÊ COPIOU NO PASSO 2
URL_WEBHOOK_GOOGLE = "https://script.google.com/macros/s/AKfycbz--5QLXcgj14H3JQidJ17A7orRrIDoBmDApdDMHUVO9gy1z7KzV1K7A_Fs496IIfzV/exec"

if st.button("Iniciar Verificação e Gerar Doc", type="primary"):
    
    with st.spinner('Analisando nicks e gerando Google Docs...'):
        try:
            df = pd.read_excel(url_excel, sheet_name=ABA)
            nicks_para_verificar = df.iloc[1:, 1].dropna().tolist()
            
            ausentes, outras_orgs, sem_requisitos = [], [], []
            modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado = [], [], [], []

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                resultados = list(executor.map(verificar_nick, nicks_para_verificar))

            # FUNÇÕES PARA FORMATAR COMO NO SEU MODELO
            def formatar_padrao(nicks):
                if not nicks: return "Nenhum irregular nesta categoria."
                return "\n\n".join([f"Nick: {n}\nPrint: " for n in nicks])
            
            def formatar_ausentes(ausentes_list):
                if not ausentes_list: return "Nenhum irregular nesta categoria."
                # ausentes_list tem o formato "Nick (X dias)"
                texto_final = []
                for item in ausentes_list:
                    nick = item.split(" (")[0]
                    dias = item.split("(")[1].replace(" dias)", "")
                    texto_final.append(f"Nick: {nick}\nQuantidade de dias ausente: {dias}\nPrint: ")
                return "\n\n".join(texto_final)
            
            def formatar_orgs(orgs_list):
                if not orgs_list: return "Nenhum irregular nesta categoria."
                # orgs_list tem o formato "Nick → Grupo"
                texto_final = []
                for item in orgs_list:
                    nick = item.split(" → ")[0]
                    grupo = item.split(" → ")[1]
                    texto_final.append(f"Nick: {nick}\nGrupo policial que possui: {grupo}\nPrint: ")
                return "\n\n".join(texto_final)

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

            total = sum(map(len, [ausentes, outras_orgs, sem_requisitos, modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado]))
            
            # PACOTE DE DADOS PARA ENVIAR AO GOOGLE DOCS
            dados_para_google = {
                "data_hoje": datetime.now().strftime("%d/%m/%Y"),
                "total": str(total),
                
                "qtd_ausentes": str(len(ausentes)),
                "lista_ausentes": formatar_ausentes(ausentes),
                
                "qtd_orgs": str(len(outras_orgs)),
                "lista_orgs": formatar_orgs(outras_orgs),
                
                "qtd_offline": str(len(modo_offline)),
                "lista_offline": formatar_padrao(modo_offline),
                
                "qtd_sem_req": str(len(sem_requisitos)),
                "lista_sem_req": formatar_padrao(sem_requisitos),
                
                "qtd_visibilidade": str(len(visibilidade_off)),
                "lista_visibilidade": formatar_padrao(visibilidade_off),
                
                "qtd_inexistente": str(len(nick_inexistente)),
                "lista_inexistente": formatar_padrao(nick_inexistente),
                
                "qtd_inapropriado": str(len(nick_inapropriado)),
                "lista_inapropriado": formatar_padrao(nick_inapropriado)
            }

            # Envia os dados para o Google Apps Script
            resposta = requests.post(URL_WEBHOOK_GOOGLE, json=dados_para_google)
            resultado_api = resposta.json()

            if resultado_api.get("status") == "sucesso":
                st.success("Verificação concluída e Relatório gerado com sucesso!")
                
                # Exibe o link do documento pronto
                url_doc = resultado_api.get('url')
                st.markdown(f"### 📄 **[CLIQUE AQUI PARA ABRIR O SEU RELATÓRIO NO GOOGLE DOCS]({url_doc})**")
                
                # Botão bônus para copiar o link
                st.code(url_doc, language="http")
            else:
                st.error(f"Erro ao gerar Google Doc: {resultado_api.get('mensagem')}")

        except Exception as e:
            st.error(f"Erro crítico: {e}")
            try:
                r_grupos = requests.get(f"https://www.habbo.com.br/api/public/users/{unique_id}/groups", timeout=10)
                if r_grupos.status_code == 200:
                    for grupo in r_grupos.json():
                        nome_grupo = grupo.get("name", "").lower()
                        desc_grupo = grupo.get("description", "").lower()
                        
                        # Verifica se pertence a OUTRAS ORGs (procura no nome ou na descrição)
                        # Só grava a primeira org proibida que achar para não sobreescrever
                        if not resultado["outra_org"]:
                            if any(p in nome_grupo or p in desc_grupo for p in PALAVRAS_PROIBIDAS):
                                resultado["outra_org"] = f"{nick} → {grupo.get('name', 'Sem Nome')}"
                        
                        # Verifica REQUISITOS (Grupo DIC ou Descrição com DIC)
                        if "polícia dic" in nome_grupo or "dic" in desc_grupo:
                            encontrou_dic = True
                            
                    break # Se leu os grupos com sucesso, sai do loop de tentativas
                
                elif r_grupos.status_code == 429:
                    time.sleep(2.5)
                    continue
                else:
                    break
            except requests.RequestException:
                time.sleep(2)
                continue

    # 6. Verifica Missão
    motto = data.get("motto", "").lower()
    tem_missao_dic = ("[dic]" in motto or "[đic]" in motto) and "soldado" in motto

    # 7. Conclusão dos Requisitos
    # O soldado entra como irregular se não encontrou grupo da DIC E também não tem a missão de soldado
    if not encontrou_dic and not tem_missao_dic:
        resultado["sem_requisitos"] = True

    return resultado

# --- INTERFACE DO SITE ---
st.title("🕵️‍♂️ Conferência de Soldados (DIC)")
st.write("O sistema buscará os nicks diretamente da sua planilha do Google Sheets.")

# CONFIGURAÇÃO DIRETA DO GOOGLE SHEETS
SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
ABA = "INICIO"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

if st.button("Iniciar Verificação Agora", type="primary"):
    
    with st.spinner('Puxando dados da nuvem e verificando nicks...'):
        try:
            # Lê o Google Sheets
            df = pd.read_excel(url_excel, sheet_name=ABA)
            
            # Pega os nicks da segunda coluna (B), pulando o cabeçalho
            nicks_para_verificar = df.iloc[1:, 1].dropna().tolist()
            
            st.info(f"Total de {len(nicks_para_verificar)} nicks encontrados na planilha.")

            ausentes, outras_orgs, sem_requisitos = [], [], []
            modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado = [], [], [], []

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
            st.error(f"Erro crítico: {e}")