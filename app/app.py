import copy
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from Sherlock_teste.app.config_io import (
    ORIGIN_FIELDS, SCHEMA, SCHEMA_BY_PATH, flatten, load_default_config,
    load_yaml_text, normalize_origin, to_yaml, unflatten, validate,
)
from Sherlock_teste.app.partitions import simulate

# ==========================================
# CONFIGURAÇÃO DE PATH E IMPORTAÇÃO
# ==========================================
APP_DIR = Path(__file__).resolve().parent
for p in (APP_DIR.parent, APP_DIR.parent.parent, Path().resolve().parent):
    if str(p) not in sys.path:
        sys.path.append(str(p))

try:
    from core.Datautils import Datautils as DT
    MODULO_CARREGADO = True
except ImportError:
    MODULO_CARREGADO = False

st.set_page_config(page_title="YGGDRA Pipeline Maker", page_icon=":material/account_tree:", layout="wide")

# ==========================================
# ETAPAS DA JORNADA (ordem de execução)
# ==========================================
STAGES = {
    "common": {
        "icon": ":material/tune:", "title": "Common", "step": "Base",
        "what": "Parâmetros compartilhados por todas as etapas: dono da pipeline, região AWS e nível de log.",
        "when": "Lido por Heimdall, Pipeline e Hermes.",
    },
    "heimdall": {
        "icon": ":material/shield:", "title": "Heimdall", "step": "1 · Pre-flight",
        "what": "Guardião. Valida se as tabelas de origem estão prontas e se o SQL é válido.",
        "when": "Roda ANTES do processamento. Se reprovar, BLOQUEIA a pipeline.",
        "off": "Desligado: a pipeline roda direto, sem checar origens nem SQL.",
    },
    "pipeline": {
        "icon": ":material/database:", "title": "Pipeline", "step": "2 · Processamento",
        "what": "Executa o SQL e grava na tabela destino, nas partições definidas pelas regras temporais.",
        "when": "Roda depois que o Heimdall aprovar.",
    },
    "data": {
        "icon": ":material/calendar_month:", "title": "Dados temporais", "step": "2 · Processamento",
        "what": "Define QUAIS partições são processadas: a padrão (hoje - lag), a janela de reprocessamento ou um backfill manual.",
        "when": "Prioridade: backfill > reprocess (no dia de corte) > partição padrão.",
    },
    "hermes": {
        "icon": ":material/mail:", "title": "Hermes", "step": "3 · Notificação",
        "what": "Envia por e-mail os relatórios gerados pelo Heimdall e pela Pipeline.",
        "when": "Roda no FINAL, conforme as regras de erro/sucesso de cada relatório.",
        "off": "Desligado: nenhum e-mail é enviado; os relatórios ficam só no arquivo temporário.",
    },
}


def stage_intro(key):
    s = STAGES[key]
    st.header(f"{s['icon']} {s['title']}")
    st.caption(s["step"])
    with st.container(border=True):
        st.markdown(f":material/info: **O que faz:** {s['what']}  \n:material/schedule: **Quando:** {s['when']}")


def section(icon, title, caption=None):
    st.subheader(f"{icon} {title}")
    if caption:
        st.caption(caption)


# ==========================================
# ESTADO DA SESSÃO
# Cada campo do YAML vira um widget com key "cfg:<caminho>".
# Origens manuais do Heimdall: lista de ids em "origin_ids", campos em "orig:<id>:<campo>".
# ==========================================
ORIGINS_PATH = "heimdall.origins.manual_mode.tables"


def K(path):
    return f"cfg:{path}"


def OK(oid, field):
    return f"orig:{oid}:{field}"


def _new_origin(values=None):
    st.session_state["origin_seq"] = st.session_state.get("origin_seq", 0) + 1
    oid = st.session_state["origin_seq"]
    for f, v in normalize_origin(values or {}).items():
        st.session_state[OK(oid, f)] = v
    st.session_state["origin_ids"].append(oid)
    return oid


def _remove_origin(oid):
    st.session_state["origin_ids"].remove(oid)
    for f, *_ in ORIGIN_FIELDS:
        st.session_state.pop(OK(oid, f), None)


