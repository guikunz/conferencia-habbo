import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
import concurrent.futures
import time
import io

# CONFIGURAÇÕES DA PÁGINA
st.set_page_config(page_title="Central de conferências DIC/Sp", page_icon="🕵️", layout="wide")

# Inicializa o "Roteador" de páginas na memória do site para a aba de conferência
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'inicio'

# ==========================================
# --- INJEÇÃO DE CSS (O SEGREDO DO VISUAL) ---
# ==========================================
st.markdown("""
<style>
    /* Estilizando o fundo para um tom muito escuro (quase preto) */
    .stApp {
        background-color: #0b090a;
        color: #e0e0e0;
    }
    
    /* Títulos em Dourado e com fonte impactante */
    h1, h2, h3, h4 {
        color: #eab308 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Titulos das seções menores */
    .section-title {
        color: #eab308;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Estilizando os containers (as caixas em volta dos itens) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #423512 !important;
        background-color: #14110f !important;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.8);
    }

    /* Estilizando os botões principais */
    .stButton > button {
        background-color: #1a0f00 !important;
        color: #eab308 !important;
        border: 1px solid #ca8a04 !important;
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        background-color: #eab308 !important;
        color: #0b090a !important;
        border: 1px solid #eab308 !important;
    }

    /* ESTILIZAÇÃO DO LINK FINAL (Transformando em Botão) */
    .btn-link-oficial {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #1a0f00;
        color: #eab308 !important;
        border: 1px solid #ca8a04;
        padding: 12px 20px;
        border-radius: 8px;
        text-decoration: none !important;
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 20px;
        transition: 0.3s;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .btn-link-oficial:hover {
        background-color: #eab308;
        color: #0b090a !important;
        border: 1px solid #eab308;
        box-shadow: 0px 0px 15px rgba(234, 179, 8, 0.4);
    }

    /* === BOTÕES DO FILTRO SYSTEM (Design Dark & Gold 3D) === */
    .btn-filtro {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #1a0f00;
        color: #eab308 !important;
        border: 1px solid #ca8a04;
        padding: 14px 20px;
        border-radius: 8px;
        text-decoration: none !important;
        font-weight: bold;
        font-size: 1.05rem;
        margin-bottom: 18px;
        box-shadow: 4px 4px 0px #000000; /* Sombra preta dura para o efeito 3D */
        transition: 0.15s ease-in-out;
        text-transform: uppercase;
    }
    .btn-filtro:hover {
        transform: translate(4px, 4px); /* Botão 'afunda' */
        box-shadow: 0px 0px 0px #000000; /* Remove a sombra ao afundar */
        background-color: #eab308;
        color: #0b090a !important;
        border: 1px solid #eab308;
    }

    /* Estilizando métricas (cartões de resumo) */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"] {
        color: #a8a29e !important;
        font-weight: bold;
    }

    /* Estilizando as caixas de texto e seleção */
    .stTextArea textarea, div[data-baseweb="select"] > div {
        background-color: #1c1917 !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 8px;
    }
    
    .stTextArea textarea:focus, div[data-baseweb="select"] > div:focus-within {
        border-color: #eab308 !important;
        box-shadow: 0 0 0 1px #eab308 !important;
    }
    
    /* Header estilizado imitando a imagem */
    .custom-header {
        background: linear-gradient(90deg, #1a1100 0%, #0b090a 100%);
        border: 1px solid #ca8a04;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0px 0px 20px rgba(202, 138, 4, 0.1);
    }
    
    /* ==========================================
       NOVO CSS AGRESSIVO PARA O MENU LATERAL 
       ========================================== */
    [data-testid="stSidebar"] {
        background-color: #14110f !important;
        border-right: 1px solid #423512 !important;
    }
    
    /* Força TODAS as letras do menu a ficarem brancas */
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Devolve a cor dourada apenas para o título do menu */
    [data-testid="stSidebar"] h2 {
        color: #eab308 !important;
    }
    
    /* Deixa o rodapé com cor cinza */
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
        color: #a8a29e !important;
    }
    
    /* Transforma a bolinha de seleção do menu em dourada */
    [data-testid="stSidebar"] div[data-baseweb="radio"] > div {
        background-color: #eab308 !important;
    }
</style>
""", unsafe_allow_html=True)

