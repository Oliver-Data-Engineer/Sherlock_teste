import React, {useState} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

// ---------------------------------------------------------------------------
// Conteudo: edite aqui textos e links sem mexer no layout.
// ---------------------------------------------------------------------------
const PLAYGROUND = '/pipeline-playground';
const DOCS = '/docs/intro';

const STACK = ['Amazon Athena', 'AWS Glue', 'Amazon S3', 'Amazon DynamoDB', 'Presto SQL'];

const COMPONENTS = [
  {title: ['Heimdall', 'validação prévia'], variant: 'surface', icon: 'shield', to: DOCS},
  {title: ['Processamento', 'em SQL'], variant: 'accent', icon: 'database', to: DOCS},
  {title: ['Hermes', 'notificação'], variant: 'inverse', icon: 'mail', to: DOCS},
  {title: ['Partição e', 'defasagem'], variant: 'surface', icon: 'calendar', to: DOCS},
  {title: ['Janela de', 'reprocessamento'], variant: 'accent', icon: 'loop', to: DOCS},
  {title: ['Carga', 'histórica'], variant: 'inverseAlt', icon: 'timeline', to: DOCS},
];

const SCENARIOS = [
  {
    text: (
      <>
        Tabela diária com dados chegando em D-2: com <code>partition.lag: 2</code>, a partição processada é sempre a de dois dias antes da
        execução.
      </>
    ),
  },
  {
    text: (
      <>
        Fechamento mensal: com <code>range_unit: month</code> e <code>day_reprocess: 30</code>, todo dia 30 a pipeline refaz o último mês.
      </>
    ),
  },
  {
    text: (
      <>
        Carga histórica de uma tabela nova: ligue o <code>backfill</code>, defina <code>start_date</code> e <code>end_date</code> e desligue
        depois da primeira execução.
      </>
    ),
  },
];

const STEPS = [
  {
    title: 'Validação prévia',
    body: 'O Heimdall lê a query, encontra as tabelas de origem e confere se estão prontas. Tabelas em ignore_check_table ficam de fora. Se alguma validação reprovar, a orquestração para aqui.',
  },
  {
    title: 'Cálculo da partição',
    body: 'A partição padrão é a data de execução menos a defasagem (lag), escrita no formato definido em partition.format.',
  },
  {
    title: 'Reprocessamento ou backfill',
    body: 'No dia de corte, a janela configurada em reprocess é processada de novo. Com o backfill ligado, o intervalo entre start_date e end_date é processado.',
  },
  {
    title: 'Execução do SQL',
    body: 'O arquivo .sql guardado no S3 roda no Athena e grava na tabela destino, particionada pela coluna configurada.',
  },
  {
    title: 'Relatórios',
    body: 'Heimdall e pipeline geram relatórios HTML temporários quando há erro, sucesso ou ambos, conforme o bloco report de cada um.',
  },
  {
    title: 'Notificação',
    body: 'O Hermes envia os relatórios por e-mail para os membros do grupo cadastrado no DynamoDB.',
  },
];

// ---------------------------------------------------------------------------
// Ilustracoes (SVG proprio, em traco, no espirito do template)
// ---------------------------------------------------------------------------
const star = (cx, cy, r) =>
  `M${cx} ${cy - r}Q${cx} ${cy} ${cx + r} ${cy}Q${cx} ${cy} ${cx} ${cy + r}Q${cx} ${cy} ${cx - r} ${cy}Q${cx} ${cy} ${cx} ${cy - r}Z`;

