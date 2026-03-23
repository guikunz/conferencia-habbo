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
    "marinha", "swat", "pmhh", "rhc", "dpe", "pho", "ex.BR"
]
PALAVRAS_INAPROPRIADAS = [
    "sexo", "buceta", "piroca", "rola", "pau", "penis", 
    "vagina", "xota", "cu", "fdp", "porra", "caralho"
]

# URL DO GOOGLE APPS SCRIPT
URL_WEBHOOK_GOOGLE = "https://script.google.com/macros/s/AKfycbz--5QLXcgj14H3JQidJ17A7orRrIDoBmDApdDMHUVO9gy1z7KzV1K7A_Fs496IIfzV/exec"

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
st.write("O sistema buscará os nicks diretamente da sua planilha do Google Sheets.")

SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
ABA = "INICIO"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# BOTÃO 1: VARREDURA PRINCIPAL
if st.button("Iniciar Verificação Agora", type="primary"):
    with st.spinner('Puxando dados da nuvem e verificando nicks...'):
        try:
            df = pd.read_excel(url_excel, sheet_name=ABA)
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

            # Salvando resultados na memória (session_state) para o Google Docs usar depois
            st.session_state.relatorio_texto = relatorio
            st.session_state.total_irregulares = total
            st.session_state.dados_google = {
                "data_hoje": data_hoje,
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

        except Exception as e:
            st.error(f"Erro crítico: {e}")

# EXIBIÇÃO DA INTERFACE APÓS A VARREDURA
if 'relatorio_texto' in st.session_state:
    st.success("Verificação concluída!")
    
    # Exibe a caixa de texto
    st.text_area("Relatório Gerado (Copie abaixo):", st.session_state.relatorio_texto, height=400)
    
    # Botão de download do .txt
    st.download_button(
        label="📥 Baixar Relatório .txt",
        data=st.session_state.relatorio_texto,
        file_name=f"relatorio_{datetime.now().strftime('%d_%m_%Y')}.txt"
    )

    # BOTÃO 2: GOOGLE DOCS (Aparece apenas se houver irregulares)
    if st.session_state.total_irregulares > 0:
        st.markdown("---")
        st.write("Deseja criar a versão formatada no Google Docs para envio?")
        
        if st.button("Gerar Relatório no Google Docs 📄", type="secondary"):
            with st.spinner("Gerando documento, por favor aguarde..."):
                try:
                    resposta = requests.post(URL_WEBHOOK_GOOGLE, json=st.session_state.dados_google)
                    resultado_api = resposta.json()
                    
                    if resultado_api.get("status") == "sucesso":
                        st.success("Relatório gerado com sucesso!")
                        url_doc = resultado_api.get('url')
                        st.markdown(f"### 📄 **[CLIQUE AQUI PARA ABRIR O SEU RELATÓRIO NO GOOGLE DOCS]({url_doc})**")
                    else:
                        st.error(f"Erro ao gerar Google Doc: {resultado_api.get('mensagem')}")
                except Exception as e:
                    st.error(f"Erro de comunicação com o Google: {e}")
