import streamlit as st
import pandas as pd
from src.sidebar.main import sidebar
from src.components.prompt_maker import render_prompt_maker

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sherlock",
    page_icon=":material/owl:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/sdushantha/sherlock/issues"
    }
)


# ---------------------------------------------------------
# 5. APLICAÇÃO PRINCIPAL (MAIN)
# ---------------------------------------------------------
def main():
    st.title(":material/owl: Sherlock Playground")
    
    config = sidebar()
    
    tab_playground, tab_prompt_maker = st.tabs([
        ":material/sports_esports: Área de Testes (Playground)", 
        ":material/edit_document: Prompt Maker"
    ])
    
    with tab_playground:
        st.write("### Área de Testes do Agente")
 
        if "dados_upload" in st.session_state:
            st.write("#### Base de Dados em uso:")
            st.dataframe(st.session_state["dados_upload"], use_container_width=True)

    with tab_prompt_maker:
        render_prompt_maker()

if __name__ == "__main__":
    main()