def apply_config(cfg):
    flat, unknown = flatten(cfg)
    for path, value in flat.items():
        kind = SCHEMA_BY_PATH[path][1]
        if kind == "records":
            for oid in list(st.session_state.get("origin_ids", [])):
                _remove_origin(oid)
            st.session_state["origin_ids"] = []
            for item in value:
                _new_origin(item)
        elif kind == "optint":
            st.session_state[K(path) + "#on"] = value is not None
            st.session_state[K(path)] = value if value is not None else 1
        else:
            st.session_state[K(path)] = "\n".join(value) if kind == "list" else value
    st.session_state["unknown_keys"] = unknown
    st.session_state["execution_partitions"] = None


def current_config():
    flat = {}
    for path, kind, _, _ in SCHEMA:
        if kind == "records":
            v = [{f: st.session_state[OK(oid, f)] for f, *_ in ORIGIN_FIELDS} for oid in st.session_state["origin_ids"]]
        else:
            v = st.session_state[K(path)]
            if kind == "list":
                v = [line.strip() for line in v.splitlines() if line.strip()]
            elif kind == "optint" and not st.session_state[K(path) + "#on"]:
                v = None
        flat[path] = v
    return unflatten(flat)


def _on_upload():
    f = st.session_state.get("upload")
    if f is None:
        return
    try:
        apply_config(load_yaml_text(f.getvalue().decode("utf-8")))
        st.session_state["load_msg"] = ("success", f"'{f.name}' carregado.")
    except Exception as e:
        st.session_state["load_msg"] = ("error", f"Erro ao ler '{f.name}': {e}")


def _on_reset():
    apply_config(load_default_config())
    st.session_state["load_msg"] = ("success", "Configuração padrão (config.yaml) recarregada.")


def _scalar_keys():
    keys = [K(p) for p, kind, _, _ in SCHEMA if kind != "records"]
    keys += [K(p) + "#on" for p, kind, _, _ in SCHEMA if kind == "optint"]
    return keys


def _state_ok():
    """True se a sessão tem todas as chaves esperadas (falha em sessões criadas por versões antigas do app)."""
    ss = st.session_state
    if not isinstance(ss.get("origin_ids"), list):
        return False
    keys = _scalar_keys()
    keys += [OK(oid, f) for oid in ss["origin_ids"] for f, *_ in ORIGIN_FIELDS]
    return all(k in ss for k in keys)


if not _state_ok():
    st.session_state["origin_ids"] = []
    apply_config(load_default_config())

# Evita que o Streamlit descarte o valor de widgets ocultos (ex.: origens manuais quando mode=auto)
for _k in _scalar_keys() + [
    OK(oid, f) for oid in st.session_state["origin_ids"] for f, *_ in ORIGIN_FIELDS
]:
    st.session_state[_k] = st.session_state[_k]


# ==========================================
# HELPERS DE WIDGET
# ==========================================
def widget(kind, label, key, options=None, help=None, disabled=False):
    if kind == "str":
        return st.text_input(label, key=key, help=help, disabled=disabled)
    if kind == "int":
        return st.number_input(label, step=1, key=key, help=help, disabled=disabled)
    if kind == "bool":
        return st.toggle(label, key=key, help=help, disabled=disabled)
    if kind == "select":
        return st.selectbox(label, options=options, key=key, help=help, disabled=disabled)
    if kind == "date":
        return st.date_input(label, key=key, help=help, disabled=disabled, format="YYYY-MM-DD")
    if kind == "list":
        return st.text_area(label, key=key, help=(help or "") + " (um item por linha)", disabled=disabled, height=110)
    raise ValueError(kind)


def field(path, label, help=None, disabled=False):
    _, kind, _, options = SCHEMA_BY_PATH[path]
    return widget(kind, label, K(path), options, help, disabled)


def report_section(prefix, disabled=False):
    enabled = field(f"{prefix}.report.enabled", "Gerar relatório", disabled=disabled,
                    help="Gera um HTML temporário que o Hermes envia por e-mail")
    off = disabled or not enabled
    c1, c2 = st.columns([1, 3])
    with c1:
        field(f"{prefix}.report.name_file_temp", "Arquivo temporário", help="HTML temporário consumido pelo Hermes", disabled=off)
    with c2:
        field(f"{prefix}.report.title", "Título do relatório", disabled=off)
    c3, c4 = st.columns(2)
    with c3:
        field(f"{prefix}.report.report.error", ":material/error: Enviar quando houver ERRO", disabled=off)
    with c4:
        field(f"{prefix}.report.report.success", ":material/check_circle: Enviar quando houver SUCESSO", disabled=off)


