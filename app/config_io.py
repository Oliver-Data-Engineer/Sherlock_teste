"""Schema, leitura/escrita e validacao do config.yaml da pipeline YGGDRA."""
import json
from datetime import date, datetime
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

# ==========================================
# OPCOES
# ==========================================
FORMATS = ["YYYY-MM-DD", "YYYY-MM-01", "YYYYMMDD", "YYYYMM01", "YYYYMM", "YYYY", "MM", "DD"]
TYPES = ["int", "string"]
UNITS = ["day", "month", "year"]
MODES = ["sql", "pyspark"]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
ORIGIN_MODES = ["auto", "manual"]

# ==========================================
# SCHEMA: (caminho, tipo, default, opcoes)
# tipos: str | int | optint (int opcional) | bool | select | date | list | records
# ==========================================
SCHEMA = [
    ("common.owner", "str", "", None),
    ("common.region", "str", "sa-east-1", None),
    ("common.log_level", "select", "INFO", LOG_LEVELS),

    ("pipeline.target.database", "str", "", None),
    ("pipeline.target.table", "str", "", None),
    ("pipeline.shared.enabled", "bool", False, None),
    ("pipeline.shared.database", "str", "", None),
    ("pipeline.mode", "select", "sql", MODES),
    ("pipeline.sql.path", "str", "", None),
    ("pipeline.data.partition.name", "str", "anomesdia", None),
    ("pipeline.data.partition.type", "select", "int", TYPES),
    ("pipeline.data.partition.format", "select", "YYYYMMDD", FORMATS),
    ("pipeline.data.partition.lag", "int", 1, None),
    ("pipeline.data.reprocess.enabled", "bool", False, None),
    ("pipeline.data.reprocess.range_value", "int", 1, None),
    ("pipeline.data.reprocess.range_unit", "select", "month", UNITS),
    ("pipeline.data.reprocess.day_reprocess", "optint", None, None),  # opcional: None = sem dia de corte
    ("pipeline.data.backfill.enabled", "bool", False, None),
    ("pipeline.data.backfill.start_date", "date", date.today(), None),
    ("pipeline.data.backfill.end_date", "date", date.today(), None),
    ("pipeline.report.enabled", "bool", True, None),
    ("pipeline.report.name_file_temp", "str", "temp", None),
    ("pipeline.report.title", "str", "", None),
    ("pipeline.report.report.error", "bool", True, None),
    ("pipeline.report.report.success", "bool", False, None),

    ("heimdall.enabled", "bool", True, None),
    ("heimdall.validate.origins", "bool", True, None),
    ("heimdall.validate.sql", "bool", True, None),
    ("heimdall.origins.mode", "select", "auto", ORIGIN_MODES),
    ("heimdall.origins.auto_mode.ignore_check_table", "list", [], None),
    ("heimdall.origins.manual_mode.tables", "records", [], None),
    ("heimdall.report.enabled", "bool", True, None),
    ("heimdall.report.name_file_temp", "str", "temp", None),
    ("heimdall.report.title", "str", "", None),
    ("heimdall.report.report.error", "bool", True, None),
    ("heimdall.report.report.success", "bool", False, None),

    ("hermes.enabled", "bool", True, None),
    ("hermes.group_name", "str", "", None),
    ("hermes.members", "list", [], None),
]
SCHEMA_BY_PATH = {s[0]: s for s in SCHEMA}

# Campos de cada origem no modo manual do Heimdall: (campo, tipo, default, opcoes, label, ajuda)
ORIGIN_FIELDS = [
    ("database", "str", "", None, "Database", "Database da tabela de origem"),
    ("table", "str", "", None, "Tabela", "Nome da tabela de origem"),
    ("partition_name", "str", "anomesdia", None, "Coluna de partição", "Partição usada para checar a prontidão"),
    ("partition_format", "select", "YYYYMMDD", FORMATS, "Formato da partição", None),
    ("lag", "int", 1, None, "Lag (dias)", "Partição esperada = data de execução - lag"),
    ("required", "bool", True, None, "Obrigatória", "Se a origem não estiver pronta, BLOQUEIA a pipeline"),
]


def normalize_origin(item):
    """Aceita dict ou string 'database.tabela' e devolve um dict com todos os campos."""
    if isinstance(item, str):
        db, _, tb = item.rpartition(".")
        item = {"database": db, "table": tb}
    if not isinstance(item, dict):
        item = {}
    return {f: _coerce(kind, item.get(f), default, opts) for f, kind, default, opts, _, _ in ORIGIN_FIELDS}


