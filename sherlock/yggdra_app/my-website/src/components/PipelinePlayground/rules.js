// ---------------------------------------------------------------------------
// Datas (sempre em horario local, sem hora)
// ---------------------------------------------------------------------------
const DAY_MS = 86400000;
const pad2 = (n) => String(n).padStart(2, '0');

export function parseISO(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return d.getMonth() === Number(m[2]) - 1 ? d : null;
}
export const toISO = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
export const toBR = (d) => `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
export const diffDays = (a, b) => Math.round((b - a) / DAY_MS);
export function addDays(d, n) {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
const daysInMonth = (y, m) => new Date(y, m + 1, 0).getDate();

function subtractRange(d, value, unit) {
  if (unit === 'day') return addDays(d, -value);
  const months = unit === 'year' ? value * 12 : value;
  const target = new Date(d.getFullYear(), d.getMonth() - months, 1);
  target.setDate(Math.min(d.getDate(), daysInMonth(target.getFullYear(), target.getMonth())));
  return target;
}

export function formatPartition(d, fmt) {
  return String(fmt || 'YYYYMMDD')
    .replace('YYYY', String(d.getFullYear()))
    .replace('MM', pad2(d.getMonth() + 1))
    .replace('DD', pad2(d.getDate()));
}

function nextCutDate(from, day) {
  if (!(day >= 1 && day <= 31)) return null;
  for (let i = 0; i <= 400; i += 1) {
    const d = addDays(from, i);
    if (d.getDate() === day) return d;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Simulacao: o que a pipeline faria se rodasse na data informada.
// Premissa: a janela de reprocessamento termina na particao padrao
// (execucao - lag) e volta range_value * range_unit.
// ---------------------------------------------------------------------------
export function simulate(c, runDate) {
  const {partition, reprocess, backfill} = c.pipeline.data;
  const fmt = partition.format;
  const lag = Math.max(0, parseInt(partition.lag, 10) || 0);
  const ref = addDays(runDate, -lag);

  const result = {runDate, ref, lag, partition: formatPartition(ref, fmt), reprocess: null, backfill: null};

  if (reprocess.enabled) {
    const day = parseInt(reprocess.day_reprocess, 10);
    const value = Math.max(1, parseInt(reprocess.range_value, 10) || 1);
    const from = subtractRange(ref, value, reprocess.range_unit);
    result.reprocess = {
      day,
      isCutDay: runDate.getDate() === day,
      from,
      to: ref,
      fromLabel: formatPartition(from, fmt),
      toLabel: formatPartition(ref, fmt),
      days: diffDays(from, ref) + 1,
      nextCut: nextCutDate(addDays(runDate, 1), day),
    };
  }

  if (backfill.enabled) {
    const s = parseISO(backfill.start_date);
    const e = parseISO(backfill.end_date);
    if (s && e && s <= e) {
      result.backfill = {
        from: s,
        to: e,
        fromLabel: formatPartition(s, fmt),
        toLabel: formatPartition(e, fmt),
        days: diffDays(s, e) + 1,
      };
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Validacoes. Cada item: {level: 'error' | 'warning', path, message}
// ---------------------------------------------------------------------------
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const IDENT = /^[a-z][a-z0-9_]*$/;
const CORP_DOMAIN = '@itau-unibanco.com.br';
const isInt = (v) => v !== '' && Number.isInteger(Number(v));

export function validate(c, today) {
  const out = [];
  const error = (path, message) => out.push({level: 'error', path, message});
  const warning = (path, message) => out.push({level: 'warning', path, message});

  const {common, pipeline: p, heimdall: h, hermes} = c;
  const {partition, reprocess, backfill} = p.data;

  // --- common ---------------------------------------------------------------
  if (!EMAIL.test(common.owner || '')) error('common.owner', 'Informe um e-mail válido para o responsável.');
  else if (!common.owner.toLowerCase().endsWith(CORP_DOMAIN))
    warning('common.owner', `O responsável deveria usar o domínio ${CORP_DOMAIN}.`);

  if (!(common.region || '').trim()) error('common.region', 'Informe a região AWS.');
  else if (!/^[a-z]{2}-[a-z]+-\d$/.test(common.region))
    warning('common.region', 'Região em formato inesperado. Exemplo: sa-east-1.');

  if (/\s/.test((common.job_name || '').trim())) error('common.job_name', 'O nome do job Glue não pode ter espaços.');

  // --- pipeline: destino ----------------------------------------------------
  checkIdent(p.target.database, 'pipeline.target.database', 'database', error);
  checkIdent(p.target.table, 'pipeline.target.table', 'tabela', error);

  if (p.shared.enabled) {
    error('pipeline.shared.enabled', 'Database compartilhado ainda não é suportado: com essa opção ligada a pipeline falha.');
    if (!(p.shared.database || '').trim()) error('pipeline.shared.database', 'Informe o database compartilhado.');
  }

  // --- pipeline: motor ------------------------------------------------------
  if (p.mode === 'pyspark') error('pipeline.mode', 'O modo PySpark ainda não é suportado. Use SQL.');
  if (p.mode === 'sql') {
    const path = (p.sql.path || '').trim();
    if (!path) error('pipeline.sql.path', 'Informe o caminho do arquivo .sql no S3.');
    else if (!/^s3:\/\/[a-z0-9.-]+\/.+/.test(path)) error('pipeline.sql.path', 'O caminho deve começar com s3://bucket/…');
    else if (!path.toLowerCase().endsWith('.sql')) warning('pipeline.sql.path', 'O arquivo não termina em .sql.');
  }

  // --- pipeline: particao ---------------------------------------------------
  checkIdent(partition.name, 'pipeline.data.partition.name', 'coluna de partição', error);
  if (!isInt(partition.lag) || Number(partition.lag) < 0)
    error('pipeline.data.partition.lag', 'A defasagem precisa ser um número inteiro maior ou igual a 0.');
  else if (Number(partition.lag) > 60)
    warning('pipeline.data.partition.lag', 'Defasagem acima de 60 dias. Confirme se é intencional.');

  if (partition.type === 'int' && partition.format.includes('-'))
    error('pipeline.data.partition.format', 'Formato com hífen não cabe em partição int. Use YYYYMMDD ou mude o tipo.');
  if (partition.type === 'date' && partition.format !== 'YYYY-MM-DD')
    warning('pipeline.data.partition.format', 'Partições do tipo date costumam usar o formato YYYY-MM-DD.');

  // --- pipeline: reprocessamento --------------------------------------------
  if (reprocess.enabled) {
    if (!isInt(reprocess.range_value) || Number(reprocess.range_value) < 1)
      error('pipeline.data.reprocess.range_value', 'O período precisa ser um inteiro maior ou igual a 1.');
    const day = Number(reprocess.day_reprocess);
    if (!isInt(reprocess.day_reprocess) || day < 1 || day > 31)
      error('pipeline.data.reprocess.day_reprocess', 'O dia de corte precisa estar entre 1 e 31.');
    else if (day > 28)
      warning(
        'pipeline.data.reprocess.day_reprocess',
        `Nem todo mês tem dia ${day} (fevereiro, por exemplo). Confirme como a pipeline trata esses meses.`,
      );
  }

  // --- pipeline: backfill ---------------------------------------------------
  if (backfill.enabled) {
    const s = parseISO(backfill.start_date);
    const e = parseISO(backfill.end_date);
    if (!s) error('pipeline.data.backfill.start_date', 'Informe uma data inicial válida.');
    if (!e) error('pipeline.data.backfill.end_date', 'Informe uma data final válida.');
    if (s && e && s > e) error('pipeline.data.backfill.end_date', 'A data final é anterior à data inicial.');
    if (e && today) {
      const limit = addDays(today, -(parseInt(partition.lag, 10) || 0));
      if (e > limit)
        warning(
          'pipeline.data.backfill.end_date',
          `A data final passa da partição disponível hoje (${toBR(limit)}). Pode ainda não haver dados.`,
        );
    }
  }

  // --- relatorios -----------------------------------------------------------
  checkReport(p.report, 'pipeline.report', p.target.table, error, warning);

  // --- heimdall -------------------------------------------------------------
  if (h.enabled) {
    if (!h.validate.origins && !h.validate.sql)
      warning('heimdall.validate.origins', 'O Heimdall está ligado, mas nenhuma validação está marcada.');
    if (h.origins.mode === 'manual' && !h.origins.manual_mode.tables.some((t) => t.trim()))
      error('heimdall.origins.manual_mode.tables', 'No modo manual, liste ao menos uma tabela de origem.');
    const listPath =
      h.origins.mode === 'manual' ? 'heimdall.origins.manual_mode.tables' : 'heimdall.origins.auto_mode.ignore_check_table';
    const list = h.origins.mode === 'manual' ? h.origins.manual_mode.tables : h.origins.auto_mode.ignore_check_table;
    const bad = list.filter((t) => t.trim() && !/^[A-Za-z0-9_.]+$/.test(t.trim()));
    if (bad.length) error(listPath, `Nomes de tabela inválidos: ${bad.join(', ')}.`);
    checkReport(h.report, 'heimdall.report', p.target.table, error, warning);
  }

  // --- hermes ---------------------------------------------------------------
  if (hermes.enabled) {
    if (!(hermes.group_name || '').trim()) error('hermes.group_name', 'Informe o grupo do DynamoDB.');
    const members = hermes.members.map((m) => m.trim()).filter(Boolean);
    if (!members.length) error('hermes.members', 'Adicione ao menos um destinatário.');
    const invalid = members.filter((m) => !EMAIL.test(m));
    if (invalid.length) error('hermes.members', `E-mails inválidos: ${invalid.join(', ')}.`);
  } else if ((p.report.enabled || (h.enabled && h.report.enabled)))
    warning('hermes.enabled', 'Os relatórios são enviados pelo Hermes. Com ele desligado, ninguém recebe o e-mail.');

  return out;
}

function checkIdent(value, path, what, error) {
  const v = (value || '').trim();
  if (!v) error(path, `Informe o nome da ${what}.`);
  else if (!IDENT.test(v)) error(path, `Use só letras minúsculas, números e _ no nome da ${what}.`);
}

function checkReport(r, base, table, error, warning) {
  if (!r.enabled) return;
  if (!(r.name_file_temp || '').trim()) error(`${base}.name_file_temp`, 'Informe o nome do arquivo temporário.');
  if (!(r.title || '').trim()) warning(`${base}.title`, 'O relatório está sem título.');
  else if (table && !r.title.includes(table)) {
    const cited = (r.title.match(/\b[a-z0-9]+(?:_[a-z0-9]+)+\b/g) || [])[0];
    warning(
      `${base}.title`,
      cited
        ? `O título cita "${cited}", mas a tabela destino é "${table}".`
        : `O título não menciona a tabela destino "${table}".`,
    );
  }
  if (!r.report.error && !r.report.success)
    warning(`${base}.report.error`, 'Relatório ligado, mas não é gerado nem em erro nem em sucesso.');
}