function HeroArt() {
  return (
    <svg className={styles.heroArt} viewBox="0 0 520 440" role="img" aria-label="Arquivo YAML cercado por órbitas, representando a pipeline">
      <g fill="none" stroke="currentColor" strokeWidth="1.5">
        <ellipse cx="270" cy="240" rx="235" ry="70" transform="rotate(-24 270 240)" />
        <ellipse cx="270" cy="240" rx="200" ry="58" transform="rotate(-24 270 240)" />
        <ellipse cx="270" cy="240" rx="165" ry="46" transform="rotate(-24 270 240)" />
      </g>
      <g transform="rotate(-8 260 215)">
        <rect x="170" y="95" width="190" height="240" rx="18" style={{fill: 'var(--paper)'}} stroke="currentColor" strokeWidth="2.5" />
        <rect x="170" y="95" width="190" height="42" rx="18" fill="currentColor" />
        <rect x="170" y="118" width="190" height="19" fill="currentColor" />
        <text x="192" y="123" fontSize="16" fontWeight="700" style={{fill: 'var(--paper)'}} fontFamily="inherit">
          pipeline.yaml
        </text>
        {[
          [192, 160, 70, 0],
          [210, 184, 50, 60],
          [210, 208, 44, 70],
          [192, 238, 60, 0],
          [210, 262, 40, 80],
          [210, 286, 56, 50],
        ].map(([x, y, k, v]) => (
          <g key={y}>
            <rect x={x} y={y} width={k} height="9" rx="4.5" fill="currentColor" />
            {v > 0 && <rect x={x + k + 10} y={y} width={v} height="9" rx="4.5" style={{fill: 'var(--o)'}} />}
          </g>
        ))}
      </g>
      <circle cx="378" cy="118" r="30" style={{fill: 'var(--o)'}} stroke="currentColor" strokeWidth="2" />
      <path d="M364 118l10 10 19-20" fill="none" stroke="#000D3C" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="455" cy="205" r="26" fill="currentColor" />
      <path d="M443 197h24v16h-24zM443 197l12 9 12-9" fill="none" style={{stroke: 'var(--paper)'}} strokeWidth="2.5" strokeLinejoin="round" />
      <circle cx="120" cy="120" r="14" fill="currentColor" />
      <circle cx="150" cy="160" r="8" style={{fill: 'var(--o)'}} />
      <circle cx="400" cy="345" r="7" style={{fill: 'var(--o)'}} />
      <path d={star(92, 300, 38)} fill="currentColor" />
      <path d={star(330, 395, 16)} fill="currentColor" />
      <path d={star(470, 70, 20)} style={{fill: 'var(--o)'}} />
    </svg>
  );
}

function CtaArt() {
  return (
    <svg className={styles.ctaArt} viewBox="0 0 360 260" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1.5">
        <ellipse cx="170" cy="150" rx="140" ry="22" />
        <ellipse cx="170" cy="138" rx="140" ry="22" />
        <ellipse cx="170" cy="126" rx="140" ry="22" />
      </g>
      <circle cx="170" cy="112" r="56" fill="currentColor" />
      <circle cx="170" cy="112" r="30" fill="none" style={{stroke: 'var(--o)'}} strokeWidth="6" />
      <path d={star(290, 160, 48)} fill="#CFD1D3" />
      <path d={star(80, 205, 46)} style={{fill: 'var(--o)'}} />
      <path d={star(250, 36, 18)} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

const ICONS = {
  shield: (
    <>
      <path d="M60 12l38 14v26c0 26-17 42-38 50-21-8-38-24-38-50V26z" />
      <path d="M42 56l13 13 25-27" strokeWidth="4" style={{stroke: 'var(--art-accent)'}} />
    </>
  ),
  database: (
    <>
      <ellipse cx="50" cy="24" rx="32" ry="11" />
      <path d="M18 24v56c0 6 14 11 32 11s32-5 32-11V24M18 52c0 6 14 11 32 11s32-5 32-11" />
      <path d="M92 58h24m-8-8l8 8-8 8" strokeWidth="3" style={{stroke: 'var(--art-accent)'}} />
    </>
  ),
  mail: (
    <>
      <rect x="14" y="26" width="92" height="62" rx="8" />
      <path d="M14 30l46 32 46-32" />
      <circle cx="102" cy="26" r="12" style={{fill: 'var(--art-accent)'}} stroke="none" />
    </>
  ),
  calendar: (
    <>
      <rect x="14" y="20" width="92" height="78" rx="8" />
      <path d="M14 42h92M36 12v16M84 12v16" />
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={24 + i * 20} y="54" width="12" height="12" rx="2" />
      ))}
      <rect x="84" y="74" width="12" height="12" rx="2" style={{fill: 'var(--art-accent)'}} stroke="none" />
    </>
  ),
  loop: (
    <>
      <path d="M92 44a34 34 0 0 0-62-8M28 72a34 34 0 0 0 62 8" />
      <path d="M26 20v18h18M94 96V78H76" strokeWidth="3" style={{stroke: 'var(--art-accent)'}} />
    </>
  ),
  timeline: (
    <>
      <path d="M14 96h96" />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={20 + i * 18} y={80 - i * 14} width="12" height={16 + i * 14} rx="2" style={{fill: i === 4 ? 'var(--art-accent)' : 'none'}} />
      ))}
    </>
  ),
};

