"""Simulacao local das particoes alvo, usada quando core.Datautils nao esta disponivel.

Regras (conforme comentarios do config.yaml):
  - particao padrao = data_ref - lag (dias)
  - backfill habilitado -> todas as datas entre start_date e end_date
  - reprocess habilitado e (sem day_reprocess OU dia(data_ref) == day_reprocess)
        -> janela de range_value range_unit terminando na particao padrao
  - particoes sao formatadas conforme partition.format e deduplicadas
"""
from calendar import monthrange
from datetime import date, datetime, timedelta


def _minus_months(d, n):
    y, m = divmod(d.year * 12 + (d.month - 1) - n, 12)
    m += 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def _shift_back(d, value, unit):
    if unit == "day":
        return d - timedelta(days=value)
    if unit == "month":
        return _minus_months(d, value)
    return _minus_months(d, value * 12)


def format_partition(d, fmt, ptype):
    s = (fmt.replace("YYYY", f"{d.year:04d}")
            .replace("MM", f"{d.month:02d}")
            .replace("DD", f"{d.day:02d}"))
    if ptype == "int" and s.isdigit():
        return int(s)
    return s


def _parse(s):
    return s if isinstance(s, date) else datetime.strptime(s, "%Y-%m-%d").date()


def simulate(data_cfg, ref_date):
    """Retorna (modo, lista_de_particoes)."""
    pt, rp, bf = data_cfg["partition"], data_cfg["reprocess"], data_cfg["backfill"]
    base = ref_date - timedelta(days=int(pt["lag"]))

    if bf["enabled"]:
        start, end = _parse(bf["start_date"]), _parse(bf["end_date"])
        mode = "backfill"
    elif rp["enabled"] and (rp.get("day_reprocess") is None or ref_date.day == int(rp["day_reprocess"])):
        start = _shift_back(base, int(rp["range_value"]), rp["range_unit"]) + timedelta(days=1)
        end = base
        mode = "reprocess"
    else:
        start = end = base
        mode = "padrao"

    seen, out = set(), []
    d = start
    while d <= end:
        v = format_partition(d, pt["format"], pt["type"])
        if v not in seen:
            seen.add(v)
            out.append(v)
        d += timedelta(days=1)
    return mode, out
