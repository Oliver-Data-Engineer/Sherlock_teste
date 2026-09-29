import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 2. MODAL DE UPLOAD
# ---------------------------------------------------------
@st.dialog("Upload de Arquivo", icon=":material/upload:")
def modal_upload_file():
    uploaded_file = st.file_uploader("Escolha um arquivo CSV ou Excel", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"Arquivo `{uploaded_file.name}` lido com sucesso!")
            st.dataframe(df.head(3), use_container_width=True)
            
            if st.button("Concluir", type="primary", use_container_width=True):
                st.session_state["dados_upload"] = df
                st.rerun() 
                
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")

# ---------------------------------------------------------
# 3. SIDEBAR
# ---------------------------------------------------------
def sidebar():
    st.sidebar.title("⚙️ Configurações")
    st.sidebar.markdown("Ajuste os parâmetros do Sherlock abaixo:")

    with st.sidebar.expander("🧠 System Prompt (Agente)", expanded=False):
        prompt_padrao = (
            "Você é um assistente Responsável por fazer a classificação de ligações..."
        )
        system_prompt = st.text_area("Instruções do Agente", value=prompt_padrao, height=150)

    st.sidebar.subheader("📂 Fonte de Dados")
    tab_local, tab_cloud = st.sidebar.tabs(["🏠 Local", "☁️ Cloud"])

    with tab_local:
        st.info("O modo local permite testar com arquivos locais sem consultar o Athena ou S3.")
        if st.button("Fazer Upload de Arquivo", type="secondary", use_container_width=True):
            modal_upload_file()

        if "dados_upload" in st.session_state:
            st.success("Arquivo pronto para uso!")
            st.dataframe(st.session_state["dados_upload"].head(2), use_container_width=True)

    with tab_cloud:
        st.info("Conecte seu agente diretamente aos dados na Nuvem.")
        
    return {
        "system_prompt": system_prompt
    }