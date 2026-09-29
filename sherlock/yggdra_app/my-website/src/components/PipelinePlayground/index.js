import React, {createContext, useCallback, useContext, useEffect, useId, useMemo, useRef, useState} from 'react';
import clsx from 'clsx';
import CodeBlock from '@theme/CodeBlock';
import {BLANK_CONFIG, EXAMPLE_CONFIG, OPTIONS} from './defaults';
import {fromYaml, toYaml} from './yaml';
import {addDays, diffDays, parseISO, simulate, toBR, toISO, validate} from './rules';
import styles from './styles.module.css';

// ---------------------------------------------------------------------------
// Etapas do formulario. "match" liga cada erro/aviso a uma etapa.
// ---------------------------------------------------------------------------
const SECTIONS = [
  {
    id: 'geral',
    title: 'Geral',
    hint: 'Responsável e ambiente',
    desc: 'Quem responde pela pipeline e onde ela roda. Vale para Heimdall, pipeline e Hermes.',
    match: (p) => p.startsWith('common.'),
  },
  {
    id: 'destino',
    title: 'Destino e SQL',
    hint: 'Tabela e query',
    desc: 'Onde os dados são gravados e qual arquivo SQL gera esses dados.',
    match: (p) => /^pipeline\.(target|shared|mode|sql)/.test(p),
  },
  {
    id: 'datas',
    title: 'Partição e datas',
    hint: 'Defasagem, reprocesso, backfill',
    desc: 'Qual data cada execução processa, quando reprocessar e como fazer cargas históricas.',
    match: (p) => p.startsWith('pipeline.data.'),
  },
  {
    id: 'heimdall',
    title: 'Heimdall',
    hint: 'Validação antes de rodar',
    desc: 'Confere origens e SQL antes do processamento. Se algo reprovar, a orquestração para.',
    match: (p) => p.startsWith('heimdall.'),
  },
  {
    id: 'aviso',
    title: 'Relatórios e e-mail',
    hint: 'Relatório e Hermes',
    desc: 'O relatório da execução e quem recebe o e-mail no fim da pipeline.',
    match: (p) => p.startsWith('pipeline.report') || p.startsWith('hermes.'),
  },
];
const sectionOf = (path) => (SECTIONS.find((s) => s.match(path)) || SECTIONS[0]).id;

// ---------------------------------------------------------------------------
// Estado compartilhado
// ---------------------------------------------------------------------------
const getIn = (obj, path) => path.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
function setIn(obj, path, value) {
  const [k, ...rest] = path.split('.');
  const copy = Array.isArray(obj) ? [...obj] : {...obj};
  copy[k] = rest.length ? setIn(obj[k], rest.join('.'), value) : value;
  return copy;
}

const ConfigContext = createContext(null);

function useField(path) {
  const {config, set, issuesByPath} = useContext(ConfigContext);
  return {
    value: getIn(config, path),
    onChange: (v) => set(path, v),
    issues: issuesByPath[path] || [],
  };
}

const hasError = (issues) => issues.some((i) => i.level === 'error');

// ---------------------------------------------------------------------------
// Campos
// ---------------------------------------------------------------------------
function Issues({issues}) {
  return issues.map((i) => (
    <p key={i.message} className={clsx(styles.issue, styles[i.level])}>
      {i.message}
    </p>
  ));
}

function Field({id, label, hint, issues, wide, children}) {
  return (
    <div className={clsx(styles.field, wide && styles.wide, hasError(issues) && styles.hasError)}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      {children}
      {hint && <p className={styles.hint}>{hint}</p>}
      <Issues issues={issues} />
    </div>
  );
}

function TextField({path, label, hint, placeholder, mono, wide, type = 'text', list}) {
  const id = useId();
  const {value, onChange, issues} = useField(path);
  return (
    <Field id={id} label={label} hint={hint} issues={issues} wide={wide}>
      <input
        id={id}
        data-path={path}
        type={type}
        list={list}
        className={clsx(styles.input, mono && styles.mono)}
        value={value ?? ''}
        placeholder={placeholder}
        aria-invalid={hasError(issues)}
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  );
}

function NumberField({path, label, hint, min, max}) {
  const id = useId();
  const {value, onChange, issues} = useField(path);
  return (
    <Field id={id} label={label} hint={hint} issues={issues}>
      <input
        id={id}
        data-path={path}
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        className={styles.input}
        value={value ?? ''}
        aria-invalid={hasError(issues)}
        onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
      />
    </Field>
  );
}