def stage_issues(issues, stage):
    return [i for i in issues if i[1] == stage]


def status_badge(enabled, issues):
    n_err = sum(1 for lvl, *_ in issues if lvl == "error")
    n_warn = len(issues) - n_err
    if enabled is False:
        st.badge("Desligado", icon=":material/power_settings_new:", color="gray")
    elif n_err:
        st.badge(f"{n_err} erro(s)", icon=":material/error:", color="red")
    elif n_warn:
        st.badge(f"{n_warn} aviso(s)", icon=":material/warning:", color="orange")
    else:
        st.badge("OK", icon=":material/check_circle:", color="green")


def show_issues(issues):
    for lvl, _, text in issues:
        if lvl == "error":
            st.error(text, icon=":material/error:")
        else:
            st.warning(text, icon=":material/warning:")


# ==========================================
# CONFIG ATUAL (valores do run anterior; recalculada após os widgets)
# ==========================================
cfg = current_config()
issues = validate(cfg)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header(":material/folder_open: Configuração")
    st.file_uploader("Importar YAML existente", type=["yaml", "yml"], key="upload", on_change=_on_upload)
    st.button("Recarregar config.yaml", icon=":material/restart_alt:", on_click=_on_reset, width="stretch")
    msg = st.session_state.pop("load_msg", None)
    if msg:
        getattr(st, msg[0])(msg[1])
    if st.session_state.get("unknown_keys"):
        st.warning("Chaves ignoradas (não mapeadas no app):\n\n" + "\n".join(f"- `{k}`" for k in st.session_state["unknown_keys"]),
                   icon=":material/visibility_off:")

    st.divider()
    st.subheader(":material/checklist: Status")
    enabled_map = {"heimdall": cfg["heimdall"]["enabled"], "hermes": cfg["hermes"]["enabled"]}
    for key, s in STAGES.items():
        c1, c2 = st.columns([3, 2])
        c1.markdown(f"{s['icon']} {s['title']}")
        with c2:
            status_badge(enabled_map.get(key), stage_issues(issues, key))
    st.divider()
    if MODULO_CARREGADO:
        st.caption(":material/check_circle: core.Datautils carregado")
    else:
        st.caption(":material/warning: core.Datautils não encontrado — partições via simulação local")


# ==========================================
# INTERFACE
# ==========================================
st.title(":material/account_tree: YGGDRA Pipeline Maker")

tab_journey, tab_common, tab_heim, tab_pipe, tab_herm, tab_test, tab_yaml = st.tabs([
    ":material/route: Jornada",
    ":material/tune: Common",
    ":material/shield: 1 · Heimdall",
    ":material/database: 2 · Pipeline",
    ":material/mail: 3 · Hermes",
    ":material/science: Teste",
    ":material/description: YAML",
])

# ------------------------------------------ JORNADA
with tab_journey:
    st.header(":material/route: Como a pipeline executa")
    st.caption("Cada etapa tem uma aba própria. Configure na ordem, teste e baixe o YAML no final.")

    flow = ["heimdall", "pipeline", "hermes"]
    cols = st.columns([5, 1, 5, 1, 5], vertical_alignment="center")
    for i, key in enumerate(flow):
        s = STAGES[key]
        with cols[i * 2]:
            with st.container(border=True, height=260):
                st.caption(s["step"])
                st.markdown(f"#### {s['icon']} {s['title']}")
                stage_iss = stage_issues(issues, key) + (stage_issues(issues, "data") if key == "pipeline" else [])
                status_badge(enabled_map.get(key), stage_iss)
                st.markdown(s["what"])
                st.caption(s["when"])
        if i < len(flow) - 1:
            cols[i * 2 + 1].markdown("## :material/arrow_forward:")

    with st.container(border=True):
        st.markdown(f"{STAGES['common']['icon']} **Common** — {STAGES['common']['what']}")

    st.subheader(":material/fork_right: O que acontece em cada cenário")
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown(
            ":material/check_circle: **Heimdall aprova**  \n"
            "Pipeline processa as partições → gera relatório de execução → Hermes envia o e-mail "
            "(se `success` estiver ligado)."
        )
    with c2, st.container(border=True):
        st.markdown(
            ":material/block: **Heimdall reprova**  \n"
            "Pipeline **não** roda → relatório de segurança é gerado → Hermes envia o e-mail "
            "(se `error` estiver ligado)."
        )

    st.subheader(":material/format_list_numbered: Passo a passo")
    st.markdown(
        "1. **Common** — identifique o dono e a região.\n"
        "2. **Heimdall** — escolha o que validar e como as origens são encontradas.\n"
        "3. **Pipeline** — tabela destino, SQL, partições e relatório.\n"
        "4. **Hermes** — quem recebe os e-mails.\n"
        "5. **Teste** — confira os erros e simule as partições.\n"
        "6. **YAML** — baixe o arquivo final."
    )

