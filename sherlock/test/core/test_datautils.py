import unittest
from unittest.mock import patch
from datetime import datetime
from dateutil.relativedelta import relativedelta

# =====================================================================
# SUÍTE DE TESTES (COBERTURA DE 100%)
# =====================================================================
class TestDatautils(unittest.TestCase):

    def setUp(self):
        """Mocka o datetime.now() para retornar sempre '2026-08-23' garantindo consistência nos testes."""
        self.mock_now = datetime(2026, 8, 23)
        self.patcher = patch('__main__.datetime')
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.now.return_value = self.mock_now
        self.mock_datetime.strptime = datetime.strptime # Mantém a funcionalidade real do strptime

    def tearDown(self):
        self.patcher.stop()

    def test_default_execution_string_format(self):
        """Testa o cenário padrão (incremental diário) com lag=1 e formato de string."""
        args = {
            'data': {
                'partition': {'lag': 1, 'format': 'YYYY-MM-DD', 'type': 'string'},
                'backfill': {'enabled': False},
                'reprocess': {'enabled': False}
            }
        }
        du = Datautils(args)
        result = du.get_execution_partitions()
        
        # Hoje é 23/08/2026 - lag de 1 = 22/08/2026
        self.assertEqual(result, ['2026-08-22'])

    def test_default_execution_int_format(self):
        """Testa o cenário padrão gerando partição como inteiro (ex: 20260822)."""
        args = {
            'data': {'partition': {'lag': 1, 'format': 'YYYY-MM-DD', 'type': 'int'}}
        }
        du = Datautils(args)
        result = du.get_execution_partitions()
        self.assertEqual(result, [20260822])
        self.assertIsInstance(result[0], int)

    def test_backfill_success(self):
        """Testa o loop de backfill passando datas válidas."""
        args = {
            'data': {
                'backfill': {
                    'enabled': True,
                    'start_date': '2026-01-01',
                    'end_date': '2026-01-03'
                },
                'partition': {'type': 'string', 'format': 'YYYY-MM-DD'}
            }
        }
        du = Datautils(args)
        result = du.get_execution_partitions()
        self.assertEqual(result, ['2026-01-01', '2026-01-02', '2026-01-03'])

    def test_backfill_invalid_date(self):
        """Testa a validação de segurança caso receba uma data inexistente (ex: 30 de Fev)."""
        args = {
            'data': {
                'backfill': {
                    'enabled': True,
                    'start_date': '2026-02-30', # Data Inválida
                    'end_date': '2026-03-01'
                }
            }
        }
        du = Datautils(args)
        with self.assertRaises(ValueError) as context:
            du.get_execution_partitions()
        self.assertIn("Erro no YAML! As datas de backfill são inválidas", str(context.exception))

    def test_reprocess_days(self):
        """Testa o reprocessamento retroagindo em dias."""
        args = {
            'data': {
                'partition': {'lag': 1, 'type': 'string'},
                'reprocess': {'enabled': True, 'range_value': 2, 'range_unit': 'day'}
            }
        }
        du = Datautils(args)
        result = du.get_execution_partitions()
        # Data Base: 22/08. Range: -2 dias = 20/08 até 22/08
        self.assertEqual(result, ['2026-08-20', '2026-08-21', '2026-08-22'])

    def test_reprocess_months(self):
        """Testa o reprocessamento retroagindo meses (segurança do relativedelta)."""
        # Mockando hoje como 30 de Março para testar a volta para Fevereiro
        self.mock_datetime.now.return_value = datetime(2026, 3, 31) 
        
        args = {
            'data': {
                'partition': {'lag': 0, 'type': 'string'}, # Base = 31/03
                'reprocess': {'enabled': True, 'range_value': 1, 'range_unit': 'month'}
            }
        }
        du = Datautils(args)
        result = du.partition_reprocess()
        
        # 1 Mês antes de 31 de Março -> 28 de Fevereiro (2026 não é bissexto)
        self.assertEqual(result[0], '2026-02-28')

    def test_reprocess_years(self):
        """Testa o reprocessamento retroagindo anos."""
        args = {
            'data': {
                'partition': {'lag': 0, 'type': 'string'}, # Base = 23/08/2026
                'reprocess': {'enabled': True, 'range_value': 1, 'range_unit': 'year'}
            }
        }
        du = Datautils(args)
        result = du.partition_reprocess()
        self.assertEqual(result[0], '2025-08-23')

    def test_reprocess_hours(self):
        """Testa o reprocessamento com unidade em horas (apenas formatação)."""
        args = {
            'data': {
                'partition': {'lag': 0, 'type': 'string'},
                'reprocess': {'enabled': True, 'range_value': 24, 'range_unit': 'hour'}
            }
        }
        du = Datautils(args)
        result = du.partition_reprocess()
        # 24 horas antes equivale a 1 dia
        self.assertEqual(result[0], '2026-08-22')

    def test_reprocess_unknown_unit(self):
        """Testa o comportamento de segurança (fallback) caso o range_unit venha errado do YAML."""
        args = {
            'data': {
                'partition': {'lag': 1, 'type': 'string'},
                'reprocess': {'enabled': True, 'range_value': 10, 'range_unit': 'seculo'}
            }
        }
        du = Datautils(args)
        result = du.partition_reprocess()
        # Se falhar no tipo, start_date = end_date (Retorna só a própria data base)
        self.assertEqual(result, ['2026-08-22'])

if __name__ == '__main__':
    unittest.main()