URL_USER = "https://www.habbo.com.br/api/public/users?name="

PALAVRAS_PROIBIDAS = [
    "exército", "dme", "rcc", "csi", "dph", "pab", "dpe", "dsp", "depi", "dpt", "dtam",
    "marinha", "swat", "pmhh", "rhc", "pho", "ex.br", "mcc", "feb", "drh", "dco", "pso", "dpo", "grm", "dho", "cmi", "dim", "doh"
]
PALAVRAS_INAPROPRIADAS = [
    "sexo", "buceta", "piroca", "rola", "pau", "penis", 
    "vagina", "xota", "cu", "fdp", "porra", "caralho"
]

URL_WEBHOOK_GOOGLE = "https://script.google.com/macros/s/AKfycbwt60cX_RXKl7X0jS6LeqDhXdOV1QGm1d4ErZkntJPWJfbLTVHBBOSHxd2uMaWDwEuVGA/exec"

def verificar_nick(nick, categoria):
    nick = str(nick).strip()
    if not nick: return None
    
    resultado = {
        "nick": nick, "inexistente": False, "inapropriado": False,
        "visibilidade_off": False, "modo_offline": False, 
        "ausente_padrao": None, "ausente_7_19": None, "ausente_20_mais": None,
        "ausente_60_mais": None, "ausente_90_mais": None,
        "outra_org": None, "sem_requisitos": False
    }

    if any(p in nick.lower() for p in PALAVRAS_INAPROPRIADAS): resultado["inapropriado"] = True

    data = None
    sucesso_usuario = False
    
    for tentativa in range(3):
        try:
            r = requests.get(URL_USER + nick, timeout=10)
            if r.status_code == 200:
                data = r.json(); sucesso_usuario = True; break
            elif r.status_code == 429: time.sleep(2.5); continue
            elif r.status_code == 404: break
            else: break
        except requests.RequestException: time.sleep(2); continue

    if not sucesso_usuario or not data:
        resultado["inexistente"] = True
        return resultado

    if not data.get("profileVisible", True): resultado["visibilidade_off"] = True

    last_access = data.get("lastAccessTime")
    if not last_access: resultado["modo_offline"] = True
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
        except ValueError: pass 

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
                            if nome_l.startswith("[dic]"): is_dic_dept = True
                                
                        if categoria == "Aspirantes a Coronéis" and "[csi] corredor" in nome_l: is_dic_dept = True
                                
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
        if not any("polícia dic" in g for g in grupos_identificados) and "[dic]" not in motto: resultado["sem_requisitos"] = True
    elif categoria in ["Cabos a Subtenentes", "Aspirantes a Coronéis"]:
        check_grupos = ["[dic] praças", "[dic] oficiais", "[dic] oficiais superiores"]
        if not any(req in g for g in grupos_identificados for req in check_grupos): resultado["sem_requisitos"] = True
    elif categoria == "Cargos Executivos":
        check_exec = ["[dic] corpo exec. superior", "[dic] corpo executivo"]
        if not any(req in g for g in grupos_identificados for req in check_exec): resultado["sem_requisitos"] = True

    return resultado

# FUNÇÕES DE FORMATAÇÃO
def formatar_padrao(lista): return "\n\n".join([f"Nick: {n}\nPrint: " for n in lista]) if lista else "Nenhum irregular nesta categoria."
def formatar_ausentes(lista):
    if not lista: return "Nenhum irregular nesta categoria."
    return "\n\n".join([f"Nick: {i.split(' (')[0]}\nQuantidade de dias ausente: {i.split('(')[1].replace(' dias)', '')}\nPrint: " for i in lista])
