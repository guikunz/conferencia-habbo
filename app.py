import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import concurrent.futures
import time

# CONFIGURAÇÕES DA PÁGINA
st.set_page_config(page_title="Conferência Habbo", page_icon="🕵️‍♂️", layout="wide")

URL_USER = "https://www.habbo.com.br/api/public/users?name="

# LISTAS DE FILTRO
PALAVRAS_PROIBIDAS = [
    "exército", "dme", "rcc", "csi", "dph", 
    "marinha", "swat", "pmhh", "rhc", "dpe", "pho", "ex.br"
]
PALAVRAS_INAPROPRIADAS = [
    "sexo", "buceta", "piroca", "rola", "pau", "penis", 
    "vagina", "xota", "cu", "fdp", "porra", "caralho"
]

URL_WEBHOOK_GOOGLE = "https://script.google.com/macros/s/AKfycbz--5QLXcgj14H3JQidJ17A7orRrIDoBmDApdDMHUVO9gy1z7KzV1K7A_Fs496IIfzV/exec"

def verificar_nick(nick, categoria):
    nick = str(nick).strip()
    if not nick:
        return None
    
    resultado = {
        "nick": nick, "inexistente": False, "inapropriado": False,
        "visibilidade_off": False, "modo_offline": False, 
        "ausente_padrao": None, "ausente_7_19": None, "ausente_20_mais": None,
        "ausente_60_mais": None, "ausente_90_mais": None,
        "outra_org": None, "sem_requisitos": False
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
            dias = int(round((agora - data_api).total_seconds() / 86400))
            
            if categoria in ["Soldados", "Cabos a Subtenentes"]:
                if dias >= 20: resultado["ausente_padrao"] = f"{nick} ({dias} dias)"
            elif categoria == "Aspirantes a Coronéis":
                if 7 <= dias <= 19: resultado["ausente_7_19"] = f"{nick} ({dias} dias)"
                elif dias >= 20: resultado["ausente_20_mais"] = f"{nick} ({dias} dias)"
            elif categoria == "Cargos Executivos":
                if 60 <= dias < 90: resultado["ausente_60_mais"] = f"{nick} ({dias} dias)"
                elif dias >= 90: resultado["ausente_90_mais"] = f"{nick} ({dias} dias)"
        except ValueError:
            pass 

    unique_id = data.get("uniqueId")
    grupos_identificados = []

    if unique_id:
        for tentativa in range(3):
            try:
                r_grupos = requests.get(f"https://www.habbo.com.br/api/public/users/{unique_id}/groups", timeout=10)
                if r_grupos.status_code == 200:
                    for grupo in r_grupos.json():
                        nome_l = grupo.get("name", "").lower()
                        desc_l = grupo.get("description", "").lower()
                        
                        is_dic_dept = False
                        if categoria in ["Aspirantes a Coronéis", "Cargos Executivos"]:
                            if nome_l.startswith("[dic]"):
                                is_dic_dept = True
                                
                        if not is_dic_dept:
                            if not resultado["outra_org"] and any(p in nome_l or p in desc_l for p in PALAVRAS_PROIBIDAS):
                                resultado["outra_org"] = f"{nick} → {grupo.get('name')}"
                        
                        grupos_identificados.append(nome_l)
                    break 
                elif r_grupos.status_code == 429: time.sleep(2.5)
                else: break
            except requests.RequestException: time.sleep(2)

    motto = data.get("motto", "").lower()
    
    if categoria == "Soldados":
        if not any("polícia dic" in g for g in grupos_identificados) and "[dic]" not in motto:
            resultado["sem_requisitos"] = True
            
    elif categoria in ["Cabos a Subtenentes", "Aspirantes a Coronéis"]:
        check_grupos = ["[dic] praças", "[dic] oficiais", "[dic] oficiais superiores"]
        if not any(g in grupos_identificados for g in check_grupos):
            resultado["sem_requisitos"] = True
            
    elif categoria == "Cargos Executivos":
        check_exec = ["[dic] corpo exec. superior", "[dic] corpo executivo"]
        if not any(g in grupos_identificados for g in check_exec):
            resultado["sem_requisitos"] = True

    return resultado

# FUNÇÕES DE FORMATAÇÃO
def formatar_padrao(lista):
    return "\n\n".join([f"Nick: {n}\nPrint: " for n in lista]) if lista else "Nenhum irregular nesta categoria."

def formatar_ausentes(lista):
    if not lista: return "Nenhum irregular nesta categoria."
    return "\n\n".join([f"Nick: {i.split(' (')[0]}\nQuantidade de dias ausente: {i.split('(')[1].replace(' dias)', '')}\nPrint: " for i in lista])

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

def listar(lista): return "\n".join(lista) if lista else "Nenhum"

# --- INTERFACE ---
st.title("🕵️‍♂️ Central de Conferência (DIC)")

col1, col2 = st.columns([1, 2]) 

with col1:
    categoria_sel = st.selectbox(
        "Selecione a patente:", 
        ["Soldados", "Cabos a Subtenentes", "Aspirantes a Coronéis", "Cargos Executivos"]
    )

SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

if st.button(f"Iniciar Verificação: {categoria_sel}", type="primary"):
    with st.spinner('Puxando dados da planilha e verificando nicks...'):
        try:
            df = pd.read_excel(url_excel, sheet_name="INICIO")
            nicks = df.iloc[1:, 1].dropna().tolist()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                resultados = list(executor.map(lambda n: verificar_nick(n, categoria_sel), nicks))

            aus_p, aus_7, aus_20, aus_60, aus_90, orgs, sem_req, off, vis, inex, inap = [], [], [], [], [], [], [], [], [], [], []

            for r in resultados:
                if not r: continue
                n = r["nick"]
                
                if r["inexistente"]: inex.append(n); continue
                if r["inapropriado"]: inap.append(n); continue
                    
                if r["ausente_90_mais"]: aus_90.append(r["ausente_90_mais"]); continue
                if r["ausente_60_mais"]: aus_60.append(r["ausente_60_mais"]); continue
                if r["ausente_20_mais"]: aus_20.append(r["ausente_20_mais"]); continue
                if r["ausente_7_19"]: aus_7.append(r["ausente_7_19"]); continue
                if r["ausente_padrao"]: aus_p.append(r["ausente_padrao"]); continue
                    
                if r["outra_org"]: orgs.append(r["outra_org"]); continue
                if r["modo_offline"]: off.append(n); continue
                if r["sem_requisitos"]: sem_req.append(n); continue
                if r["visibilidade_off"]: vis.append(n); continue

            fuso_br = timezone(timedelta(hours=-3))
            data_hoje = datetime.now(fuso_br).strftime("%d/%m/%Y")
            total = sum(map(len, [aus_p, aus_7, aus_20, aus_60, aus_90, orgs, sem_req, off, vis, inex, inap]))

            relatorio = f"Conferência de {categoria_sel}\nData: {data_hoje}\nTotal de irregulares: {total}\n"
            relatorio += f"\nAusentes: {listar(aus_p + aus_7 + aus_20 + aus_60 + aus_90)}"
            relatorio += f"\n\nOutras Orgs: {listar(orgs)}"
            relatorio += f"\n\nRetiraram-se dos grupos: {listar(sem_req)}"

            st.session_state.relatorio_texto = relatorio
            st.session_state.dados_google = {
                "categoria": categoria_sel, "data_hoje": data_hoje, "total": str(total),
                "qtd_ausentes_padrao": str(len(aus_p)), "lista_ausentes_padrao": formatar_ausentes(aus_p),
                "qtd_aus_7_19": str(len(aus_7)), "lista_aus_7_19": formatar_ausentes(aus_7),
                "qtd_aus_20_mais": str(len(aus_20)), "lista_aus_20_mais": formatar_ausentes(aus_20),
                "qtd_aus_60_mais": str(len(aus_60)), "lista_aus_60_mais": formatar_ausentes(aus_60),
                "qtd_aus_90_mais": str(len(aus_90)), "lista_aus_90_mais": formatar_ausentes(aus_90),
                "qtd_orgs": str(len(orgs)), "lista_orgs": formatar_orgs(orgs),
                "qtd_offline": str(len(off)), "lista_offline": formatar_padrao(off),
                "qtd_sem_req": str(len(sem_req)), "lista_sem_req": formatar_padrao(sem_req),
                "qtd_visibilidade": str(len(vis)), "lista_visibilidade": formatar_padrao(vis),
                "qtd_inexistente": str(len(inex)), "lista_inexistente": formatar_padrao(inex),
                "qtd_inapropriado": str(len(inap)), "lista_inapropriado": formatar_padrao(inap)
            }
            st.session_state.gerado = True

        except Exception as e: st.error(f"Erro: {e}")

if 'gerado' in st.session_state:
    st.text_area("Relatório:", st.session_state.relatorio_texto, height=300)
    
    if st.button("Gerar no Google Docs 📄", type="secondary"):
        with st.spinner("Gerando relatório no Google Docs..."):
            try:
                res = requests.post(URL_WEBHOOK_GOOGLE, json=st.session_state.dados_google).json()
                if res.get("status") == "sucesso": 
                    st.success("Relatório gerado!")
                    st.markdown(f"### 📄 **[CLIQUE AQUI PARA ABRIR O SEU RELATÓRIO]({res.get('url')})**")
                else:
                    st.error(f"Erro no Google: {res.get('mensagem')}")
            except Exception as e:
                st.error(f"Erro de comunicação: {e}")
