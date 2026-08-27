import streamlit as st
import pandas as pd
import json


@st.dialog("Assistente de Criação de Prompt 🤖", width="large")
def modal_gerar_prompt():
    st.write("Converse com a IA para estruturar seu System Prompt.")
    
    # Toggle para usar o prompt atual como contexto
    usar_contexto = st.toggle("Usar texto atual do System Prompt como base", value=True)
    
    if usar_contexto and st.session_state.get('system_prompt', '') != "":
        st.info("O prompt atual será enviado como contexto para a IA.")

    # Resgatando Inputs e Outputs das sessões anteriores
    inputs_ativos = st.session_state.get('colunas_ativas', [])
    outputs_ativos = st.session_state.get('colunas_output_ativas', [])
    
    # Construindo o Schema JSON obrigatório com base nas configurações de Output
    schema_dict = {}
    for i, col_name in enumerate(outputs_ativos):
        nome = st.session_state.get(f'out_name_{i}', col_name)
        tipo = st.session_state.get(f'out_type_{i}', 'StringType')
        desc = st.session_state.get(f'out_desc_{i}', 'Sem descrição')
        
        schema_dict[nome] = {
            "type": tipo,
            "description": desc
        }
    
    schema_json_str = json.dumps(schema_dict, indent=4, ensure_ascii=False)

    with st.expander("Ver Schema JSON e Inputs que serão enviados ao Agente"):
        st.write("**Colunas de Entrada Disponíveis:**", inputs_ativos)
        st.write("**Schema JSON Obrigatório de Saída:**")
        st.code(schema_json_str, language='json')

    # ==========================================
    # 1. CONTAINER PARA AS MENSAGENS (FICA ACIMA)
    # ==========================================
    # Altura fixa ajuda a criar uma barra de rolagem se a conversa ficar longa
    chat_area = st.container(height=400, border=False)

    # ==========================================
    # 2. INPUT DO USUÁRIO (FICA ABAIXO DO CONTAINER)
    # ==========================================
    pedido_usuario = st.chat_input("Ex: Crie um prompt para classificar o nível de irritação do cliente...")

    # ==========================================
    # 3. LÓGICA DE ESTADO E GERAÇÃO
    # ==========================================
    # Inicializa variáveis temporárias para segurar a conversa sem sumir ao clicar no botão
    if "msg_usuario_temp" not in st.session_state:
        st.session_state["msg_usuario_temp"] = None
    if "prompt_gerado_temp" not in st.session_state:
        st.session_state["prompt_gerado_temp"] = None

    if pedido_usuario:
        st.session_state["msg_usuario_temp"] = pedido_usuario
        
        texto_base = st.session_state.get('system_prompt', '') if usar_contexto else ""
        
        st.session_state["prompt_gerado_temp"] = f"""Você é um analista especialista em qualidade de atendimento.
                                                    Seu objetivo é analisar as transcrições fornecidas e extrair dados de forma precisa.

                                                    Contexto adicional: {texto_base if texto_base else 'Nenhum contexto extra fornecido.'}

                                                    Instruções:
                                                    1. Leia as seguintes colunas de entrada fornecidas no dataset: {', '.join(inputs_ativos)}.
                                                    2. Extraia os dados e retorne EXATAMENTE no formato JSON abaixo, seguindo os tipos estritos (Spark Types).

                                                    SCHEMA OBRIGATÓRIO (MANDATORY JSON):

                                                    {schema_json_str}
                                                    

                                                    Não inclua nenhum texto antes ou depois do JSON. Retorne apenas o JSON validado."""


    with chat_area:
        if st.session_state["msg_usuario_temp"]:
            # Exibe a mensagem do usuário
            st.chat_message("user").write(st.session_state["msg_usuario_temp"])
            
            # Exibe a resposta da IA
            with st.chat_message("assistant"):
                st.markdown(st.session_state["prompt_gerado_temp"])
                
                # Botão para aplicar
                if st.button("Aplicar este Prompt", icon=":material/check:", type="primary"):
                    # Atualiza o campo de texto principal
                    st.session_state['text_area_prompt'] = st.session_state["prompt_gerado_temp"]
                    st.session_state['system_prompt'] = st.session_state["prompt_gerado_temp"]
                    
                    # Limpa o chat do modal para a próxima vez que ele for aberto
                    st.session_state["msg_usuario_temp"] = None
                    st.session_state["prompt_gerado_temp"] = None
                    
                    st.rerun() # Fecha o modal e atualiza a interface de fundo


