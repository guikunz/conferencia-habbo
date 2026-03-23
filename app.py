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

    # 1. Verifica Nick Inapropriado
    if any(p in nick.lower() for p in PALAVRAS_INAPROPRIADAS):
        resultado["inapropriado"] = True

    # 2. Busca o Usuário (Com tentativas para evitar bloqueio)
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

    # 3. Verifica Visibilidade
    if not data.get("profileVisible", True):
        resultado["visibilidade_off"] = True

    # 4. Verifica Modo Offline e Ausência
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

    # 5. Verifica Grupos (Nome e Descrição)
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