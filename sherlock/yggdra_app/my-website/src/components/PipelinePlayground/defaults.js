// Configuracao de exemplo (espelha o YAML de referencia da pipeline).
export const EXAMPLE_CONFIG = {
  common: {
    owner: 'guilherme.e.oliveira-silva@itau-unibanco.com.br',
    region: 'sa-east-1',
    job_name: '',
    log_level: 'INFO',
  },
  pipeline: {
    target: {database: 'workspace_db', table: 'sepj_sot_ga4_login_new'},
    shared: {
      enabled: true,
      database: 'database_db_compartilhado_consumer_dungeonsedados',
    },
    mode: 'sql',
    sql: {
      path: 's3://itau-self-wkp-sa-east-1-060795934823/SQL_CENTER/sepj_sot_ga4_login.sql',
    },
    data: {
      partition: {name: 'anomesdia', type: 'int', format: 'YYYYMMDD', lag: 2},
      reprocess: {enabled: true, range_value: 1, range_unit: 'month', day_reprocess: 30},
      backfill: {enabled: false, start_date: '2026-07-01', end_date: '2026-08-21'},
    },
    report: {
      enabled: true,
      name_file_temp: 'temp',
      title: 'Relatorio de Execucao Pipeline Tabela sepj_sot_ga4_login_new',
      report: {error: true, success: false},
    },
  },
  heimdall: {
    enabled: true,
    validate: {origins: true, sql: true},
    origins: {
      mode: 'auto',
      auto_mode: {ignore_check_table: ['tb_depara_funis']},
      manual_mode: {tables: []},
    },
    report: {
      enabled: true,
      name_file_temp: 'temp',
      title: 'Relatorio de Segurança da Tabela sepj_spec_ga4_login_new',
      report: {error: true, success: false},
    },
  },
  hermes: {
    enabled: true,
    group_name: 'yggdra_dd',
    members: ['guilherme.e.oliveira-silva@itau-unibanco.com.br'],
  },
};

// Configuracao "em branco": base para "Limpar" e para importar YAML incompleto.
export const BLANK_CONFIG = {
  common: {owner: '', region: 'sa-east-1', job_name: '', log_level: 'INFO'},
  pipeline: {
    target: {database: '', table: ''},
    shared: {enabled: false, database: ''},
    mode: 'sql',
    sql: {path: ''},
    data: {
      partition: {name: 'anomesdia', type: 'int', format: 'YYYYMMDD', lag: 0},
      reprocess: {enabled: false, range_value: 1, range_unit: 'month', day_reprocess: 1},
      backfill: {enabled: false, start_date: '', end_date: ''},
    },
    report: {
      enabled: false,
      name_file_temp: 'temp',
      title: '',
      report: {error: true, success: false},
    },
  },
  heimdall: {
    enabled: false,
    validate: {origins: true, sql: true},
    origins: {mode: 'auto', auto_mode: {ignore_check_table: []}, manual_mode: {tables: []}},
    report: {
      enabled: false,
      name_file_temp: 'temp',
      title: '',
      report: {error: true, success: false},
    },
  },
  hermes: {enabled: false, group_name: '', members: []},
};

export const OPTIONS = {
  logLevels: ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
  regions: ['sa-east-1', 'us-east-1', 'us-east-2', 'us-west-2'],
  modes: [
    {value: 'sql', label: 'SQL (Athena / DataFactory)'},
    {value: 'pyspark', label: 'PySpark (ainda não suportado)'},
  ],
  partitionTypes: ['int', 'string', 'date'],
  partitionFormats: ['YYYYMMDD', 'YYYYMM', 'YYYY', 'MM', 'YYYY-MM-DD'],
  rangeUnits: [
    {value: 'day', label: 'dia(s)'},
    {value: 'month', label: 'mês(es)'},
    {value: 'year', label: 'ano(s)'},
  ],
  originModes: [
    {value: 'auto', label: 'Automático (extrai da query)'},
    {value: 'manual', label: 'Manual (lista de tabelas)'},
  ],
};
