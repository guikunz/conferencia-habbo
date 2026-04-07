import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import concurrent.futures
import time

# CONFIGURAÇÕES DA PÁGINA
st.set_page_config(page_title="Conferência Habbo", page_icon="🕵️‍♂️", layout="wide")

URL_USER = "https://www.habbo.com.br/api/public/users?name="

# LISTAS ATUALIZADAS
PALAVRAS_PROIBIDAS = [
    "exército", "militar", "dme", "rcc", "csi", "dph", 
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
            segundos_ausente = (agora - data_api).total_seconds()
            dias = int(round(segundos_ausente / 86400))
            
            # Lógica de ausência por categoria
            if categoria == "Soldados" or categoria == "Cabos a Subtenentes":
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
    tem_grupo_dic_base = False
    tem_grupo_pracas = False
    tem_grupo_oficiais = False
    tem_grupo_oficiais_sup = False

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
                            tem_grupo_dic_base = True
                        if "[dic] praças" in nome_grupo:
                            tem_grupo_pracas = True
                        if "[dic] oficiais" in nome_grupo and "superiores" not in nome_grupo:
                            tem_grupo_oficiais = True
                        if "[dic] oficiais superiores" in nome_grupo:
                            tem_grupo_oficiais_sup = True
                            
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

    # Lógica de grupos faltantes ("se retiraram") por categoria
    if categoria == "Soldados":
        if not tem_grupo_dic_base and not tem_missao_dic:
            resultado["sem_requisitos"] = True
            
    elif categoria == "Cabos a Subtenentes":
        # Se NÃO tiver o grupo de Praças, está irregular (se retirou)
        if not tem_grupo_pracas:
            resultado["sem_requisitos"] = True
            
    elif categoria == "Aspirantes a Coronéis":
        # Se NÃO tiver Praças, NEM Oficiais, NEM Oficiais Sup, está irregular
        if not tem_grupo_pracas and not tem_grupo_oficiais and not tem_grupo_oficiais_sup:
            resultado["sem_requisitos"] = True
            
    elif categoria == "Cargos Executivos":
        if not tem_grupo_dic_base:
            resultado["sem_requisitos"] = True

    return resultado

# FUNÇÕES DE FORMATAÇÃO
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

def listar(lista): return "\n".join(lista) if lista else "Nenhum"

# --- INTERFACE DO SITE ---
st.title("🕵️‍♂️ Central de Conferência (DIC)")

# SELEÇÃO DE CATEGORIA
categoria_selecionada = st.selectbox(
    "Selecione a patente para realizar a conferência:",
    ["Soldados", "Cabos a Subtenentes", "Aspirantes a Coronéis", "Cargos Executivos"]
)

st.write("O sistema buscará os nicks diretamente da sua planilha do Google Sheets.")
SHEET_ID = "1XfJmLoTi9kbhYx9pRlpvVRX1EF6o2OB-_GXPDAC1TcY"
ABA = "INICIO"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# BOTÃO 1: VARREDURA PRINCIPAL
if st.button(f"Iniciar Verificação: {categoria_selecionada}", type="primary"):
    with st.spinner('Puxando dados da nuvem e verificando nicks...'):
        try:
            df = pd.read_excel(url_excel, sheet_name=ABA)
            nicks_para_verificar = df.iloc[1:, 1].dropna().tolist()
            st.info(f"Total de {len(nicks_para_verificar)} nicks encontrados na planilha.")

            aus_padrao, aus_7_19, aus_20_mais, aus_60_mais, aus_90_mais = [], [], [], [], []
            outras_orgs, sem_requisitos = [], []
            modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado = [], [], [], []

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                resultados = list(executor.map(lambda n: verificar_nick(n, categoria_selecionada), nicks_para_verificar))

            for res in resultados:
                if not res: continue
                nick = res["nick"]
                
                if res["inexistente"]: nick_inexistente.append(nick); continue
                if res["inapropriado"]: nick_inapropriado.append(nick)
                if res["visibilidade_off"]: visibilidade_off.append(nick)
                if res["modo_offline"]: modo_offline.append(nick)
                if res["ausente_padrao"]: aus_padrao.append(res["ausente_padrao"])
                if res["ausente_7_19"]: aus_7_19.append(res["ausente_7_19"])
                if res["ausente_20_mais"]: aus_20_mais.append(res["ausente_20_mais"])
                if res["ausente_60_mais"]: aus_60_mais.append(res["ausente_60_mais"])
                if res["ausente_90_mais"]: aus_90_mais.append(res["ausente_90_mais"])
                if res["outra_org"]: outras_orgs.append(res["outra_org"])
                if res["sem_requisitos"]: sem_requisitos.append(nick)

            fuso_br = timezone(timedelta(hours=-3))
            data_hoje = datetime.now(fuso_br).strftime("%d/%m/%Y")
            
            total = sum(map(len, [aus_padrao, aus_7_19, aus_20_mais, aus_60_mais, aus_90_mais, outras_orgs, sem_requisitos, modo_offline, visibilidade_off, nick_inexistente, nick_inapropriado]))

            # MONTAGEM DO RELATÓRIO BASEADO NA CATEGORIA
            if categoria_selecionada == "Soldados" or categoria_selecionada == "Cabos a Subtenentes":
                relatorio = f"""Conferência de {categoria_selecionada}\nData: {data_hoje}\nQuantidade total de irregulares: {total}\n
----------------------------------------\nQuantidade de policiais ausentes há 20 dias ou mais: [{len(aus_padrao)}]\n{listar(aus_padrao)}\n
----------------------------------------\nQuantidade de policiais com grupos de outras Organizações: [{len(outras_orgs)}]\n{listar(outras_orgs)}\n
----------------------------------------\nQuantidade de policiais com o perfil no "modo offline": [{len(modo_offline)}]\n{listar(modo_offline)}\n
----------------------------------------\nQuantidade de policiais que se retiraram dos grupos da DIC: [{len(sem_requisitos)}]\n{listar(sem_requisitos)}\n
----------------------------------------\nQuantidade de policiais com a visibilidade do perfil desativada: [{len(visibilidade_off)}]\n{listar(visibilidade_off)}\n
----------------------------------------\nQuantidade de policiais que não possuem um nick existente no Habbo: [{len(nick_inexistente)}]\n{listar(nick_inexistente)}\n
----------------------------------------\nQuantidade de policiais que possuem um nick inapropriado no Habbo: [{len(nick_inapropriado)}]\n{listar(nick_inapropriado)}\n
----------------------------------------\nAtenciosamente,"""

            elif categoria_selecionada == "Aspirantes a Coronéis":
                relatorio = f"""Conferência de {categoria_selecionada}\nData: {data_hoje}\nQuantidade total de irregulares: {total}\n
----------------------------------------\nQuantidade de policiais ausentes de 07 à 19 dias: [{len(aus_7_19)}]\n{listar(aus_7_19)}\n
----------------------------------------\nQuantidade de policiais ausentes há 20 dias ou mais: [{len(aus_20_mais)}]\n{listar(aus_20_mais)}\n
----------------------------------------\nQuantidade de policiais com grupos de outras Organizações: [{len(outras_orgs)}]\n{listar(outras_orgs)}\n
----------------------------------------\nQuantidade de policiais com o perfil no "modo offline": [{len(modo_offline)}]\n{listar(modo_offline)}\n
----------------------------------------\nQuantidade de policiais que se retiraram dos grupos da DIC: [{len(sem_requisitos)}]\n{listar(sem_requisitos)}\n
----------------------------------------\nQuantidade de policiais com a visibilidade do perfil desativada: [{len(visibilidade_off)}]\n{listar(visibilidade_off)}\n
----------------------------------------\nQuantidade de policiais que não possuem um nick existente no Habbo: [{len(nick_inexistente)}]\n{listar(nick_inexistente)}\n
----------------------------------------\nQuantidade de policiais que possuem um nick inapropriado no Habbo: [{len(nick_inapropriado)}]\n{listar(nick_inapropriado)}\n
----------------------------------------\nAtenciosamente,"""

            elif categoria_selecionada == "Cargos Executivos":
                relatorio = f"""Conferência de {categoria_selecionada}\nData: {data_hoje}\nQuantidade total de irregulares: {total}\n
----------------------------------------\nQuantidade de policiais ausentes há 60 dias ou mais: [{len(aus_60_mais)}]\n{listar(aus_60_mais)}\n
----------------------------------------\nQuantidade de Chanceleres ausentes há 90 dias ou mais: [{len(aus_90_mais)}]\n{listar(aus_90_mais)}\n
----------------------------------------\nQuantidade de policiais com grupos de outras Organizações: [{len(outras_orgs)}]\n{listar(outras_orgs)}\n
----------------------------------------\nQuantidade de policiais com o perfil no "modo offline": [{len(modo_offline)}]\n{listar(modo_offline)}\n
----------------------------------------\nQuantidade de policiais que se retiraram dos grupos da DIC: [{len(sem_requisitos)}]\n{listar(sem_requisitos)}\n
----------------------------------------\nQuantidade de policiais com a visibilidade do perfil desativada: [{len(visibilidade_off)}]\n{listar(visibilidade_off)}\n
----------------------------------------\nQuantidade de policiais que não possuem um nick existente no Habbo: [{len(nick_inexistente)}]\n{listar(nick_inexistente)}\n
----------------------------------------\nQuantidade de policiais que possuem um nick inadequado no Habbo: [{len(nick_inapropriado)}]\n{listar(nick_inapropriado)}\n
----------------------------------------\nAtenciosamente,"""

            st.session_state.relatorio_texto = relatorio
            st.session_state.total_irregulares = total
            st.session_state.categoria = categoria_selecionada
            
            # Dados adaptados para o Google Docs (CUIDADO: Seus templates no GAS precisam ser atualizados)
            st.session_state.dados_google = {
                "categoria": categoria_selecionada,
                "data_hoje": data_hoje,
                "total": str(total),
                "qtd_ausentes_padrao": str(len(aus_padrao)),
                "lista_ausentes_padrao": formatar_ausentes(aus_padrao),
                "qtd_aus_7_19": str(len(aus_7_19)),
                "lista_aus_7_19": formatar_ausentes(aus_7_19),
                "qtd_aus_20_mais": str(len(aus_20_mais)),
                "lista_aus_20_mais": formatar_ausentes(aus_20_mais),
                "qtd_aus_60_mais": str(len(aus_60_mais)),
                "lista_aus_60_mais": formatar_ausentes(aus_60_mais),
                "qtd_aus_90_mais": str(len(aus_90_mais)),
                "lista_aus_90_mais": formatar_ausentes(aus_90_mais),
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
    st.success(f"Verificação de {st.session_state.categoria} concluída!")
    
    st.text_area("Relatório Gerado (Copie abaixo):", st.session_state.relatorio_texto, height=400)
    
    st.download_button(
        label="📥 Baixar Relatório .txt",
        data=st.session_state.relatorio_texto,
        file_name=f"relatorio_{st.session_state.categoria.replace(' ', '_')}_{datetime.now(timezone(timedelta(hours=-3))).strftime('%d_%m_%Y')}.txt"
    )

    if st.session_state.total_irregulares > 0:
        st.markdown("---")
        st.write("Deseja criar a versão formatada no Google Docs para envio?")
        st.caption("Aviso: Verifique se o seu Google Apps Script já está configurado para receber as novas variáveis desta categoria.")
        
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