@st.dialog("Galeria de Templates de Prompt 📚")
def modal_templates():
    st.write("Selecione um template pré-configurado para carregar no campo principal.")
    
    # Lista simulada de templates
    templates = [
        {
            "titulo": "Extração de Motivo e Sentimento",
            "texto": "Atue como um analista de call center. Leia a transcrição da chamada e identifique o motivo principal do contato e o sentimento final do cliente. Retorne estritamente o JSON configurado no schema."
        },
        {
            "titulo": "Identificação de Risco de Churn (Cancelamento)",
            "texto": "Analise o texto fornecido e identifique sinais de insatisfação que indiquem possível quebra de contrato ou cancelamento. Siga o schema JSON definido para organizar a saída."
        },
        {
            "titulo": "Sumarização Executiva",
            "texto": "Leia a conversa entre o atendente e o cliente. Faça um resumo em no máximo 3 frases focando no problema reportado e na solução dada. Retorne os dados formatados no JSON exigido."
        }
    ]
    
    # Criando os cards da galeria
    for tpl in templates:
        with st.container(border=True):
            col_txt, col_btn = st.columns([6, 1], vertical_alignment="center")
            with col_txt:
                st.subheader(tpl["titulo"])
                st.write(tpl["texto"])
            with col_btn:
                # Botão alterado para usar apenas o ícone material/add
                if st.button(label="", icon=":material/add:", key=f"btn_{tpl['titulo']}", help="Usar este template"):
                    # O segredo para o text_area atualizar é sobrescrever diretamente a 'key' dele no session_state
                    st.session_state['text_area_prompt'] = tpl["texto"]
                    st.session_state['system_prompt'] = tpl["texto"]
                    st.rerun()

@st.dialog("Editar Prompt Manualmente ✏️", width="large")
def modal_editar_manual():
    st.write("Edite livremente as instruções do seu System Prompt.")
    
    # Text area dentro do modal carregando o valor atual
    prompt_atualizado = st.text_area(
        label="Conteúdo do Prompt",
        value=st.session_state.get('system_prompt', ''),
        height=400,
        placeholder="Escreva sua instrução principal aqui..."
    )
    
    # Botão para salvar e fechar o modal
    if st.button("Salvar Alterações", type="primary", icon=":material/save:"):
        st.session_state['system_prompt'] = prompt_atualizado
        st.rerun()

def aba_system_prompt():
    st.header("Configuração do System Prompt")
    st.write("Defina a instrução principal (System Prompt) que guiará o modelo de linguagem.")

    # Inicializa o prompt no session_state se não existir
    if 'system_prompt' not in st.session_state:
        st.session_state['system_prompt'] = ""

    # Adicionado mais uma coluna para o botão de edição manual
    col_gen, col_tpl, col_edit, _ = st.columns([1.2, 1.2, 1.2, 2.4])

    with col_gen:
        if st.button("✨ Generate Prompt (IA)", use_container_width=True):
            modal_gerar_prompt()
            
    with col_tpl:
        if st.button("📚 Template Prompt", use_container_width=True):
            modal_templates()

    with col_edit:
        if st.button("✏️ Editar Manualmente", use_container_width=True):
            modal_editar_manual()

    st.divider()

    # Exibição do Preview ao invés do input aberto
    st.subheader("Preview do System Prompt", anchor=False)
    
    if st.session_state['system_prompt'].strip():
        # Exibe o prompt gerado no formato código/markdown
        st.code(st.session_state['system_prompt'], language="markdown")
    else:
        st.info("Nenhum prompt definido. Use os botões acima para gerar um template, pedir ajuda para a IA ou escrever manualmente.")