function SelectField({path, label, hint, options, wide}) {
  const id = useId();
  const {value, onChange, issues} = useField(path);
  return (
    <Field id={id} label={label} hint={hint} issues={issues} wide={wide}>
      <select id={id} data-path={path} className={styles.input} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => {
          const opt = typeof o === 'string' ? {value: o, label: o} : o;
          return (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          );
        })}
      </select>
    </Field>
  );
}

// Linha de configuracao liga/desliga (texto a esquerda, chave a direita).
function Setting({path, label, hint, wide}) {
  const id = useId();
  const {value, onChange, issues} = useField(path);
  return (
    <div className={clsx(styles.setting, wide && styles.wide)}>
      <div className={styles.settingText}>
        <label htmlFor={id}>{label}</label>
        {hint && <p className={styles.hint}>{hint}</p>}
        <Issues issues={issues} />
      </div>
      <input
        id={id}
        data-path={path}
        type="checkbox"
        role="switch"
        className={styles.switch}
        checked={!!value}
        onChange={(e) => onChange(e.target.checked)}
      />
    </div>
  );
}

// Chave compacta usada no cabecalho de grupos e etapas.
function InlineSwitch({path, label}) {
  const id = useId();
  const {value, onChange} = useField(path);
  return (
    <div className={styles.inlineSwitch}>
      <label htmlFor={id}>{value ? 'Ligado' : 'Desligado'}</label>
      <input
        id={id}
        data-path={path}
        type="checkbox"
        role="switch"
        aria-label={label}
        className={styles.switch}
        checked={!!value}
        onChange={(e) => onChange(e.target.checked)}
      />
    </div>
  );
}