def formatar_orgs(orgs_list):
    if not orgs_list: return "Nenhum irregular nesta categoria."
    texto_final = []
    for item in orgs_list:
        if " → " in item:
            nick = item.split(" → ")[0]; grupo = item.split(" → ")[1]
            texto_final.append(f"Nick: {nick}\nGrupo policial que possui: {grupo}\nPrint: ")
        else: texto_final.append(f"Nick: {item}\nGrupo policial que possui: ?\nPrint: ")
    return "\n\n".join(texto_final)
def listar(lista): return "\n".join(lista) if lista else "Nenhum"


# ==========================================
# --- MENU LATERAL ---
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🕵️ MENU - Sp</h2>", unsafe_allow_html=True)
    st.markdown("---")
    menu_selecionado = st.radio(
        "Navegação",
        # Ordem das opções atualizada
        ["Conferência Oficial", "Filtro do System", "Ferramenta de Cópia"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("© 2026 DIC - Supervisores - by: gui_kunz")


# ==========================================
# --- PÁGINA 1: CONFERÊNCIA OFICIAL ---
# ==========================================
if menu_selecionado == "Conferência Oficial":
    
    st.markdown("""
        <div class='custom-header'>
            <h1 style='margin-bottom: 0px;'>DEPARTAMENTO DE INVESTIGAÇÃO CRIMINAL - Supervisores</h1>
            <p style='color: #a8a29e; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 2px;'>Módulo de Conferência de Graduação, Posto e Cargos</p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.pagina_atual == 'inicio':

        with st.container(border=True):
            col_esq, col_dir = st.columns([1, 2], gap="large") 
            
            with col_esq:
                st.markdown("<div class='section-title'>📋 INSIRA OS NICKS COPIADOS DO SYSTEM ABAIXO</div>", unsafe_allow_html=True)
                dados_colados = st.text_area(
                    "Copie as linhas da sua planilha e cole abaixo:", 
                    height=130, 
                    label_visibility="collapsed", 
                    placeholder="Cole os dados aqui..."
                )

            with col_dir:
                st.markdown("<div class='section-title'>🕵️ CONSULTA POR  Graduação, Posto e Cargos</div>", unsafe_allow_html=True)
                categoria_sel = st.selectbox(
                    "Selecione uma categoria de patente:", 
                    ["Soldados", "Cabos a Subtenentes", "Aspirantes a Coronéis", "Cargos Executivos"],
                    label_visibility="collapsed"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                iniciar_btn = st.button(f"🔎 INICIAR VERIFICAÇÃO", type="primary", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if iniciar_btn:
            if not dados_colados.strip():
                st.warning("⚠️ O banco de dados está vazio. Por favor, cole os dados da planilha antes de iniciar.")
            else:
                with st.status("Processando dados de inteligência...", expanded=True) as status:
                    try:
                        df = pd.read_csv(io.StringIO(dados_colados), sep='\t', header=None)
                        indice_coluna_nick = 2 if df.shape[1] >= 3 else 0
                        nicks = df.iloc[:, indice_coluna_nick].dropna().astype(str).tolist()
                        nicks = [n.strip() for n in nicks if n.strip() and str(n).lower() != 'nan']
                        total_lidos = len(nicks)
                        
                        st.write(f"Estabelecendo conexão segura para {total_lidos} policiais...")
                        
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
                        
                        total_ausentes = len(aus_p) + len(aus_7) + len(aus_20) + len(aus_60) + len(aus_90)
                        total_irregulares = sum(map(len, [aus_p, aus_7, aus_20, aus_60, aus_90, orgs, sem_req, off, vis, inex, inap]))

                        # ATUALIZADO: Todos os campos agora são exibidos na pré-visualização
                        relatorio = f"Conferência de {categoria_sel}\nData: {data_hoje}\nTotal de irregulares: {total_irregulares}\n"
                        relatorio += f"\nAusentes:\n{listar(aus_p + aus_7 + aus_20 + aus_60 + aus_90)}"
                        relatorio += f"\n\nOutras Orgs:\n{listar(orgs)}"
                        relatorio += f"\n\nRetiraram-se dos grupos:\n{listar(sem_req)}"
                        relatorio += f"\n\nModo Offline:\n{listar(off)}"
                        relatorio += f"\n\nPerfil Oculto (Visibilidade Off):\n{listar(vis)}"
                        relatorio += f"\n\nNicks Inexistentes:\n{listar(inex)}"
                        relatorio += f"\n\nNicks Inapropriados:\n{listar(inap)}"

                        st.session_state.relatorio_texto = relatorio
                        st.session_state.df_view = df 
                        st.session_state.dados_google = {
                            "categoria": categoria_sel, "data_hoje": data_hoje, "total": str(total_irregulares),
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
                        
                        st.session_state.metricas = {"lidos": total_lidos, "irregulares": total_irregulares, "ausentes": total_ausentes}
                        
                        status.update(label="Verificação concluída com sucesso!", state="complete", expanded=False)
                        time.sleep(0.5) 
                        
                        st.session_state.pagina_atual = 'resultados'
                        st.rerun()

                    except Exception as e: 
                        status.update(label="Erro no processamento", state="error", expanded=True)
                        st.error(f"Detalhe do erro: {e}")

    elif st.session_state.pagina_atual == 'resultados':

        col_v1, col_v2, col_v3 = st.columns([1, 4, 1])
        with col_v1:
            if st.button("⬅️ VOLTAR AO INÍCIO", use_container_width=True):
                st.session_state.pagina_atual = 'inicio'
                st.rerun() 

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_met1, col_met2, col_met3 = st.columns(3)
        col_met1.metric(label="👥 POLICIAIS IDENTIFICADOS", value=st.session_state.metricas["lidos"])
        col_met2.metric(label="⚠️ AVISOS DE IRREGULARIDADE", value=st.session_state.metricas["irregulares"])
        col_met3.metric(label="😴 POLICIAIS AUSENTES", value=st.session_state.metricas["ausentes"])

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_view_esq, col_view_dir = st.columns([1, 1.2], gap="medium")
        
        with col_view_esq:
            st.markdown("<div class='section-title'>📑 REGISTROS ANALISADOS</div>", unsafe_allow_html=True)
            st.dataframe(st.session_state.df_view, use_container_width=True, height=350)
            
        with col_view_dir:
            st.markdown("<div class='section-title'>📝 CONSOLIDAÇÃO DOS DADOS</div>", unsafe_allow_html=True)
            st.text_area("Resultado gerado", st.session_state.relatorio_texto, height=265, label_visibility="collapsed")
            
            if st.button("GERAR O RELATÓRIO OFICIAL 📄", type="primary", use_container_width=True):
                with st.spinner("Sincronizando com o Arquivo Central (Google Docs)..."):
                    try:
                        resposta_google = requests.post(URL_WEBHOOK_GOOGLE, json=st.session_state.dados_google)
                        
                        try:
                            res = resposta_google.json()
                            if res.get("status") == "sucesso": 
                                st.success("✅ Documento gerado e arquivado!")
                                
                                url_final = res.get('url')
                                st.markdown(f"""
                                    <a href='{url_final}' target='_blank' class='btn-link-oficial'>
                                        🔗 ACESSAR O RELATÓRIO OFICIAL AQUI
                                    </a>
                                """, unsafe_allow_html=True)
                                
                            else:
                                st.error(f"Falha na comunicação: {res.get('mensagem')}")
                                
                        except Exception as decodificacao_erro:
                            st.error("⚠️ O Google bloqueou o acesso ou ocorreu um erro crítico no Apps Script.")
                            st.info("Verifique se em 'Gerenciar Implantações' a opção 'Quem tem acesso' está como 'Qualquer pessoa'.")
                            with st.expander("Ver resposta técnica do Google (Para diagnóstico)"):
                                st.text(resposta_google.text) 
                                
                    except Exception as e:
                        st.error(f"Erro de conexão com a base de dados: {e}")

# ==========================================
# --- PÁGINA 2: FILTRO DO SYSTEM ---
# ==========================================
elif menu_selecionado == "Filtro do System":

    st.markdown("""
        <div class='custom-header'>
            <h1 style='margin-bottom: 0px;'>FILTRO DO SYSTEM</h1>
            <p style='color: #a8a29e; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 2px;'>Links de atalho para consulta direta no banco de dados</p>
        </div>
    """, unsafe_allow_html=True)

    links_militares = {
        "Soldados": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=1&limite=100",
        "Cabos": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=2&limite=100",
        "Sargentos": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=3&limite=100",
        "Subtenentes": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=4&limite=100",
        "Aspirantes": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=5&limite=100",
        "Tenentes": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=6&limite=100",
        "Capitães": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=7&limite=100",
        "Majores": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=8&limite=100",
        "Tenentes-Coronéis": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=9&limite=100",
        "Coronéis": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=1&patente=10&limite=100"
    }

    links_pagas = {
        "Sócio": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=1&limite=100",
        "Agente": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=2&limite=100",
        "Analista": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=3&limite=100",
        "Coordenador": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=4&limite=100",
        "Promotor": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=5&limite=100",
        "Advogado": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=6&limite=100",
        "Administrador": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=7&limite=100",
        "Delegado": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=8&limite=100",
        "Investigador": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=9&limite=100",
        "Detetive": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=10&limite=100",
        "Supervisor": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=11&limite=100",
        "Líder": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=12&limite=100",
        "Líder-Executivo": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=13&limite=100",
        "Chanceler": "https://dic.systemhb.net/membros?filtro=-1&hierarquia=2&patente=14&limite=100"
    }

    with st.container(border=True):
        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown("<div class='section-title' style='text-align: center;'>HIERARQUIA MILITAR</div><br>", unsafe_allow_html=True)
            for nome_botao, link_url in links_militares.items():
                st.markdown(f"<a href='{link_url}' target='_blank' class='btn-filtro'>{nome_botao}</a>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='section-title' style='text-align: center;'>HIERARQUIA PAGA</div><br>", unsafe_allow_html=True)
            for nome_botao, link_url in links_pagas.items():
                st.markdown(f"<a href='{link_url}' target='_blank' class='btn-filtro'>{nome_botao}</a>", unsafe_allow_html=True)


# ==========================================
# --- PÁGINA 3: FERRAMENTA DE CÓPIA ---
# ==========================================
elif menu_selecionado == "Ferramenta de Cópia":
    
    st.markdown("""
        <div class='custom-header'>
            <h1 style='margin-bottom: 0px;'>FERRAMENTA DE EXTRAÇÃO</h1>
            <p style='color: #a8a29e; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 2px;'>Utilitário para cópia rápida de dados do System</p>
        </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<div class='section-title'>🚀 COMO INSTALAR E UTILIZAR</div>", unsafe_allow_html=True)
        
        st.write("Para agilizar sua conferência, você pode instalar um botão na barra de favoritos do seu navegador. Ele copia e formata todos os nicks da página do System com apenas um clique.")
        
        st.markdown("""
        1. Clique no botão dourado abaixo para acessar a página oficial da ferramenta.
        2. Na nova página, **arraste o botão indicado** para a barra de favoritos do seu navegador.
        3. Quando você estiver na tela do System visualizando os policiais, basta **clicar no seu novo favorito**.
        4. Volte aqui na Central DIC e aperte **Ctrl+V** na caixa de texto. Pronto!
        """)
        
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
            <a href='https://guikunz.github.io/copiador-nicks/' target='_blank' class='btn-link-oficial'>
                🔗 ACESSAR PÁGINA DE INSTALAÇÃO DO COPIADOR
            </a>
        """, unsafe_allow_html=True)