def inicializar_dados():
    # Verifica se os dados já existem no session_state para não recriá-los a cada recarregamento
    if "dados_upload" not in st.session_state:
        # Dados simulados de transcrições de call center
        dados_chamadas = {
            "id_chamada": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010],
            "data_hora": [
                "2026-08-26 09:15:00", "2026-08-26 09:30:22", "2026-08-26 10:05:10", 
                "2026-08-26 10:45:00", "2026-08-26 11:10:15", "2026-08-26 13:20:00", 
                "2026-08-26 14:05:30", "2026-08-26 15:30:45", "2026-08-26 16:15:20", 
                "2026-08-26 17:00:10"
            ],
            "motivo": [
                "Fatura Incorreta", "Suporte Técnico", "Upgrade de Plano", 
                "Cancelamento", "Mudança de Endereço", "Dúvida - Pontos", 
                "Reset de Senha", "Reclamação - Atraso", "Confirmação de Pagamento", 
                "Ativação de Serviço"
            ],
            "sentimento_cliente": [
                "Irritado", "Frustrado", "Positivo", "Insatisfeito", "Neutro", 
                "Positivo", "Neutro", "Muito Irritado", "Neutro", "Positivo"
            ],
            "transcricao": [
                "Atendente: Olá, como posso ajudar? | Cliente: Minha fatura veio com valor dobrado! | Atendente: Peço desculpas, vou verificar. Vi aqui que houve um erro de sistema, já fiz o estorno. | Cliente: Ok, obrigado.",
                "Atendente: Suporte técnico, bom dia. | Cliente: Minha internet caiu desde ontem. | Atendente: Vou reiniciar seu sinal por aqui. Voltou? | Cliente: Sim, agora acenderam as luzes. Obrigado.",
                "Atendente: Central de vendas. | Cliente: Quero aumentar a velocidade da minha internet. | Atendente: Temos um plano de 500 Mega por mais R$20 mensais, aceita? | Cliente: Sim, pode alterar.",
                "Atendente: Setor de retenção. | Cliente: Quero cancelar meu plano, está muito caro. | Atendente: Posso oferecer 30% de desconto por 12 meses para o senhor ficar. | Cliente: Sendo assim, eu aceito.",
                "Atendente: Bom dia. | Cliente: Preciso alterar o endereço de cobrança. | Atendente: Claro, me informe o novo CEP, por favor. | Cliente: É 01001-000. | Atendente: Atualizado com sucesso.",
                "Atendente: Programa de fidelidade. | Cliente: Quantos pontos eu tenho? | Atendente: O senhor tem 5.000 pontos que vencem mês que vem. | Cliente: Ótimo, vou trocar por um resgate no site.",
                "Atendente: Suporte. | Cliente: Esqueci a senha do aplicativo. | Atendente: Enviei um link de recuperação para o seu e-mail cadastrado. | Cliente: Chegou aqui, consegui acessar.",
                "Atendente: Agendamento. | Cliente: O técnico deveria ter chegado às 9h e não apareceu. | Atendente: Tivemos um imprevisto na rota, ele chegará em 30 minutos. | Cliente: Um absurdo, mas vou aguardar.",
                "Atendente: Financeiro. | Cliente: Paguei a conta ontem, já constou? | Atendente: Sim, o pagamento de R$ 150 já está baixado no sistema. | Cliente: Perfeito, era só isso.",
                "Atendente: Atendimento. | Cliente: Vou viajar para fora e preciso de roaming. | Atendente: Ativei o pacote Américas no seu número, válido por 7 dias. | Cliente: Muito obrigado pela rapidez."
            ]
        }
        
        # Salvando o DataFrame no session_state
        st.session_state['dados_upload'] = pd.DataFrame(dados_chamadas)


def input_data():
    if "dados_upload" in st.session_state and st.session_state['dados_upload'] is not None:
        df = st.session_state['dados_upload']
        colunas_originais = df.columns.tolist()
        
        # 1. Inicializa a lista de colunas ativas no session_state
        if 'colunas_ativas' not in st.session_state:
            st.session_state['colunas_ativas'] = colunas_originais.copy()

        # 2. Callback para quando o usuário alterar o Multiselect manualmente
        def sync_multiselect():
            st.session_state['colunas_ativas'] = st.session_state['seletor_colunas']

        # Envelopando tudo no Expander
        with st.expander("Gerenciar Colunas de Input", expanded=True,icon=':material/build:'):
            
            # 3. Multiselect amarrado ao session_state e ao callback
            st.multiselect(
                label="Colunas de Input Disponíveis",
                options=list(set(colunas_originais + st.session_state['colunas_ativas'])), 
                default=st.session_state['colunas_ativas'],
                key="seletor_colunas",
                on_change=sync_multiselect
            )

            # Botão global para adicionar uma coluna totalmente nova
            if st.button(label='Adicionar Nova Coluna', icon=':material/add:'):
                nova_col = f"Nova_Coluna_{len(st.session_state['colunas_ativas']) + 1}"
                if nova_col not in st.session_state['colunas_ativas']:
                    st.session_state['colunas_ativas'].append(nova_col)
                    st.rerun() # Atualiza a tela imediatamente

            st.divider() # Linha divisória visual

            colunas_para_remover = []

            # 4. Loop renderizando os campos
            for i, col_name in enumerate(st.session_state['colunas_ativas']):
                # Proporção 11 para inputs, 1 para a lixeira. Alinhamento por baixo.
                col_inputs, col_trash = st.columns([11, 1], vertical_alignment="bottom")
                
                with col_inputs:
                    # Usamos o nome da coluna no key para evitar erros de renderização
                    input_name = st.text_input(
                        label=f'Nome da Coluna:', 
                        value=col_name, 
                        key=f'name_{col_name}_{i}'
                    )
                    input_desc = st.text_area(
                        label='Descrição da coluna:', 
                        key=f'desc_{col_name}_{i}',
                        height=68 # Mantém o text area compacto
                    )
                    
                with col_trash:
                    # Botão de deletar individual
                    if st.button(label='', icon=':material/delete:', key=f'trash_{col_name}_{i}', help=f"Remover {col_name}"):
                        colunas_para_remover.append(col_name)
                
                st.markdown("---") # Linha divisória entre as colunas

            # 5. Lógica de remoção executada fora do loop
            if colunas_para_remover:
                for c in colunas_para_remover:
                    st.session_state['colunas_ativas'].remove(c)
                st.rerun()