# ------------------------------------------ COMMON
with tab_common:
    stage_intro("common")
    field("common.owner", "Owner", help="OWNER - e-mail de governança")
    c1, c2 = st.columns(2)
    with c1:
        field("common.region", "Region")
    with c2:
        field("common.log_level", "Log level")

# ------------------------------------------ HEIMDALL
with tab_heim:
    stage_intro("heimdall")
    h_on = field("heimdall.enabled", "Habilitar Heimdall")
    if not h_on:
        st.info(STAGES["heimdall"]["off"], icon=":material/power_settings_new:")

    st.divider()
    section(":material/fact_check:", "Validações", "O que o Heimdall confere antes de liberar o processamento.")
    c1, c2 = st.columns(2)
    with c1:
        field("heimdall.validate.origins", "Validar origens", help="Checa se todas as tabelas de origem já têm a partição esperada", disabled=not h_on)
    with c2:
        field("heimdall.validate.sql", "Validar SQL", help="Checa a sintaxe do SQL antes de executar", disabled=not h_on)

    st.divider()
    section(":material/hub:", "Origens (upstream)", "De onde vêm os dados que a pipeline consome.")
    o_mode = st.radio(
        "Modo de busca", options=["auto", "manual"], key=K("heimdall.origins.mode"), disabled=not h_on, horizontal=True,
        format_func={"auto": ":material/auto_awesome: Automático", "manual": ":material/edit_note: Manual"}.get,
    )

    if o_mode == "auto":
        st.caption(":material/auto_awesome: As origens são extraídas automaticamente do SQL. Liste abaixo as que devem ser ignoradas na checagem.")
        field("heimdall.origins.auto_mode.ignore_check_table", "Tabelas ignoradas na checagem", disabled=not h_on)
    else:
        st.caption(":material/edit_note: Cadastre cada origem com as regras de checagem. Só estas tabelas serão validadas.")
        ids = st.session_state["origin_ids"]
        if not ids:
            st.info("Nenhuma origem cadastrada.", icon=":material/inbox:")
        for n, oid in enumerate(ids, 1):
            db = st.session_state[OK(oid, "database")]
            tb = st.session_state[OK(oid, "table")]
            label = f"#{n} · {db}.{tb}" if db and tb else f"#{n} · Nova origem"
            with st.expander(label, icon=":material/table:", expanded=not (db and tb)):
                fields = {f: (kind, opts, lbl, hlp) for f, kind, _, opts, lbl, hlp in ORIGIN_FIELDS}

                def fw(f):
                    kind, opts, lbl, hlp = fields[f]
                    widget(kind, lbl, OK(oid, f), opts, hlp, disabled=not h_on)

                c1, c2 = st.columns(2)
                with c1:
                    fw("database")
                with c2:
                    fw("table")
                c3, c4, c5 = st.columns(3)
                with c3:
                    fw("partition_name")
                with c4:
                    fw("partition_format")
                with c5:
                    fw("lag")
                c6, c7 = st.columns([3, 1], vertical_alignment="bottom")
                with c6:
                    fw("required")
                with c7:
                    st.button("Remover", icon=":material/delete:", key=f"rm:{oid}", on_click=_remove_origin,
                              args=(oid,), disabled=not h_on, width="stretch")
        st.button("Adicionar origem", icon=":material/add:", on_click=_new_origin, disabled=not h_on)

    st.divider()
    section(":material/summarize:", "Relatório de auditoria", "Resultado do pre-flight, enviado pelo Hermes.")
    report_section("heimdall", disabled=not h_on)

    if stage_issues(issues, "heimdall"):
        st.divider()
        show_issues(stage_issues(issues, "heimdall"))