def _get(d, path):
    for part in path.split("."):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d


def _set(d, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value


def _coerce(kind, value, default, options):
    """Converte um valor vindo do YAML para o tipo esperado pelo widget."""
    if value is None:
        return default
    try:
        if kind == "bool":
            return bool(value)
        if kind in ("int", "optint"):
            return int(value)
        if kind == "date":
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        if kind == "list":
            return [str(v) for v in value] if isinstance(value, list) else [str(value)]
        if kind == "records":
            return [normalize_origin(v) for v in value] if isinstance(value, list) else default
        if kind == "select":
            return value if value in options else default
        return str(value)
    except (TypeError, ValueError):
        return default


def flatten(cfg):
    """dict aninhado -> {caminho: valor tipado}. Retorna tambem chaves nao reconhecidas."""
    flat = {path: _coerce(kind, _get(cfg, path), default, opts) for path, kind, default, opts in SCHEMA}
    unknown = []

    def walk(d, prefix=""):
        for k, v in d.items():
            p = f"{prefix}{k}"
            if p in SCHEMA_BY_PATH:
                continue
            if isinstance(v, dict):
                walk(v, p + ".")
            elif p not in SCHEMA_BY_PATH:
                unknown.append(p)

    if isinstance(cfg, dict):
        walk(cfg)
    return flat, unknown


def unflatten(flat):
    cfg = {}
    for path, kind, _, _ in SCHEMA:
        value = flat[path]
        if kind == "date":
            value = value.strftime("%Y-%m-%d")
        _set(cfg, path, value)
    return cfg


def load_yaml_text(text):
    # Espacos nao-separaveis (U+00A0, comuns em copia/cola) sao invalidos como indentacao YAML
    text = text.replace("\u00a0", " ").replace("\ufeff", "")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("O YAML precisa ter um mapeamento na raiz.")
    return data


def load_default_config():
    if CONFIG_PATH.exists():
        return load_yaml_text(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


# ==========================================
# GERACAO DO YAML (com comentarios, no mesmo layout do config.yaml original)
# ==========================================
def _q(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return json.dumps(str(v), ensure_ascii=False)


def _list(items, indent):
    pad = " " * indent
    if not items:
        return [f"{pad}[]"]
    return [f"{pad}- {_q(i)}" for i in items]


def _records(items, indent):
    pad = " " * indent
    if not items:
        return [f"{pad}[]"]
    out = []
    for it in items:
        for i, (f, *_rest) in enumerate(ORIGIN_FIELDS):
            out.append(f"{pad}{'- ' if i == 0 else '  '}{f}: {_q(it[f])}")
    return out


def _report_block(r, indent, comment):
    pad = " " * indent
    return [
        f"{pad}report:",
        f"{pad}  enabled: {_q(r['enabled'])}",
        f"{pad}  name_file_temp: {_q(r['name_file_temp'])}              # arquivo HTML temporario (consumido pelo Hermes)",
        f"{pad}  title: {_q(r['title'])}",
        f"{pad}  report:",
        f"{pad}    error: {_q(r['report']['error'])}                          # gera/roteia relatorio quando houver erro",
        f"{pad}    success: {_q(r['report']['success'])}                       # gera/roteia relatorio quando houver sucesso",
    ] if comment else []


def to_yaml(cfg):
    c, p, h, m = cfg["common"], cfg["pipeline"], cfg["heimdall"], cfg["hermes"]
    d = p["data"]
    pt, rp, bf = d["partition"], d["reprocess"], d["backfill"]
    L = [
        "# -----------------------------------------------------------------------------",
        "# COMMON - Configuracoes COMPARTILHADAS por Heimdall, Pipeline e Hermes.",
        "# -----------------------------------------------------------------------------",
        "common:",
        f"  owner: {_q(c['owner'])}     # OWNER (governanca / dominio corporativo)",
        f"  region: {_q(c['region'])}",
        f"  log_level: {_q(c['log_level'])}                            # LOG_LEVEL (DEBUG, INFO, WARNING, ERROR)",
        "",
        "# -----------------------------------------------------------------------------",
        "# PIPELINE - Configuracao do PROCESSAMENTO (DataFactory / Hefesto).",
        "# -----------------------------------------------------------------------------",
        "pipeline:",
        "",
        "  # --- Identidade da tabela destino -----------------------------------------",
        "  target:",
        f"    database: {_q(p['target']['database'])}                                     # DB",
        f"    table: {_q(p['target']['table'])}                       # TABLE_NAME",
        "",
        "  # Database compartilhado (opcional)",
        "  shared:",
        f"    enabled: {_q(p['shared']['enabled'])}",
        f"    database: {_q(p['shared']['database'])}",
        "",
        "  # --- Motor de execucao e origem do SQL ------------------------------------",
        f"  mode: {_q(p['mode'])}                                                  # (sql | pyspark) - pyspark AINDA",
        "",
        "  sql:",
        f"    path: {_q(p['sql']['path'])}   # PATH_SQL_ORIGEM (S3) do arquivo .sql",
        "",
        "  # --- Regras temporais / dados ---------------------------------------------",
        "  data:",
        "    # Particionamento da Tabela Destino",
        "    partition:",
        f"      name: {_q(pt['name'])}",
        f"      type: {_q(pt['type'])}                  # PARTITION_TYPE",
        f"      format: {_q(pt['format'])}           # PARTITION_FORMAT - formato do valor da particao",
        f"      lag: {_q(pt['lag'])}                       # DEFASAGEM - data da particao padrao = today() - lag",
        "",
        "    # Estrategia e Janela de Reprocessamento",
        "    reprocess:",
        f"      enabled: {_q(rp['enabled'])}                # REPROCESSAMENTO - liga/desliga o reprocessamento",
        f"      range_value: {_q(rp['range_value'])}                # RANGE_REPROCESSAMENTO - periodo reprocessado",
        f"      range_unit: {_q(rp['range_unit'])}           # day, month, year",
        *([f"      day_reprocess: {_q(rp['day_reprocess'])}             # DIA_CORTE - dia em que o reprocessamento e feito"]
          if rp["day_reprocess"] is not None else
          ["      # day_reprocess: (opcional) sem dia de corte = reprocessa em toda execucao"]),
        "",
        '    # Filtros Opcionais de Carga Inicial ou Execucao Manual - data "%Y-%m-%d"',
        "    backfill:",
        f"      enabled: {_q(bf['enabled'])}               # liga/desliga o backfill",
        f"      start_date: {_q(bf['start_date'])}     # DT_INI - data inicio do processamento",
        f"      end_date: {_q(bf['end_date'])}       # DT_FIM - data final do processamento",
        "",
        "  # --- Relatorio de execucao (etapa de PROCESSAMENTO) -----------------------",
        *_report_block(p["report"], 2, True),
        "",
        "# -----------------------------------------------------------------------------",
        "# HEIMDALL - Guardiao / Pre-Flight. Roda ANTES do processamento e pode BLOQUEAR",
        "# a orquestracao caso alguma validacao reprove.",
        "# -----------------------------------------------------------------------------",
        "heimdall:",
        f"  enabled: {_q(h['enabled'])}",
        "",
        "  # --- Validacoes a executar -------------------------------------------------",
        "  validate:",
        f"    origins: {_q(h['validate']['origins'])}                       # avalia a prontidao de todas as origens",
        f"    sql: {_q(h['validate']['sql'])}                           # valida a saude sintatica do SQL antes de rodar",
        "",
        "  # --- Mapeamento das origens (linhagem / upstream) -------------------------",
        "  origins:",
        "    # Modo de busca das origens (auto = extrai da query; manual = lista abaixo)",
        f"    mode: {_q(h['origins']['mode'])}",
        "",
        "    auto_mode:",
        "      ignore_check_table:",
        *_list(h["origins"]["auto_mode"]["ignore_check_table"], 8),
    ]
    if h["origins"]["mode"] == "manual":
        L += [
            "",
            "    manual_mode:",
            "      tables:",
            *_records(h["origins"]["manual_mode"]["tables"], 8),
        ]
    L += [
        "",
        "  # --- Relatorio de auditoria (etapa de PRE-FLIGHT) -------------------------",
        *_report_block(h["report"], 2, True),
        "",
        "# -----------------------------------------------------------------------------",
        "# HERMES - Mensageiro / Notificacao por e-mail (roda no FINAL da pipeline).",
        "# Requer a lib iara_beholder_logs no cluster.",
        "# -----------------------------------------------------------------------------",
        "hermes:",
        f"  enabled: {_q(m['enabled'])}",
        f"  group_name: {_q(m['group_name'])}     # GROUP_NAME (grupo no DynamoDB)",
        "  members:                                 # MEMBERS - destinatarios do e-mail",
        *_list(m["members"], 4),
        "",
    ]
    return "\n".join(L)


# ==========================================
# VALIDACAO
# ==========================================
def validate(cfg):
    """Retorna lista de (nivel, etapa, mensagem).

    nivel: 'error' | 'warning'; etapa: 'common' | 'heimdall' | 'pipeline' | 'data' | 'hermes'.
    """
    out = []

    def err(stage, msg):
        out.append(("error", stage, msg))

    def warn(stage, msg):
        out.append(("warning", stage, msg))

    c, p, h, m = cfg["common"], cfg["pipeline"], cfg["heimdall"], cfg["hermes"]
    d = p["data"]

    if not c["owner"]:
        err("common", "Owner vazio.")
    elif "@" not in c["owner"]:
        warn("common", "Owner não parece um e-mail.")
    if not c["region"]:
        err("common", "Region vazia.")

    if not p["target"]["database"]:
        err("pipeline", "Database da tabela destino vazio.")
    if not p["target"]["table"]:
        err("pipeline", "Nome da tabela destino vazio.")
    if p["shared"]["enabled"] and not p["shared"]["database"]:
        err("pipeline", "Database compartilhado habilitado mas sem nome.")
    if p["mode"] == "pyspark":
        err("pipeline", "Modo pyspark ainda não é suportado.")
    if p["mode"] == "sql":
        path = p["sql"]["path"]
        if not path:
            err("pipeline", "Caminho do SQL vazio (obrigatório no modo sql).")
        else:
            if not path.startswith("s3://"):
                warn("pipeline", "Caminho do SQL deveria começar com s3://")
            if not path.lower().endswith(".sql"):
                warn("pipeline", "Caminho do SQL deveria terminar com .sql")

    if d["partition"]["lag"] < 0:
        err("data", "Lag da partição não pode ser negativo.")
    if not d["partition"]["name"]:
        err("data", "Nome da partição vazio.")
    if d["partition"]["type"] == "int" and "-" in d["partition"]["format"]:
        warn("data", f"Partição do tipo int com formato '{d['partition']['format']}' (contém '-').")

    rp = d["reprocess"]
    if rp["enabled"]:
        if rp["range_value"] < 1:
            err("data", "Range do reprocess deve ser >= 1.")
        if rp["day_reprocess"] is None:
            pass
        elif not 1 <= rp["day_reprocess"] <= 31:
            err("data", "Dia de corte do reprocess deve estar entre 1 e 31.")
        elif rp["day_reprocess"] > 28:
            warn("data", f"Dia de corte {rp['day_reprocess']}: meses mais curtos nunca terão reprocessamento.")

    bf = d["backfill"]
    if bf["enabled"]:
        if bf["start_date"] > bf["end_date"]:
            err("data", "Backfill: data inicial maior que a final.")
        if bf["end_date"] > date.today().strftime("%Y-%m-%d"):
            warn("data", "Backfill: data final está no futuro.")

    if h["enabled"] and h["origins"]["mode"] == "manual":
        tables = h["origins"]["manual_mode"]["tables"]
        if not tables:
            err("heimdall", "Modo manual sem nenhuma origem cadastrada.")
        seen = set()
        for i, t in enumerate(tables, 1):
            if not t["database"] or not t["table"]:
                err("heimdall", f"Origem #{i}: database e tabela são obrigatórios.")
                continue
            fq = f"{t['database']}.{t['table']}"
            if fq in seen:
                warn("heimdall", f"Origem {fq} cadastrada mais de uma vez.")
            seen.add(fq)
            if t["lag"] < 0:
                err("heimdall", f"Origem {fq}: lag não pode ser negativo.")

    if m["enabled"]:
        if not m["group_name"]:
            err("hermes", "Group name vazio.")
        if not m["members"]:
            err("hermes", "Nenhum destinatário (ninguém receberá o e-mail).")
        for mem in m["members"]:
            if "@" not in mem:
                warn("hermes", f"'{mem}' não parece um e-mail.")
        if not (p["report"]["enabled"] or (h["enabled"] and h["report"]["enabled"])):
            warn("hermes", "Hermes habilitado mas nenhum relatório (Heimdall/Pipeline) está habilitado.")

    for stage, rep in (("pipeline", p["report"]), ("heimdall", h["report"])):
        if rep["enabled"] and not (rep["report"]["error"] or rep["report"]["success"]):
            warn(stage, "Relatório habilitado mas não será enviado nem em erro nem em sucesso.")

    return out