function ListField({path, label, hint, placeholder, addLabel}) {
  const {value, onChange, issues} = useField(path);
  const items = value || [];
  const update = (i, v) => onChange(items.map((x, idx) => (idx === i ? v : x)));
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i));
  return (
    <div className={clsx(styles.field, styles.wide, hasError(issues) && styles.hasError)} data-path={path} tabIndex={-1}>
      <span className={styles.label}>{label}</span>
      {hint && <p className={styles.hint}>{hint}</p>}
      <div className={styles.list}>
        {items.map((item, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <div key={i} className={styles.listRow}>
            <input
              className={clsx(styles.input, styles.mono)}
              value={item}
              placeholder={placeholder}
              aria-label={`${label} ${i + 1}`}
              onChange={(e) => update(i, e.target.value)}
            />
            <button type="button" className={clsx(styles.btn, styles.btnGhost, styles.btnSm)} onClick={() => remove(i)} aria-label={`Remover ${item || 'item vazio'}`}>
              Remover
            </button>
          </div>
        ))}
        <button type="button" className={clsx(styles.btn, styles.btnGhost, styles.btnSm, styles.addButton)} onClick={() => onChange([...items, ''])}>
          + {addLabel}
        </button>
      </div>
      <Issues issues={issues} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Estrutura
// ---------------------------------------------------------------------------
function Group({title, hint, togglePath, offText = 'Desligado.', children}) {
  const {config, issuesByPath} = useContext(ConfigContext);
  const on = togglePath ? !!getIn(config, togglePath) : true;
  return (
    <div className={styles.group}>
      <div className={styles.groupHead}>
        <div>
          <h3>{title}</h3>
          {hint && <p className={styles.hint}>{hint}</p>}
        </div>
        {togglePath && <InlineSwitch path={togglePath} label={title} />}
      </div>
      {togglePath && <Issues issues={issuesByPath[togglePath] || []} />}
      {on ? <div className={styles.grid}>{children}</div> : <p className={styles.off}>{offText}</p>}
    </div>
  );
}

function ReportGroup({base, title}) {
  return (
    <Group title={title} hint="Arquivo HTML que o Hermes envia por e-mail." togglePath={`${base}.enabled`} offText="Desligado. Nenhum relatório é gerado.">
      <TextField path={`${base}.title`} label="Título" wide />
      <TextField path={`${base}.name_file_temp`} label="Arquivo temporário" mono />
      <div />
      <Setting path={`${base}.report.error`} label="Gerar quando houver erro" />
      <Setting path={`${base}.report.success`} label="Gerar quando houver sucesso" />
    </Group>
  );
}

function Panel({index, togglePath, offText, onPrev, onNext, children}) {
  const section = SECTIONS[index];
  const {config, issuesByPath} = useContext(ConfigContext);
  const on = togglePath ? !!getIn(config, togglePath) : true;
  const next = SECTIONS[index + 1];
  const headingId = `pp-${section.id}`;
  return (
    <section className={styles.panel} aria-labelledby={headingId}>
      <header className={styles.panelHead}>
        <div>
          <p className={styles.stepOf}>
            Etapa {index + 1} de {SECTIONS.length}
          </p>
          <h2 id={headingId} className={styles.panelTitle}>
            {section.title}
          </h2>
          <p className={styles.panelDesc}>{section.desc}</p>
        </div>
        {togglePath && <InlineSwitch path={togglePath} label={section.title} />}
      </header>
      <div className={styles.panelBody}>
        {togglePath && <Issues issues={issuesByPath[togglePath] || []} />}
        {on ? children : <p className={clsx(styles.off, styles.offLarge)}>{offText}</p>}
      </div>
      <footer className={styles.panelFoot}>
        {index > 0 ? (
          <button type="button" className={clsx(styles.btn, styles.btnGhost)} onClick={onPrev}>
            ← {SECTIONS[index - 1].title}
          </button>
        ) : (
          <span />
        )}
        {next && (
          <button type="button" className={clsx(styles.btn, styles.btnDark)} onClick={onNext}>
            Próximo: {next.title} →
          </button>
        )}
      </footer>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Conteudo de cada etapa
// ---------------------------------------------------------------------------
function StepGeral() {
  return (
    <Group title="Identificação">
      <TextField path="common.owner" label="Responsável (e-mail)" type="email" placeholder="nome@itau-unibanco.com.br" wide />
      <TextField path="common.region" label="Região AWS" list="pp-regions" mono />
      <datalist id="pp-regions">
        {OPTIONS.regions.map((r) => (
          <option key={r} value={r} />
        ))}
      </datalist>
      <SelectField path="common.log_level" label="Nível de log" options={OPTIONS.logLevels} />
      <TextField path="common.job_name" label="Job Glue (opcional)" hint="Vazio pula o backup do script e omite a chave no YAML." mono wide />
    </Group>
  );
}

function StepDestino() {
  return (
    <>
      <Group title="Tabela destino">
        <TextField path="pipeline.target.database" label="Database" mono />
        <TextField path="pipeline.target.table" label="Tabela" mono />
      </Group>
      <Group
        title="Database compartilhado"
        hint="Ainda não suportado pela pipeline."
        togglePath="pipeline.shared.enabled"
        offText="Desligado. A tabela é gravada no database acima.">
        <TextField path="pipeline.shared.database" label="Database compartilhado" mono wide />
      </Group>
      <Group title="Origem do SQL">
        <SelectField path="pipeline.mode" label="Motor" options={OPTIONS.modes} wide />
        <TextField path="pipeline.sql.path" label="Arquivo SQL no S3" placeholder="s3://bucket/pasta/arquivo.sql" mono wide />
      </Group>
    </>
  );
}

function StepDatas() {
  return (
    <>
      <Group title="Partição" hint="Define qual data cada execução processa.">
        <TextField path="pipeline.data.partition.name" label="Coluna" mono />
        <NumberField path="pipeline.data.partition.lag" label="Defasagem (dias)" hint="Partição padrão = data da execução − defasagem." min={0} />
        <SelectField path="pipeline.data.partition.type" label="Tipo" options={OPTIONS.partitionTypes} />
        <SelectField path="pipeline.data.partition.format" label="Formato" options={OPTIONS.partitionFormats} />
      </Group>
      <Group
        title="Reprocessamento"
        hint="Refaz uma janela de dados no dia de corte."
        togglePath="pipeline.data.reprocess.enabled"
        offText="Desligado. Só a partição padrão é processada.">
        <NumberField path="pipeline.data.reprocess.range_value" label="Período" min={1} />
        <SelectField path="pipeline.data.reprocess.range_unit" label="Unidade" options={OPTIONS.rangeUnits} />
        <NumberField path="pipeline.data.reprocess.day_reprocess" label="Dia de corte" hint="Dia do mês em que o reprocessamento roda." min={1} max={31} />
      </Group>
      <Group title="Backfill" hint="Carga manual de um intervalo de datas." togglePath="pipeline.data.backfill.enabled" offText="Desligado.">
        <TextField path="pipeline.data.backfill.start_date" label="Data inicial" type="date" />
        <TextField path="pipeline.data.backfill.end_date" label="Data final" type="date" />
      </Group>
    </>
  );
}

function StepHeimdall() {
  const {config} = useContext(ConfigContext);
  return (
    <>
      <Group title="Validações">
        <Setting path="heimdall.validate.origins" label="Prontidão das origens" hint="Confere se as tabelas de origem estão atualizadas." />
        <Setting path="heimdall.validate.sql" label="Sintaxe do SQL" hint="Valida a query antes de rodar." />
      </Group>
      <Group title="Origens">
        <SelectField path="heimdall.origins.mode" label="Como encontrar as origens" options={OPTIONS.originModes} wide />
        {config.heimdall.origins.mode === 'manual' ? (
          <ListField path="heimdall.origins.manual_mode.tables" label="Tabelas de origem" placeholder="database.tabela" addLabel="Adicionar tabela" />
        ) : (
          <ListField
            path="heimdall.origins.auto_mode.ignore_check_table"
            label="Tabelas a não checar"
            hint="Aparecem na query, mas ficam fora da checagem de prontidão."
            placeholder="nome_da_tabela"
            addLabel="Adicionar tabela"
          />
        )}
      </Group>
      <ReportGroup base="heimdall.report" title="Relatório de auditoria" />
    </>
  );
}

function StepAviso() {
  return (
    <>
      <ReportGroup base="pipeline.report" title="Relatório de execução" />
      <Group
        title="Hermes"
        hint="Envia os relatórios por e-mail. Requer iara_beholder_logs no cluster."
        togglePath="hermes.enabled"
        offText="Desligado. Os relatórios são gerados, mas ninguém recebe e-mail.">
        <TextField path="hermes.group_name" label="Grupo no DynamoDB" mono wide />
        <ListField path="hermes.members" label="Destinatários" placeholder="nome@itau-unibanco.com.br" addLabel="Adicionar destinatário" />
      </Group>
    </>
  );
}

// ---------------------------------------------------------------------------
// Painel de saida: YAML, simulacao e validacao
// ---------------------------------------------------------------------------
const MAX_CELLS = 63;

function DayStrip({sim}) {
  const {runDate, ref, reprocess} = sim;
  const showWindow = reprocess && reprocess.isCutDay;
  let start = addDays(ref, -6);
  if (showWindow && reprocess.from < start) start = reprocess.from;
  let truncated = false;
  if (diffDays(start, runDate) + 1 > MAX_CELLS) {
    start = addDays(runDate, -(MAX_CELLS - 1));
    truncated = true;
  }
  const days = [];
  for (let d = start; d <= runDate; d = addDays(d, 1)) days.push(d);

  return (
    <div className={styles.timeline}>
      <ol className={styles.strip} aria-label="Linha do tempo da execução simulada">
        {days.map((d) => {
          const isRef = +d === +ref;
          const isRun = +d === +runDate;
          const pending = d > ref && d < runDate;
          const inWindow = showWindow && d >= reprocess.from && d <= reprocess.to;
          const tags = [isRef && 'partição padrão', inWindow && 'reprocessada', pending && 'dentro da defasagem', isRun && 'dia da execução'].filter(Boolean);
          return (
            <li
              key={+d}
              title={`${toBR(d)}${tags.length ? `: ${tags.join(', ')}` : ''}`}
              className={clsx(
                styles.day,
                inWindow && styles.dayWindow,
                pending && styles.dayPending,
                isRef && styles.dayPartition,
                isRun && styles.dayRun,
                d.getDate() === 1 && styles.dayFirst,
              )}>
              {d.getDate()}
            </li>
          );
        })}
      </ol>
      <ul className={styles.legend}>
        <li>
          <span className={clsx(styles.swatch, styles.dayPartition)} />
          Partição padrão
        </li>
        {showWindow && (
          <li>
            <span className={clsx(styles.swatch, styles.dayWindow)} />
            Reprocessada
          </li>
        )}
        {sim.lag > 1 && (
          <li>
            <span className={clsx(styles.swatch, styles.dayPending)} />
            Defasagem
          </li>
        )}
        <li>
          <span className={clsx(styles.swatch, styles.dayRun)} />
          Execução
        </li>
      </ul>
      {truncated && <p className={styles.hint}>Janela longa demais para exibir inteira. Mostrando os últimos {MAX_CELLS} dias.</p>}
    </div>
  );
}

function SimulationTab({sim, simDate, setSimDate}) {
  const id = useId();
  const rp = sim && sim.reprocess;
  return (
    <>
      <div className={styles.simDate}>
        <label htmlFor={id}>Simular execução em</label>
        <input id={id} type="date" className={styles.input} value={simDate} onChange={(e) => setSimDate(e.target.value)} />
      </div>
      {!sim ? (
        <p className={styles.hint}>Escolha uma data para ver o que a pipeline processaria.</p>
      ) : (
        <>
          <dl className={styles.facts}>
            <div className={styles.fact}>
              <dt>Partição padrão</dt>
              <dd>
                <strong className={styles.bigValue}>{sim.partition}</strong>
                <span className={styles.hint}>
                  {toBR(sim.ref)}, {sim.lag} {sim.lag === 1 ? 'dia' : 'dias'} antes da execução
                </span>
              </dd>
            </div>
            <div className={styles.fact}>
              <dt>Reprocessamento</dt>
              <dd>
                {!rp && 'Desligado.'}
                {rp && rp.isCutDay && (
                  <>
                    Dia de corte. Reprocessa de <code>{rp.fromLabel}</code> a <code>{rp.toLabel}</code> ({rp.days} dias).
                  </>
                )}
                {rp && !rp.isCutDay && (
                  <>
                    Não roda nesta data.{' '}
                    {rp.nextCut ? (
                      <>
                        Próximo corte em {toBR(rp.nextCut)}.{' '}
                        <button type="button" className={styles.linkButton} onClick={() => setSimDate(toISO(rp.nextCut))}>
                          Simular nesse dia
                        </button>
                      </>
                    ) : (
                      'Dia de corte inválido.'
                    )}
                  </>
                )}
              </dd>
            </div>
            <div className={styles.fact}>
              <dt>Backfill</dt>
              <dd>
                {sim.backfill ? (
                  <>
                    Carga de <code>{sim.backfill.fromLabel}</code> a <code>{sim.backfill.toLabel}</code> ({sim.backfill.days} dias).
                  </>
                ) : (
                  'Desligado ou com datas inválidas.'
                )}
              </dd>
            </div>
          </dl>
          <DayStrip sim={sim} />
        </>
      )}
    </>
  );
}

function ValidationTab({errors, warnings, onGo}) {
  if (!errors.length && !warnings.length) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyIcon} aria-hidden="true">
          ✓
        </span>
        <p>Nenhum problema encontrado. O YAML está pronto para uso.</p>
      </div>
    );
  }
  return (
    <ul className={styles.issueList}>
      {[...errors, ...warnings].map((i) => (
        <li key={i.path + i.message}>
          <button type="button" className={clsx(styles.issueItem, styles[i.level])} onClick={() => onGo(i.path)}>
            <span className={styles.issueMeta}>
              {i.level === 'error' ? 'Erro' : 'Aviso'} em {SECTIONS.find((s) => s.id === sectionOf(i.path)).title}
            </span>
            <span>{i.message}</span>
            <span className={styles.issueGo}>Ir para o campo</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Pagina
// ---------------------------------------------------------------------------
export default function PipelinePlayground() {
  const [config, setConfig] = useState(EXAMPLE_CONFIG);
  const [active, setActive] = useState(0);
  const [tab, setTab] = useState('yaml');
  const [focusPath, setFocusPath] = useState(null);
  const [today, setToday] = useState(null);
  const [simDate, setSimDate] = useState('');
  const [importText, setImportText] = useState('');
  const [importError, setImportError] = useState('');
  const [flash, setFlash] = useState('');
  const dialogRef = useRef(null);

  // "Hoje" so e definido no navegador para nao divergir do HTML gerado no build.
  useEffect(() => {
    const t = new Date();
    t.setHours(0, 0, 0, 0);
    setToday(t);
    setSimDate(toISO(t));
  }, []);

  // Leva o foco ao campo escolhido na lista de validacao.
  useEffect(() => {
    if (!focusPath) return undefined;
    const raf = requestAnimationFrame(() => {
      const el = document.querySelector(`[data-path="${focusPath}"]`);
      if (el) {
        el.scrollIntoView({block: 'center', behavior: 'smooth'});
        el.focus({preventScroll: true});
      }
      setFocusPath(null);
    });
    return () => cancelAnimationFrame(raf);
  }, [focusPath, active]);

  useEffect(() => {
    if (!flash) return undefined;
    const t = setTimeout(() => setFlash(''), 6000);
    return () => clearTimeout(t);
  }, [flash]);

  const set = useCallback((path, v) => setConfig((c) => setIn(c, path, v)), []);
  const issues = useMemo(() => validate(config, today), [config, today]);
  const issuesByPath = useMemo(
    () => issues.reduce((acc, i) => ({...acc, [i.path]: [...(acc[i.path] || []), i]}), {}),
    [issues],
  );
  const perSection = useMemo(() => {
    const out = Object.fromEntries(SECTIONS.map((s) => [s.id, {error: 0, warning: 0}]));
    issues.forEach((i) => {
      out[sectionOf(i.path)][i.level] += 1;
    });
    return out;
  }, [issues]);
  const yamlText = useMemo(() => toYaml(config), [config]);
  const sim = useMemo(() => {
    const d = parseISO(simDate);
    return d ? simulate(config, d) : null;
  }, [config, simDate]);

  const errors = issues.filter((i) => i.level === 'error');
  const warnings = issues.filter((i) => i.level === 'warning');
  const fileName = `${(config.pipeline.target.table || 'pipeline').trim()}.yaml`;

  const goTo = (i) => {
    setActive(i);
    if (typeof window !== 'undefined') {
      const top = document.getElementById('pp-top');
      if (top && top.getBoundingClientRect().top < 0) top.scrollIntoView({behavior: 'smooth'});
    }
  };
  const goToField = (path) => {
    setActive(SECTIONS.findIndex((s) => s.id === sectionOf(path)));
    setFocusPath(path);
  };

  const openImport = () => {
    setImportError('');
    dialogRef.current?.showModal();
  };
  const applyImport = () => {
    try {
      const {config: next, ignored} = fromYaml(importText);
      setConfig(next);
      setActive(0);
      dialogRef.current?.close();
      setFlash(
        ignored.length ? `Configuração importada. Chaves desconhecidas ignoradas: ${ignored.join(', ')}.` : 'Configuração importada.',
      );
    } catch (e) {
      setImportError(e.message);
    }
  };

  const download = () => {
    const blob = new Blob([yamlText], {type: 'text/yaml;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const status = errors.length
    ? {cls: styles.pillError, text: `${errors.length} ${errors.length === 1 ? 'erro' : 'erros'}`}
    : warnings.length
      ? {cls: styles.pillWarn, text: `${warnings.length} ${warnings.length === 1 ? 'aviso' : 'avisos'}`}
      : {cls: styles.pillOk, text: 'Pronta para rodar'};

  const steps = [StepGeral, StepDestino, StepDatas, StepHeimdall, StepAviso];
  const Step = steps[active];
  const panelToggle = {
    heimdall: {togglePath: 'heimdall.enabled', offText: 'Heimdall desligado. A pipeline roda sem validação prévia.'},
  }[SECTIONS[active].id];

  return (
    <ConfigContext.Provider value={{config, set, issuesByPath}}>
      <div className={styles.root}>
        <header id="pp-top" className={styles.top}>
          <div>
            <h1>Testar configuração da pipeline</h1>
            <p>Preencha as etapas, confira a simulação e baixe o YAML. Tudo roda no seu navegador: nada é enviado.</p>
          </div>
          <div className={styles.topActions}>
            <button type="button" className={clsx(styles.pill, status.cls)} onClick={() => setTab('val')}>
              {status.text}
            </button>
            <button type="button" className={clsx(styles.btn, styles.btnGhost)} onClick={openImport}>
              Importar YAML
            </button>
            <button type="button" className={clsx(styles.btn, styles.btnGhost)} onClick={() => setConfig(EXAMPLE_CONFIG)}>
              Exemplo
            </button>
            <button type="button" className={clsx(styles.btn, styles.btnGhost)} onClick={() => setConfig(BLANK_CONFIG)}>
              Limpar
            </button>
            <button type="button" className={clsx(styles.btn, styles.btnPrimary)} onClick={download}>
              Baixar YAML
            </button>
          </div>
        </header>

        {flash && (
          <p className={styles.flash} role="status">
            {flash}
          </p>
        )}

        <div className={styles.layout}>
          <nav className={styles.nav} aria-label="Etapas da configuração">
            <ol>
              {SECTIONS.map((s, i) => {
                const c = perSection[s.id];
                return (
                  <li key={s.id}>
                    <button type="button" className={styles.navItem} aria-current={active === i ? 'step' : undefined} onClick={() => goTo(i)}>
                      <span className={styles.navNum}>{i + 1}</span>
                      <span className={styles.navText}>
                        <strong>{s.title}</strong>
                        <small>{s.hint}</small>
                      </span>
                      {c.error > 0 ? (
                        <span className={clsx(styles.navBadge, styles.navBadgeError)} aria-label={`${c.error} erros`}>
                          {c.error}
                        </span>
                      ) : c.warning > 0 ? (
                        <span className={clsx(styles.navBadge, styles.navBadgeWarn)} aria-label={`${c.warning} avisos`}>
                          {c.warning}
                        </span>
                      ) : (
                        <span className={clsx(styles.navBadge, styles.navBadgeOk)} aria-label="Sem problemas">
                          ✓
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>

          <div className={styles.main}>
            <Panel
              key={SECTIONS[active].id}
              index={active}
              togglePath={panelToggle?.togglePath}
              offText={panelToggle?.offText}
              onPrev={() => goTo(active - 1)}
              onNext={() => goTo(active + 1)}>
              <Step />
            </Panel>
          </div>

          <aside className={styles.output} aria-label="Resultado">
            <div className={styles.tabs} role="tablist" aria-label="Resultado">
              {[
                {id: 'yaml', label: 'YAML'},
                {id: 'sim', label: 'Simulação'},
                {id: 'val', label: 'Validação', count: errors.length + warnings.length},
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  id={`pp-tab-${t.id}`}
                  aria-selected={tab === t.id}
                  aria-controls={`pp-tabpanel-${t.id}`}
                  className={styles.tab}
                  onClick={() => setTab(t.id)}>
                  {t.label}
                  {t.count > 0 && <span className={clsx(styles.tabCount, errors.length && styles.tabCountError)}>{t.count}</span>}
                </button>
              ))}
            </div>

            <div className={styles.outBody} role="tabpanel" id={`pp-tabpanel-${tab}`} aria-labelledby={`pp-tab-${tab}`}>
              {tab === 'yaml' && (
                <>
                  {errors.length > 0 && (
                    <p className={clsx(styles.issue, styles.error)}>
                      Há {errors.length} {errors.length === 1 ? 'erro' : 'erros'}. Corrija antes de usar este arquivo.
                    </p>
                  )}
                  <div className={styles.code}>
                    <CodeBlock language="yaml" title={fileName}>
                      {yamlText}
                    </CodeBlock>
                  </div>
                </>
              )}
              {tab === 'sim' && <SimulationTab sim={sim} simDate={simDate} setSimDate={setSimDate} />}
              {tab === 'val' && <ValidationTab errors={errors} warnings={warnings} onGo={goToField} />}
            </div>
          </aside>
        </div>

        <dialog ref={dialogRef} className={styles.dialog} aria-labelledby="pp-import-title">
          <div className={styles.dialogBody}>
            <h2 id="pp-import-title">Importar YAML</h2>
            <p className={styles.hint}>Cole o conteúdo de um arquivo de configuração existente. Os campos serão preenchidos com esses valores.</p>
            <textarea
              aria-label="Conteúdo do YAML"
              className={clsx(styles.input, styles.mono, styles.textarea)}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              spellCheck={false}
            />
            {importError && <p className={clsx(styles.issue, styles.error)}>{importError}</p>}
            <div className={styles.dialogActions}>
              <button type="button" className={clsx(styles.btn, styles.btnGhost)} onClick={() => dialogRef.current?.close()}>
                Cancelar
              </button>
              <button type="button" className={clsx(styles.btn, styles.btnPrimary)} onClick={applyImport} disabled={!importText.trim()}>
                Carregar configuração
              </button>
            </div>
          </div>
        </dialog>
      </div>
    </ConfigContext.Provider>
  );
}