# ------------------------------------------ PIPELINE
with tab_pipe:
    stage_intro("pipeline")
    sub_dest, sub_data, sub_rep = st.tabs([
        ":material/table: Destino & SQL",
        ":material/calendar_month: Dados temporais",
        ":material/summarize: Relatório",
    ])

    with sub_dest:
        section(":material/table: ", "Tabela destino", "Onde o resultado do SQL é gravado.")
        c1, c2 = st.columns(2)
        with c1:
            field("pipeline.target.database", "Database")
        with c2:
            field("pipeline.target.table", "Table")

        st.divider()
        section(":material/share:", "Database compartilhado", "Opcional: publica a tabela também em um database compartilhado.")
        shared = field("pipeline.shared.enabled", "Habilitar database compartilhado")
        field("pipeline.shared.database", "Database compartilhado", disabled=not shared)

        st.divider()
        section(":material/code:", "Motor de execução", "Como a transformação é executada.")
        mode = field("pipeline.mode", "Mode")
        if mode == "pyspark":
            st.error("Modo pyspark ainda não é suportado.", icon=":material/error:")
        field("pipeline.sql.path", "SQL path (S3)", help="PATH_SQL_ORIGEM - arquivo .sql no S3", disabled=mode != "sql")

    with sub_data:
        st.caption(f":material/info: {STAGES['data']['what']}  \n:material/low_priority: {STAGES['data']['when']}")

        section(":material/view_column:", "Partição", "Formato da partição da tabela destino e a defasagem padrão.")
        c1, c2 = st.columns(2)
        with c1:
            field("pipeline.data.partition.name", "Nome da partição")
            field("pipeline.data.partition.type", "Type")
        with c2:
            field("pipeline.data.partition.format", "Formato")
            field("pipeline.data.partition.lag", "Lag (dias)", help="Partição padrão = hoje - lag")

        st.divider()
        section(":material/history:", "Reprocessamento",
                "Reprocessa uma janela para trás em vez de só a partição padrão — em toda execução ou só no dia de corte.")
        rp = field("pipeline.data.reprocess.enabled", "Habilitar reprocess")
        c1, c2, c3 = st.columns(3)
        with c1:
            field("pipeline.data.reprocess.range_value", "Range value", disabled=not rp)
        with c2:
            field("pipeline.data.reprocess.range_unit", "Range unit", disabled=not rp)
        with c3:
            dc_key = K("pipeline.data.reprocess.day_reprocess")
            dc_on = st.toggle("Usar dia de corte", key=dc_key + "#on", disabled=not rp,
                              help="Opcional. Desligado: reprocessa em toda execução.")
            st.number_input("Dia de corte", min_value=1, max_value=31, step=1, key=dc_key,
                            help="Dia do mês em que o reprocessamento ocorre", disabled=not (rp and dc_on))
        if rp:
            st.caption(
                f":material/event_repeat: Reprocessa **{st.session_state[K('pipeline.data.reprocess.range_value')]} "
                f"{st.session_state[K('pipeline.data.reprocess.range_unit')]}(s)** "
                + (f"todo dia **{st.session_state[dc_key]}** do mês." if dc_on else "em **toda execução**.")
            )

        st.divider()
        section(":material/fast_rewind:", "Backfill", "Carga inicial ou execução manual de um período fechado.")
        bf = field("pipeline.data.backfill.enabled", "Habilitar backfill")
        c1, c2 = st.columns(2)
        with c1:
            field("pipeline.data.backfill.start_date", "Start date", disabled=not bf)
        with c2:
            field("pipeline.data.backfill.end_date", "End date", disabled=not bf)
        if bf:
            st.info("Com backfill habilitado, ele tem prioridade sobre a partição padrão e o reprocess.", icon=":material/priority_high:")

    with sub_rep:
        section(":material/summarize:", "Relatório de execução", "Resultado do processamento, enviado pelo Hermes.")
        report_section("pipeline")

    pipe_issues = stage_issues(issues, "pipeline") + stage_issues(issues, "data")
    if pipe_issues:
        st.divider()
        show_issues(pipe_issues)

