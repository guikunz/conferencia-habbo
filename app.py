import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import concurrent.futures
import time

# CONFIGURAÇÕES DA PÁGINA
st.set_page_config(page_title="Conferência Habbo", page_icon="🕵️‍♂️")

URL_USER = "https://www.habbo.com.br/api/public/users?name="

# LISTAS ATUALIZADAS
PALAVRAS_PROIBIDAS = [
    "exército", "militar", "dme", "rcc", "csi", "dph", 
    "marinha", "swat", "pmhh", "rhc", "asa", "dpe", "pho"
]
PALAVRAS_INAPROPRIADAS = [
    "sexo", "buceta", "piroca", "rola", "pau", "penis", 
    "vagina", "xota", "cu", "fdp", "porra", "caralho"
]

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
                        nome_grupo = grupo.get("name", "").lower()
                        desc_grupo = grupo.get("description", "").lower()
                        
                        if not resultado["outra_org"]:
                            if any(p in nome_grupo or p in desc_grupo for p in PALAVRAS_PROIBIDAS):
                                resultado["outra_org"] = f"{nick} → {grupo.get('name', 'Sem Nome')}"
                        
                        if "polícia dic" in nome_grupo or "dic" in desc_grupo:
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

# FUNÇÕES DE FORMATAÇÃO PARA O GOOGLE DOCS
def formatar_padrao(nicks):
    if not nicks: return "Nenhum irregular nesta categoria."
    return "\n\n".join([f"Nick: {n}\nPrint: " for n in nicks])

def formatar_ausentes(ausentes_list):
    if not ausentes_list: return "Nenhum irregular nesta categoria."
    texto_final = []
    for item in ausentes_list:
        if " (" in item:
            nick = item.split(" (")[0]
            dias = item.split("(")[1].replace(" dias)", "")
            texto_final.append(f"Nick: {nick}\nQuantidade de dias ausente: {dias}\nPrint: ")
        else:
            texto_final.append(f"Nick: {item}\nQuantidade de dias ausente: ?\nPrint: ")
    return "\n\n".join(texto_final)

def formatar_orgs(orgs_list):
    if not orgs_list: return "Nenhum irregular nesta categoria."
    texto_final = []
    for item in orgs_list:
        if " → " in item:
            nick = item.split(" → ")[0]
            grupo = item.split(" → ")[1]
            texto_final.append(f"Nick: {nick}\nGrupo policial que possui: {grupo}\nPrint: ")
        else:
            texto_final.append(f"Nick: {item}\nGrupo policial que possui: ?\nPrint: ")
    return "\n\n".join(texto_final)

# --- INTERFACE DO SITE ---
st.title("🕵️‍♂️ Conferência de Soldados (DIC)")
st.write("O sistema buscará os nicks da planilha e gerará um relatório direto no Google Docs.")

SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
ABA = "INICIO"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# ⚠️ COLOQUE AQUI A URL DO APP DA WEB QUE VOCÊ COPIOU LÁ NO GOOGLE APPS SCRIPT
URL_WEBHOOK_GOOGLE = "https://script.google.com/macros/s/AKfycbz--5QLXcgj14H3JQidJ17A7orRrIDoBmDApdDMHUVO9gy1z7KzV1K7A_Fs496IIfzV/exec"

if st.button("Iniciar Verificação e Gerar Doc", type="primary"):
    
    with st.spinner('Analisando nicks e gerando Google Docs (isso pode levar alguns minutos)...'):
        try:
            df = pd.read_excel(url_excel, sheet_name=ABA)
            nicks_para_verificar = df.iloc[1:, 1].dropna().tolist()
            
            st.info(f"Total de {len(nicks_para_verificar)} nicks encontrados na planilha. Consultando o Habbo...")

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

            total = sum(map(len, [ausentes, outras_orgs, sem_requisitos, modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado]))
            
            # PACOTE DE DADOS PARA ENVIAR AO GOOGLE DOCS
            dados