function Icon({name}) {
  return (
    <svg className={styles.cardArt} viewBox="0 0 120 110" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {ICONS[name]}
    </svg>
  );
}

function ArrowCircle() {
  return (
    <span className={styles.arrowCircle} aria-hidden="true">
      <svg viewBox="0 0 20 20" width="18" height="18">
        <path d="M5 15L15 5M7 5h8v8" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Secoes
// ---------------------------------------------------------------------------
function SectionHead({title, children}) {
  return (
    <div className={styles.sectionHead}>
      <Heading as="h2" className={styles.label}>
        {title}
      </Heading>
      <p>{children}</p>
    </div>
  );
}

function Steps() {
  const [open, setOpen] = useState(0);
  return (
    <ol className={styles.steps}>
      {STEPS.map((s, i) => {
        const isOpen = open === i;
        const id = `step-${i}`;
        return (
          <li key={s.title} className={clsx(styles.step, isOpen && styles.stepOpen)}>
            <h3 className={styles.stepHeading}>
              <button type="button" className={styles.stepButton} aria-expanded={isOpen} aria-controls={id} onClick={() => setOpen(isOpen ? -1 : i)}>
                <span className={styles.stepNumber}>{String(i + 1).padStart(2, '0')}</span>
                <span className={styles.stepTitle}>{s.title}</span>
                <span className={styles.stepToggle} aria-hidden="true">
                  {isOpen ? '−' : '+'}
                </span>
              </button>
            </h3>
            <div id={id} className={styles.stepBody} hidden={!isOpen}>
              <p>{s.body}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <main className={styles.home}>
        <div className={styles.wrap}>
          <section className={styles.hero}>
            <div>
              <Heading as="h1">Pipelines de dados que se validam antes de rodar</Heading>
              <p className={styles.lead}>
                Descreva a tabela, o SQL e as regras de partição em um único YAML. O Heimdall confere as origens, a pipeline processa e o Hermes
                avisa o time por e-mail.
              </p>
              <div className={styles.actions}>
                <Link className={styles.btnDark} to={PLAYGROUND}>
                  Testar uma configuração
                </Link>
                <Link className={styles.btnGhost} to={DOCS}>
                  Ler a documentação
                </Link>
              </div>
            </div>
            <HeroArt />
          </section>

          <section className={styles.stack} aria-label="Tecnologias usadas">
            <span className={styles.stackLabel}>Roda sobre</span>
            <ul>
              {STACK.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </section>

          <SectionHead title="Componentes">
            Cada bloco do YAML controla uma etapa. Heimdall e Hermes podem ser desligados sem afetar o processamento.
          </SectionHead>
          <div className={styles.cards}>
            {COMPONENTS.map((c) => (
              <article key={c.title.join(' ')} className={clsx(styles.card, styles[c.variant])}>
                <div className={styles.cardText}>
                  <Heading as="h3" className={styles.cardTitle}>
                    {c.title.map((line) => (
                      <span key={line}>{line}</span>
                    ))}
                  </Heading>
                  <Link className={styles.more} to={c.to} aria-label={`Saiba mais sobre ${c.title.join(' ')}`}>
                    <ArrowCircle />
                    Saiba mais
                  </Link>
                </div>
                <Icon name={c.icon} />
              </article>
            ))}
          </div>

          <section className={styles.cta}>
            <div>
              <Heading as="h2">Teste antes de subir para produção</Heading>
              <p>
                Monte o YAML no simulador, veja qual partição seria processada em qualquer data e baixe o arquivo pronto, sem erro de
                digitação.
              </p>
              <Link className={styles.btnDark} to={PLAYGROUND}>
                Abrir o simulador
              </Link>
            </div>
            <CtaArt />
          </section>

          <SectionHead title="Cenários">Configurações comuns e o trecho do YAML que resolve cada uma.</SectionHead>
          <section className={styles.cases}>
            {SCENARIOS.map((s, i) => (
              // eslint-disable-next-line react/no-array-index-key
              <div key={i} className={styles.case}>
                <p>{s.text}</p>
                <Link to={PLAYGROUND} className={styles.caseLink}>
                  Simular este cenário
                  <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
                    <path d="M5 15L15 5M7 5h8v8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </Link>
              </div>
            ))}
          </section>

          <SectionHead title="Como funciona">O que acontece, em ordem, a cada execução da pipeline.</SectionHead>
          <Steps />
        </div>
      </main>
    </Layout>
  );
}