def output_column():
    # 1. Inicializa a lista de colunas de output no session_state
    if 'colunas_output_ativas' not in st.session_state:
        # Começa com uma coluna padrão de exemplo
        st.session_state['colunas_output_ativas'] = ["Output_1"]

    # Opções fixas para o selectbox de tipo de dado
    tipos_de_dados = [
        "StringType", 
        "IntegerType", 
        "FloatType", 
        "DoubleType", 
        "BooleanType", 
        "DateType", 
        "TimestampType",
        "ArrayType"
    ]

    # Envelopando tudo no Expander
    with st.expander("Configurar Colunas de Output", expanded=True, icon=':material/add_column_right:'):
        
        # Botão para adicionar uma nova coluna de output
        if st.button(label='Adicionar Novo Output', icon=':material/add:', key='btn_add_output'):
            novo_output = f"Novo_Output_{len(st.session_state['colunas_output_ativas']) + 1}"
            st.session_state['colunas_output_ativas'].append(novo_output)
            st.rerun() # Atualiza a tela imediatamente

        st.divider() # Linha divisória visual

        outputs_para_remover = []

        # 2. Loop renderizando os campos de output
        for i, col_name in enumerate(st.session_state['colunas_output_ativas']):
            # Proporção 11 para inputs, 1 para a lixeira
            col_inputs, col_trash = st.columns([11, 1], vertical_alignment="bottom")
            
            with col_inputs:
                # Subdividindo a área de inputs para colocar Nome e Tipo lado a lado
                col_nome, col_tipo = st.columns([2, 1])
                
                with col_nome:
                    st.text_input(
                        label='Nome da Coluna:', 
                        value=col_name, 
                        key=f'out_name_{i}'
                    )
                with col_tipo:
                    st.selectbox(
                        label='Tipo de Dado:',
                        options=tipos_de_dados,
                        key=f'out_type_{i}'
                    )
                
                # Regra da coluna ocupando toda a largura do bloco de inputs
                st.text_area(
                    label='Regra da Coluna (Instrução/Prompt):', 
                    placeholder="Ex: Classifique o sentimento como Positivo, Negativo ou Neutro...",
                    key=f'out_desc_{i}',
                    height=68 
                )
                
            with col_trash:
                # Botão de deletar individual
                if st.button(label='', icon=':material/delete:', key=f'trash_out_{i}', help="Remover Output"):
                    outputs_para_remover.append(col_name)
            
            st.markdown("---") # Linha divisória entre os blocos

        # 3. Lógica de remoção executada fora do loop
        if outputs_para_remover:
            for c in outputs_para_remover:
                st.session_state['colunas_output_ativas'].remove(c)
            st.rerun() # Recarrega a página para atualizar os componentes




def main():
    st.set_page_config(page_title="Análise de Atendimento", layout="wide")
    st.title("Sistema de Análise de Transcrições")
    
    inicializar_dados()
    input,output,system_prompt = st.tabs(["1. Inputs", "2. Outputs", "3. System Prompt"])
    with input:
        input_data()
    with output:
        output_column()
    with system_prompt:
        aba_system_prompt()

if __name__ == "__main__":
    main()