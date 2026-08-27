import streamlit as st


# ---------------------------------------------------------
# 4. FUNÇÃO DO PROMPT MAKER
# ---------------------------------------------------------
def render_prompt_maker():
    st.markdown("### 🛠️ Construtor de System Prompt")
    st.markdown("Preencha as seções abaixo para estruturar o comportamento da sua IA classificadora.")
    
    # Inicializa as listas dinâmicas no st.session_state se não existirem
    if "pm_guardrails" not in st.session_state:
        st.session_state.pm_guardrails = ["Nunca invente dados que não existam no contexto fornecido."]
    if "pm_fewshots" not in st.session_state:
        st.session_state.pm_fewshots = [{"user": "Exemplo de entrada", "assistant": "Saída esperada"}]
    if "pm_input_cols" not in st.session_state:
        st.session_state.pm_input_cols = [{"name": "transcricao_audio", "context": "Texto extraído da fala do cliente com o atendente."}]
    if "pm_output_cols" not in st.session_state:
        st.session_state.pm_output_cols = [{"name": "categoria", "rule": "Preencher apenas com: A, B, C, D ou E"}]

    # --- LINHA 1: Role & Task ---
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("1. Papel ou Persona (Role)", expanded=True):
            st.caption("Defina exatamente quem a IA deve ser.")
            role = st.text_area("Persona", "Você é um classificador de dados especialista em analisar transcrições de atendimento.", height=80)
    with col2:
        with st.expander("2. Objetivo Principal (Task)", expanded=True):
            st.caption("Qual é o trabalho exato que o modelo deve executar.")
            task = st.text_area("Tarefa", "Sua tarefa é analisar os dados de entrada e categorizá-los rigorosamente conforme as regras estabelecidas.", height=80)

    # --- LINHA 2: Contexto & Input Data ---
    col3, col4 = st.columns(2)
    with col3:
        with st.expander("3. Contexto Global (Context)", expanded=False):
            st.caption("Informações base ou definições gerais do negócio.")
            context = st.text_area("Contexto", "Você receberá linhas de um dataset. Analise o contexto de cada linha antes de classificar.", height=150)
    with col4:
        with st.expander("4. Colunas de Entrada (Input Data)", expanded=False):
            st.caption("Quais colunas a IA vai ler e o que cada uma significa?")
            
            # --- Nova lógica de Importação via Toggle ---
            if "dados_upload" in st.session_state:
                import_toggle = st.toggle("Importar colunas do database carregado")
                
                if import_toggle:
                    df_cols = st.session_state["dados_upload"].columns.tolist()
                    colunas_selecionadas = st.multiselect("Selecione as colunas para importar:", options=df_cols)
                    
                    if st.button("📥 Importar", type="primary"):
                        existing_names = [c["name"] for c in st.session_state.pm_input_cols]
                        for col_name in colunas_selecionadas:
                            if col_name not in existing_names:
                                st.session_state.pm_input_cols.append({"name": col_name, "context": ""})
                        st.rerun()
                st.divider()
            # ---------------------------------------------

            # Lista dinâmica de inputs e contextos
            for i, in_col in enumerate(st.session_state.pm_input_cols):
                st.markdown(f"**Input {i+1}**")
                st.session_state.pm_input_cols[i]["name"] = st.text_input("Nome da Coluna", value=in_col["name"], key=f"in_name_{i}")
                st.session_state.pm_input_cols[i]["context"] = st.text_area("Descrição / Contexto da coluna", value=in_col["context"], key=f"in_ctx_{i}", height=68)
                
                if st.button("🗑️ Remover Input", key=f"del_in_{i}"):
                    st.session_state.pm_input_cols.pop(i)
                    st.rerun()
                st.divider()

            if st.button("➕ Adicionar Coluna de Entrada Manualmente", type="secondary"):
                st.session_state.pm_input_cols.append({"name": "", "context": ""})
                st.rerun()

    # --- LINHA 3: Output Columns & Output Format ---
    col5, col6 = st.columns(2)
    with col5:
        with st.expander("5. Regras das Colunas de Saída (Output Cols)", expanded=False):
            st.caption("Defina as colunas que a IA deve gerar e a regra para cada uma.")
            
            for i, out_col in enumerate(st.session_state.pm_output_cols):
                st.markdown(f"**Coluna {i+1}**")
                st.session_state.pm_output_cols[i]["name"] = st.text_input("Nome da Coluna", value=out_col["name"], key=f"out_name_{i}")
                st.session_state.pm_output_cols[i]["rule"] = st.text_area("Regra de Preenchimento", value=out_col["rule"], key=f"out_rule_{i}", height=68)
                
                if st.button("🗑️ Remover Coluna", key=f"del_out_{i}"):
                    st.session_state.pm_output_cols.pop(i)
                    st.rerun()
                st.divider()

            if st.button("➕ Adicionar Coluna de Saída", type="secondary"):
                st.session_state.pm_output_cols.append({"name": "", "rule": ""})
                st.rerun()

    with col6:
        with st.expander("6. Formato de Saída Global (Output Format)", expanded=False):
            st.caption("Como a IA deve estruturar a resposta final (Ex: JSON, CSV).")
            output_format = st.text_area("Formato", "Retorne o resultado estritamente em formato JSON, utilizando as colunas de saída definidas como chaves.", height=150)

    # --- LINHA 4: Guardrails & Few-Shot ---
    col7, col8 = st.columns(2)
    with col7:
        with st.expander("7. Restrições e Barreiras (Guardrails)", expanded=False):
            st.caption("O que o modelo **NÃO** deve fazer em hipótese alguma.")
            
            for i, gr in enumerate(st.session_state.pm_guardrails):
                c_input, c_btn = st.columns([8, 1])
                with c_input:
                    st.session_state.pm_guardrails[i] = st.text_input(f"Regra {i+1}", value=gr, key=f"gr_{i}", label_visibility="collapsed")
                with c_btn:
                    if st.button("🗑️", key=f"del_gr_{i}", help="Remover"):
                        st.session_state.pm_guardrails.pop(i)
                        st.rerun()
            
            if st.button("➕ Adicionar Regra", type="secondary"):
                st.session_state.pm_guardrails.append("")
                st.rerun()

    with col8:
        with st.expander("8. Exemplos (Few-Shot Prompting)", expanded=False):
            st.caption("Exemplos de entrada e saída aumentam muito a precisão.")
            
            for i, fs in enumerate(st.session_state.pm_fewshots):
                st.markdown(f"**Exemplo {i+1}**")
                st.session_state.pm_fewshots[i]["user"] = st.text_input("Entrada (User)", value=fs["user"], key=f"fs_u_{i}")
                st.session_state.pm_fewshots[i]["assistant"] = st.text_area("Saída Esperada (Assistant)", value=fs["assistant"], key=f"fs_a_{i}", height=68)
                
                if st.button("🗑️ Remover Exemplo", key=f"del_fs_{i}"):
                    st.session_state.pm_fewshots.pop(i)
                    st.rerun()
                st.divider()

            if st.button("➕ Adicionar Exemplo", type="secondary"):
                st.session_state.pm_fewshots.append({"user": "", "assistant": ""})
                st.rerun()

    # --- LIVE PREVIEW (LARGURA TOTAL) ---
    st.divider()
    st.subheader("👁️ Live Preview do System Prompt")
    
    # --- Montagem Dinâmica do Markdown ---
    prompt_final = f"**{role}**\n\n"
    prompt_final += f"**OBJETIVO DA TAREFA:**\n{task}\n\n"
    
    if context.strip():
        prompt_final += f"**CONTEXTO GERAL:**\n{context}\n\n"
    
    # Montagem das Colunas de Entrada (Input Data com Contexto)
    valid_in_cols = [c for c in st.session_state.pm_input_cols if c["name"].strip()]
    if valid_in_cols:
        prompt_final += "**DADOS DE ENTRADA (INPUTS E SEUS CONTEXTOS):**\n"
        prompt_final += "Você receberá os seguintes dados. Entenda o contexto de cada um deles:\n"
        for c in valid_in_cols:
            ctx = f" - {c['context']}" if c['context'].strip() else ""
            prompt_final += f"- **{c['name']}**{ctx}\n"
        prompt_final += "\n"

    # Montagem das Colunas de Saída e Regras (Output Columns)
    valid_out_cols = [c for c in st.session_state.pm_output_cols if c["name"].strip()]
    if valid_out_cols:
        prompt_final += "**COLUNAS DE SAÍDA E REGRAS DE CLASSIFICAÇÃO:**\n"
        prompt_final += "Sua classificação deve gerar as seguintes colunas, respeitando estritamente suas regras:\n"
        for c in valid_out_cols:
            prompt_final += f"- **{c['name']}**: {c['rule']}\n"
        prompt_final += "\n"

    # Montagem das Restrições (Guardrails)
    valid_guardrails = [g for g in st.session_state.pm_guardrails if g.strip()]
    if valid_guardrails:
        prompt_final += "**RESTRIÇÕES (O QUE NÃO FAZER):**\n"
        for gr in valid_guardrails:
            prompt_final += f"- {gr}\n"
        prompt_final += "\n"
    
    # Formato de Saída (Output Format)
    if output_format.strip():
        prompt_final += f"**FORMATO DE SAÍDA EXIGIDO:**\n{output_format}\n\n"
    
    # Montagem dos Exemplos (Few-Shot)
    valid_fewshots = [fs for fs in st.session_state.pm_fewshots if fs["user"].strip() or fs["assistant"].strip()]
    if valid_fewshots:
        prompt_final += "**EXEMPLOS DE CLASSIFICAÇÃO (FEW-SHOT):**\n"
        for i, fs in enumerate(valid_fewshots):
            prompt_final += f"--- Exemplo {i+1} ---\n"
            prompt_final += f"Entrada:\n{fs['user']}\n"
            prompt_final += f"Saída Esperada:\n{fs['assistant']}\n\n"

    # Exibição
    st.info("Aqui está o resultado do seu prompt estruturado. Utilize o botão de copiar no canto superior direito do bloco.")
    st.code(prompt_final, language="markdown")