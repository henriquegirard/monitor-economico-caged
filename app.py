import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from dateutil.relativedelta import relativedelta
from caged_data import baixar_e_processar_caged

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Monitor Econômico Inteligente", layout="wide", page_icon="🧭")

# --- ESTILO UX/UI ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; }
    div[data-testid="metric-container"] {
        background-color: #1E293B; border: 1px solid #334155;
        padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="metric-container"] label { color: #94A3B8; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #F8FAFC; }
    
    /* Botão Azul Forçado */
    div.stButton > button {
        background-color: #38BDF8 !important; color: #0F172A !important;
        font-weight: bold !important; border: none !important;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #0EA5E9 !important; color: white !important;
    }
    
    h1, h2, h3 {color: #F8FAFC !important;}
    p, span, div, li {color: #CBD5E1;}
    .resumo-box {
        background-color: #1E293B; border-left: 5px solid #38BDF8;
        padding: 20px; border-radius: 5px; margin-bottom: 25px; color: #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# --- MAPAS ---
MAPA_CNAE = {
    'A': 'Agricultura', 'B': 'Extrativa', 'C': 'Indústria', 'D': 'Eletricidade/Gás',
    'E': 'Água/Esgoto', 'F': 'Construção', 'G': 'Comércio', 'H': 'Transporte',
    'I': 'Alojamento/Alim.', 'J': 'Tecnologia', 'K': 'Financeiro',
    'L': 'Imobiliário', 'M': 'Profissional/Cient.', 'N': 'Administrativo',
    'O': 'Adm. Pública', 'P': 'Educação', 'Q': 'Saúde', 'R': 'Artes',
    'S': 'Outros Serviços', 'T': 'Domésticos', 'U': 'Internacionais'
}
MAPA_MUNICIPIOS = {'430460': 'Canoas (RS)', '431490': 'Porto Alegre (RS)'}
MAPA_SEXO = {'1': 'Masculino', '3': 'Feminino', 'M': 'Masculino', 'F': 'Feminino'}

# --- FUNÇÃO DE LIMPEZA ---
def normalizar_colunas(df):
    df.columns = df.columns.str.strip().str.lower()
    df = df.loc[:, ~df.columns.duplicated()]

    cols_novas = []
    for col in df.columns:
        col = col.replace('ç', 'c').replace('ã', 'a').replace('õ', 'o')
        col = col.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        col = col.replace('ó', 'o').replace('ú', 'u').replace('ê', 'e')
        cols_novas.append(col)
    df.columns = cols_novas

    col_saldo = None
    col_salario = None
    col_municipio = None
    col_secao = None
    
    for col in df.columns:
        if col == 'saldomovimentacao': col_saldo = col
        elif 'saldo' in col and not col_saldo: col_saldo = col
        
        if col == 'salariomovimentacao': col_salario = col
        elif 'salario' in col and not col_salario: col_salario = col
        
        if 'municipio' in col and not col_municipio: col_municipio = col
        if 'secao' in col and not col_secao: col_secao = col

    rename_map = {}
    if col_saldo: rename_map[col_saldo] = 'saldomovimentacao'
    if col_salario: rename_map[col_salario] = 'salariomovimentacao'
    if col_municipio: rename_map[col_municipio] = 'municipio'
    if col_secao: rename_map[col_secao] = 'secao'
    
    df.rename(columns=rename_map, inplace=True)

    if 'saldomovimentacao' in df.columns:
        df['saldomovimentacao'] = pd.to_numeric(df['saldomovimentacao'], errors='coerce').fillna(0)
    
    if 'salariomovimentacao' in df.columns:
        if isinstance(df['salariomovimentacao'], pd.DataFrame):
            df['salariomovimentacao'] = df['salariomovimentacao'].iloc[:, 0]
            
        df['salariomovimentacao'] = df['salariomovimentacao'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['salariomovimentacao'] = pd.to_numeric(df['salariomovimentacao'], errors='coerce').fillna(0)
        
    return df

# --- CARREGAR DADOS ---
def carregar_historico(ano_fim, mes_fim):
    dfs = []
    data_ref = datetime.date(ano_fim, mes_fim, 1)
    status_text = st.sidebar.empty()
    bar = st.sidebar.progress(0)
    erros_log = []
    
    for i in range(3):
        dt = data_ref - relativedelta(months=i)
        status_text.text(f"📥 Baixando: {dt.month}/{dt.year}...")
        try:
            df_temp = baixar_e_processar_caged(dt.year, dt.month)
            if df_temp is not None and not df_temp.empty:
                df_temp = normalizar_colunas(df_temp)
                df_temp['data_ordem'] = pd.to_datetime(dt)
                dfs.append(df_temp)
            else:
                erros_log.append(f"{dt.month}/{dt.year}: Arquivo vazio/não encontrado.")
        except Exception as e:
            erros_log.append(f"{dt.month}/{dt.year}: Erro técnico - {str(e)}")
        bar.progress((i + 1) * 33)
        
    status_text.empty()
    bar.empty()
    
    if dfs:
        return pd.concat(dfs, ignore_index=True), erros_log
    return None, erros_log

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135679.png", width=40)
    st.title("Parâmetros")
    col1, col2 = st.columns(2)
    ano_sel = col1.selectbox("Ano", [2025, 2024, 2023])
    mes_sel = col2.selectbox("Mês", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    
    if st.button("Carregar Dados Oficiais"):
        with st.spinner("Processando..."):
            df_hist, erros = carregar_historico(ano_sel, mes_sel)
            if df_hist is not None:
                st.session_state['dados_full'] = df_hist
                st.success("Dados carregados!")
                if erros:
                    with st.expander("⚠️ Alertas"):
                        for e in erros: st.write(e)
            else:
                st.error("Dados não encontrados.")
                with st.expander("🛠️ Detalhes (Debug)"):
                    for e in erros: st.write(e)

# --- DASHBOARD ---
if 'dados_full' not in st.session_state:
    st.warning("👈 Clique no botão lateral para iniciar.")
    st.stop()

df_full = st.session_state['dados_full']

# Mapeamentos e Filtros
if 'saldomovimentacao' not in df_full.columns:
    st.error("Erro: Coluna de saldo não identificada.")
    st.stop()

col_mun = 'municipio' if 'municipio' in df_full.columns else df_full.columns[0]
df_full['Cidade'] = df_full[col_mun].astype(str).map(MAPA_MUNICIPIOS).fillna(df_full[col_mun].astype(str))
col_sec = 'secao' if 'secao' in df_full.columns else 'seção'
df_full['Setor'] = df_full[col_sec].astype(str).map(MAPA_CNAE).fillna("Outros")

st.title(f"🧭 Bússola Econômica - {mes_sel}/{ano_sel}")

cidades_disp = sorted(df_full['Cidade'].unique())
idx_padrao = cidades_disp.index('Canoas (RS)') if 'Canoas (RS)' in cidades_disp else 0
sel_cidade = st.selectbox("Analise o cenário de:", cidades_disp, index=idx_padrao)

df_city_full = df_full[df_full['Cidade'] == sel_cidade]
mes_atual_dt = pd.to_datetime(datetime.date(ano_sel, mes_sel, 1))
df_mes = df_city_full[df_city_full['data_ordem'] == mes_atual_dt]

# KPIs
total, admissoes, desligamentos, saldo = 0, 0, 0, 0
top_setor, nome_pag, valor_pag = "-", "-", 0

if not df_mes.empty:
    total = len(df_mes)
    admissoes = len(df_mes[df_mes['saldomovimentacao'] == 1])
    desligamentos = len(df_mes[df_mes['saldomovimentacao'] == -1])
    saldo = admissoes - desligamentos
    
    if admissoes > 0:
        top_setor = df_mes[df_mes['saldomovimentacao'] == 1]['Setor'].value_counts().idxmax()
        
    df_sal = df_mes[(df_mes['saldomovimentacao'] == 1) & (df_mes['salariomovimentacao'] > 0)]
    if not df_sal.empty:
        rank = df_sal.groupby('Setor')['salariomovimentacao'].mean().sort_values(ascending=False)
        nome_pag = rank.index[0]
        valor_pag = rank.iloc[0]

# --- FORMATADOR BR (Para o Texto de Resumo) ---
def formatar_moeda_br(valor):
    # Formata como 3,000.00 primeiro (Padrão US)
    s = f"{valor:,.2f}"
    # Inverte os caracteres: vírgula vira X, ponto vira vírgula, X vira ponto
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

texto_saldo = "Positivo 🟢" if saldo > 0 else "Negativo 🔴"
valor_formatado = formatar_moeda_br(valor_pag)

st.markdown(f"""
<div class="resumo-box">
    <b>Resumo ({mes_sel}/{ano_sel}):</b> Saldo de <b>{saldo}</b> vagas ({texto_saldo}).<br>
    🏆 <b>Líder contratações:</b> {top_setor}<br>
    💎 <b>Maior salário inicial:</b> {nome_pag} (R$ {valor_formatado})
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Movimentação", total)
c2.metric("Admissões", admissoes, delta="Entradas")
c3.metric("Desligamentos", desligamentos, delta="-Saídas", delta_color="inverse")
c4.metric("Saldo Líquido", saldo, delta="Vagas Reais")

st.markdown("---")
col_L, col_R = st.columns([2, 1])

with col_L:
    st.subheader("Volume por Setor")
    if not df_mes.empty and admissoes > 0:
        d = df_mes[df_mes['saldomovimentacao'] == 1]['Setor'].value_counts().reset_index().head(8)
        d.columns = ['Setor', 'Qtd']
        fig = px.bar(d, x='Qtd', y='Setor', orientation='h', text_auto=True, color='Qtd', color_continuous_scale='Teal')
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', font_color="#F8FAFC")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")

with col_R:
    st.subheader("Perfil")
    if not df_mes.empty and 'sexo' in df_mes.columns and admissoes > 0:
        df_mes['Gênero'] = df_mes['sexo'].astype(str).map(MAPA_SEXO).fillna("Outros")
        d = df_mes[df_mes['saldomovimentacao'] == 1]['Gênero'].value_counts().reset_index()
        d.columns = ['Gênero', 'Qtd']
        fig = px.pie(d, values='Qtd', names='Gênero', hole=0.6, color_discrete_sequence=['#38BDF8', '#F472B6'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_color="#F8FAFC")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader("📈 Tendência & Renda")
t1, t2 = st.tabs(["Evolução", "Salários"])

with t1:
    if not df_city_full.empty:
        evo = df_city_full.groupby('data_ordem')['saldomovimentacao'].sum().reset_index()
        evo['data_ordem'] = pd.to_datetime(evo['data_ordem'])
        evo['Mês'] = evo['data_ordem'].dt.strftime('%m/%Y')
        fig = px.line(evo, x='Mês', y='saldomovimentacao', markers=True)
        fig.update_traces(line_color='#38BDF8', line_width=4)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_color="#F8FAFC", yaxis_gridcolor='#334155')
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if not df_mes.empty and 'salariomovimentacao' in df_mes.columns:
        df_s = df_mes[(df_mes['saldomovimentacao'] == 1) & (df_mes['salariomovimentacao'] > 0)]
        if not df_s.empty:
            top = df_s.groupby('Setor')['salariomovimentacao'].mean().sort_values().tail(10).reset_index()
            
            # --- FORMATAÇÃO BRASILEIRA NO GRÁFICO ---
            # Cria uma coluna de texto (label) personalizada
            top['label_br'] = top['salariomovimentacao'].apply(lambda x: f"R$ {x:.2f}".replace('.', ','))
            
            # Usa 'text' apontando para essa coluna nova
            fig = px.bar(top, x='salariomovimentacao', y='Setor', orientation='h', 
                         text='label_br',  # Aqui está o segredo
                         color='salariomovimentacao', color_continuous_scale='Viridis')
            
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_color="#F8FAFC")
            st.plotly_chart(fig, use_container_width=True)
        else: st.warning("Sem dados salariais válidos.")