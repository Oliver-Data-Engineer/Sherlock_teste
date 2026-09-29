import {load as loadYaml} from 'js-yaml';
import {BLANK_CONFIG} from './defaults';

// ---------------------------------------------------------------------------
// Geracao: escrita manual para manter a ordem das chaves e os comentarios
// no mesmo padrao do arquivo de referencia.
// ---------------------------------------------------------------------------
const COMMENT_COL = 52;
const pad = (n) => ' '.repeat(n);
const str = (v) => JSON.stringify(v == null ? '' : String(v)); // string YAML entre aspas duplas
const bool = (v) => (v ? 'true' : 'false');
const int = (v) => {
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? String(n) : '0';
};

function kv(indent, key, value, comment) {
  const base = value === undefined ? `${pad(indent)}${key}:` : `${pad(indent)}${key}: ${value}`;
  return comment ? `${base.padEnd(COMMENT_COL)} # ${comment}` : base;
}

function list(indent, key, items, comment) {
  const clean = (items || []).map((i) => String(i).trim()).filter(Boolean);
  if (!clean.length) return [kv(indent, key, '[]', comment)];
  return [kv(indent, key, undefined, comment), ...clean.map((i) => `${pad(indent + 2)}- ${str(i)}`)];
}

function banner(title, lines = []) {
  const rule = `# ${'-'.repeat(77)}`;
  return [rule, `# ${title}`, ...lines.map((l) => `# ${l}`), rule];
}

function reportBlock(r) {
  return [
    kv(2, 'report'),
    kv(4, 'enabled', bool(r.enabled)),
    kv(4, 'name_file_temp', str(r.name_file_temp), 'arquivo HTML temporario (consumido pelo Hermes)'),
    kv(4, 'title', str(r.title)),
    kv(4, 'report'),
    kv(6, 'error', bool(r.report.error), 'gera/roteia relatorio quando houver erro'),
    kv(6, 'success', bool(r.report.success), 'gera/roteia relatorio quando houver sucesso'),
  ];
}

