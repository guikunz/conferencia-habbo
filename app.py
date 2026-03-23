import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import concurrent.futures
import time

# CONFIGURAÇÕES DA PÁGINA
st.set_page_config(page_title="Conferência Habbo", page_icon="🕵️‍♂️")

URL_USER = "https://www.habbo.com.br/api/public/users?name="

PALAVRAS_PROIBIDAS = ["exército", "militar", "dme", "rcc", "csi", "dph"]
PALAVRAS_INAPROPRIADAS = ["sexo", "buceta", "piroca", "rola", "pau", "penis", "vagina", "xota", "cu", "fdp", "porra", "caralho"]

def verificar_nick(nick):
    nick = str(nick).strip()
    if not nick:
        return None
    
    resultado = {
        "nick": nick, "inexistente": False, "inapropriado": False,
        "visibilidade_off": False, "modo_offline": False, 
        "ausente": None, "outra_org": None, "sem_requisitos": False
    }

    if any(p in nick.lower() for p in PALAVRAS_INAPROPRIADAS):
        resultado["inapropriado"] = True

    data = None
    sucesso_usuario = False
    
    for tentativa in range(3):
        try:
            r = requests.get(URL_USER + nick, timeout=10)
            if r.status_code == 200:
                data = r.json()
                sucesso_usuario = True
                break
            elif r.status_code == 429:
                time.sleep(2.5)
                continue
            elif r.status_code == 404:
                break
            else:
                break
        except requests.RequestException:
            time.sleep(2)
            continue

    if not sucesso_usuario or not data:
        resultado["inexistente"] = True
        return resultado

    if not data.get("profileVisible", True):
        resultado["visibilidade_off"] = True

    last_access = data.get("lastAccessTime")
    if not last_access:
        resultado["modo_offline"] = True
    else:
        try:
            data_api = datetime.fromisoformat(last_access.replace('+0000', '+00:00'))
            agora = datetime.now(timezone.utc)
            dias = (agora - data_api).days
            if dias >= 20:
                resultado["ausente"] = f"{nick} ({dias} dias)"
        except ValueError:
            pass 

    unique_id = data.get("uniqueId")
    encontrou_dic = False

    if unique_id:
        for tentativa in range(3):
            try:
                r_grupos = requests.get(f"https://www.habbo.com.br/api/public/users/{unique_id}/groups", timeout=10)
                if r_grupos.status_code == 200:
                    for grupo in r_grupos.json():
                        texto = (grupo.get("name", "") + " " + grupo.get("description", "")).lower()
                        if any(p in texto for p in PALAVRAS_PROIBIDAS):
                            resultado["outra_org"] = f"{nick} → {grupo.get('name')}"
                            break
                        if "polícia dic" in texto:
                            encontrou_dic = True
                    break 
                elif r_grupos.status_code == 429:
                    time.sleep(2.5)
                    continue
                else:
                    break
            except requests.RequestException:
                time.sleep(2)
                continue

    motto = data.get("motto", "").lower()
    tem_missao_dic = ("[dic]" in motto or "[đic]" in motto) and "soldado" in motto

    if not encontrou_dic and not tem_missao_dic:
        resultado["sem_requisitos"] = True

    return resultado

# INTERFACE DO SITE
st.title("🕵️‍♂️ Conferência de Soldados")
st.write("Faça o upload da planilha Excel (.xlsx) contendo a lista de nicks para verificação.")

arquivo_enviado = st.file_uploader("Escolha o arquivo Excel", type=["xlsx"])

if arquivo_enviado is not None:
    if st.button("Iniciar Verificação", type="primary"):
        
        with st.spinner('Lendo a planilha e consultando os servidores do Habbo... Por favor, aguarde.'):
            try:
                # O Pandas lê o arquivo que o usuário enviou pelo site
                df = pd.read_excel(arquivo_enviado, sheet_name="INICIO")
                nicks_para_verificar = df.iloc[1:, 1].dropna().tolist()
                
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

                st.success("Verificação concluída com sucesso!")
                
                # Mostra o texto na tela
                st.text_area("Resultado do Relatório:", relatorio, height=300)
                
                # Botão para baixar o TXT
                st.download_button(
                    label="📥 Baixar Relatório (.txt)",
                    data=relatorio,
                    file_name=f"relatorio_soldados_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Ocorreu um erro ao ler a planilha. Verifique se a aba se chama 'INICIO'. Erro: {e}")