# ------------------------------------------ HERMES
with tab_herm:
    stage_intro("hermes")
    m_on = field("hermes.enabled", "Habilitar Hermes")
    if not m_on:
        st.info(STAGES["hermes"]["off"], icon=":material/power_settings_new:")
    field("hermes.group_name", "Group name", help="Grupo no DynamoDB", disabled=not m_on)
    field("hermes.members", "Destinatários", disabled=not m_on)
    if stage_issues(issues, "hermes"):
        show_issues(stage_issues(issues, "hermes"))

# Recalcula com os valores renderizados neste run
cfg = current_config()
issues = validate(cfg)

# ------------------------------------------ TESTE
with tab_test:
    st.header(":material/science: Teste da configuração")

    section(":material/rule:", "Validação por etapa")
    if not issues:
        st.success("Nenhum problema encontrado.", icon=":material/check_circle:")
    for key, s in STAGES.items():
        iss = stage_issues(issues, key)
        if iss:
            with st.expander(f"{s['title']} — {len(iss)} item(ns)", icon=s["icon"], expanded=True):
                show_issues(iss)

    st.divider()
    section(":material/view_column:", "Partições alvo")
    ref = st.date_input("Data de referência (simula o 'hoje' da execução)", value=date.today(), format="YYYY-MM-DD")
    data_cfg = copy.deepcopy(cfg["pipeline"]["data"])
    payload_json = {"data": data_cfg}

    use_dt = st.toggle("Usar core.Datautils (ignora a data de referência)", value=MODULO_CARREGADO, disabled=not MODULO_CARREGADO)

    if st.button("Gerar partições", icon=":material/play_arrow:", type="primary"):
        try:
            if use_dt:
                st.session_state["execution_partitions"] = ("Datautils", DT(payload_json).get_execution_partitions())
            else:
                st.session_state["execution_partitions"] = simulate(data_cfg, ref)
        except Exception as e:
            st.error(f"Erro ao processar partições: {e}", icon=":material/error:")
            st.session_state["execution_partitions"] = None

    col_json, col_part = st.columns(2)
    with col_json:
        st.markdown(":material/data_object: **Payload enviado**")
        st.json(payload_json)
    with col_part:
        res = st.session_state.get("execution_partitions")
        if res is None:
            st.info("Clique em 'Gerar partições'.", icon=":material/touch_app:")
        else:
            origem, parts = res
            if parts:
                st.success(f"Modo: **{origem}** — {len(parts)} partição(ões)", icon=":material/check_circle:")
                st.dataframe({cfg["pipeline"]["data"]["partition"]["name"]: parts}, width="stretch", height=300)
            else:
                st.warning("Nenhuma partição foi retornada com esta configuração.", icon=":material/warning:")

    st.divider()
    section(":material/calendar_view_month:", "Calendário de execuções (simulação)",
            "O que cada execução diária faria a partir da data de referência.")
    days = st.slider("Dias", 7, 90, 35)
    rows = []
    for i in range(days):
        d = ref + timedelta(days=i)
        m, parts = simulate(data_cfg, d)
        rows.append({
            "execução": d.isoformat(),
            "modo": m,
            "qtd partições": len(parts),
            "de": str(parts[0]) if parts else "",
            "até": str(parts[-1]) if parts else "",
        })
    st.dataframe(rows, width="stretch", hide_index=True)

# ------------------------------------------ YAML
with tab_yaml:
    st.header(":material/description: Arquivo YAML")
    yaml_text = to_yaml(cfg)
    n_err = sum(1 for lvl, *_ in issues if lvl == "error")
    if n_err:
        st.error(f"A configuração tem {n_err} erro(s). Veja a aba Teste antes de usar.", icon=":material/error:")
    elif issues:
        st.warning(f"{len(issues)} aviso(s) — veja a aba Teste.", icon=":material/warning:")
    else:
        st.success("Configuração válida.", icon=":material/check_circle:")

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    with c1:
        fname = st.text_input("Nome do arquivo", value="config.yaml")
    with c2:
        st.download_button("Baixar YAML", icon=":material/download:", data=yaml_text.encode("utf-8"), file_name=fname,
                           mime="application/x-yaml", type="primary", width="stretch")
    st.code(yaml_text, language="yaml")