export function toYaml(c) {
  const {common, pipeline: p, heimdall: h, hermes} = c;
  const {partition, reprocess, backfill} = p.data;
  const jobName = (common.job_name || '').trim();

  const lines = [
    ...banner('COMMON - Configuracoes COMPARTILHADAS por Heimdall, Pipeline e Hermes.'),
    'common:',
    kv(2, 'owner', str(common.owner), 'OWNER (governanca / dominio corporativo)'),
    kv(2, 'region', str(common.region), 'REGION_NAME'),
    ...(jobName ? [kv(2, 'job_name', str(jobName), 'JOB_NAME do Glue (vazio = pula o backup)')] : []),
    kv(2, 'log_level', str(common.log_level), 'LOG_LEVEL (DEBUG, INFO, WARNING, ERROR)'),
    '',
    ...banner('PIPELINE - Configuracao do PROCESSAMENTO (DataFactory / Hefesto).', [
      'Define a tabela destino, a origem do SQL, o motor de execucao e as regras',
      'temporais (particionamento, reprocessamento e backfill).',
    ]),
    'pipeline:',
    kv(2, 'target'),
    kv(4, 'database', str(p.target.database), 'DB'),
    kv(4, 'table', str(p.target.table), 'TABLE_NAME'),
    '',
    kv(2, 'shared', undefined, 'Database compartilhado - AINDA NAO SUPORTADO'),
    kv(4, 'enabled', bool(p.shared.enabled), 'true dispara erro'),
    kv(4, 'database', str(p.shared.database)),
    '',
    kv(2, 'mode', str(p.mode), 'sql | pyspark (pyspark ainda nao suportado)'),
    kv(2, 'sql'),
    kv(4, 'path', str(p.sql.path), 'PATH_SQL_ORIGEM (S3) do arquivo .sql'),
    '',
    kv(2, 'data'),
    kv(4, 'partition'),
    kv(6, 'name', str(partition.name), 'nome da coluna de particao'),
    kv(6, 'type', str(partition.type), 'PARTITION_TYPE'),
    kv(6, 'format', str(partition.format), 'PARTITION_FORMAT'),
    kv(6, 'lag', int(partition.lag), 'DEFASAGEM - particao padrao = today() - lag'),
    '',
    kv(4, 'reprocess'),
    kv(6, 'enabled', bool(reprocess.enabled), 'REPROCESSAMENTO'),
    kv(6, 'range_value', int(reprocess.range_value), 'RANGE_REPROCESSAMENTO'),
    kv(6, 'range_unit', str(reprocess.range_unit), 'day, month, year'),
    kv(6, 'day_reprocess', int(reprocess.day_reprocess), 'DIA_CORTE'),
    '',
    kv(4, 'backfill', undefined, 'datas no formato %Y-%m-%d'),
    kv(6, 'enabled', bool(backfill.enabled)),
    kv(6, 'start_date', str(backfill.start_date), 'DT_INI'),
    kv(6, 'end_date', str(backfill.end_date), 'DT_FIM'),
    '',
    ...reportBlock(p.report),
    '',
    ...banner('HEIMDALL - Guardiao / Pre-Flight. Roda ANTES do processamento e pode', [
      'BLOQUEAR a orquestracao caso alguma validacao reprove.',
    ]),
    'heimdall:',
    kv(2, 'enabled', bool(h.enabled)),
    '',
    kv(2, 'validate'),
    kv(4, 'origins', bool(h.validate.origins), 'avalia a prontidao das origens'),
    kv(4, 'sql', bool(h.validate.sql), 'valida a sintaxe do SQL antes de rodar'),
    '',
    kv(2, 'origins'),
    kv(4, 'mode', str(h.origins.mode), 'auto = extrai da query; manual = lista'),
    ...(h.origins.mode === 'manual'
      ? [kv(4, 'manual_mode'), ...list(6, 'tables', h.origins.manual_mode.tables)]
      : [kv(4, 'auto_mode'), ...list(6, 'ignore_check_table', h.origins.auto_mode.ignore_check_table)]),
    '',
    ...reportBlock(h.report),
    '',
    ...banner('HERMES - Mensageiro / Notificacao por e-mail (roda no FINAL da pipeline).', [
      'Requer a lib iara_beholder_logs no cluster.',
    ]),
    'hermes:',
    kv(2, 'enabled', bool(hermes.enabled)),
    kv(2, 'group_name', str(hermes.group_name), 'GROUP_NAME (grupo no DynamoDB)'),
    ...list(2, 'members', hermes.members, 'MEMBERS - destinatarios do e-mail'),
  ];

  return `${lines.join('\n')}\n`;
}

// ---------------------------------------------------------------------------
// Importacao: le um YAML existente e encaixa na estrutura conhecida.
// ---------------------------------------------------------------------------
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function normalize(v) {
  if (v instanceof Date) return v.toISOString().slice(0, 10); // datas sem aspas viram Date no js-yaml
  if (Array.isArray(v)) return v.map(normalize);
  if (isObj(v)) return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, normalize(x)]));
  return v;
}

function merge(base, over, path, ignored) {
  if (over === undefined || over === null) return base;
  if (Array.isArray(base)) return Array.isArray(over) ? over.map(String) : base;
  if (isObj(base)) {
    if (!isObj(over)) {
      ignored.push(path);
      return base;
    }
    const out = {...base};
    for (const [k, v] of Object.entries(over)) {
      const p = path ? `${path}.${k}` : k;
      if (!(k in base)) {
        ignored.push(p);
        continue;
      }
      out[k] = merge(base[k], v, p, ignored);
    }
    return out;
  }
  if (typeof base === 'boolean') return over === true || over === 'true';
  if (typeof base === 'number') {
    const n = Number(over);
    return Number.isFinite(n) ? n : base;
  }
  return String(over);
}

export function fromYaml(text) {
  let raw;
  try {
    raw = loadYaml(text);
  } catch (e) {
    const line = e.mark ? ` na linha ${e.mark.line + 1}` : '';
    throw new Error(`YAML inválido${line}: ${e.reason || e.message}`);
  }
  if (!isObj(raw)) {
    throw new Error('O texto colado não tem as seções common, pipeline, heimdall e hermes.');
  }
  const ignored = [];
  const config = merge(BLANK_CONFIG, normalize(raw), '', ignored);
  return {config, ignored};
}
