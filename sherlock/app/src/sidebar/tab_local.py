import streamlit as st

@st.dialog("Upload de Arquivo", icon=":material/upload:")
def modal_upload_file():
    # O widget de upload
    uploaded_file = st.file_uploader(
        "Escolha um arquivo CSV ou Excel", 
        type=["csv", "xlsx", "xls"], 
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        st.success(f"Arquivo `{uploaded_file.name}` carregado com sucesso!")
        
        # Bloco try-except para evitar quebra caso o arquivo esteja corrompido
        try:
            # Verifica a extensão para usar o método correto do pandas
            if uploaded_file.name.endswith('.csv'):
                # Lê como CSV
                df = pd.read_csv(uploaded_file)
            else:
                # Lê como Excel
                df = pd.read_excel(uploaded_file)
            
            # Mostra o preview dos dados (apenas as 5 primeiras linhas para não poluir o modal)
            st.write("**Preview dos Dados:**")
            st.dataframe(df.head(), use_container_width=True)
            
            # Botão de concluir
            if st.button("Concluir", type="primary", use_container_width=True):
                # Salva o dataframe no session_state para usar fora do modal
                st.session_state["dados_upload"] = df
                
                # st.rerun() fecha o modal e recarrega a página principal com os novos dados
                st.rerun() 
                
        except Exception as e:
            st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
            
    else:
        st.info("Aguardando o upload do arquivo...")