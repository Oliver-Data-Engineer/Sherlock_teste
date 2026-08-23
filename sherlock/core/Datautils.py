from datetime import datetime
from dateutil.relativedelta import relativedelta

class Datautils: 
    def __init__(self, args):
        self.cfg = args.get('data', {})
        self.cfg_partition = self.cfg.get('partition', {})
        self.cfg_reprocess = self.cfg.get('reprocess', {})
        self.cfg_backfill = self.cfg.get('backfill', {})
        
        self.lag = self.cfg_partition.get('lag', 1)
        self.today = datetime.now()
        
        self.partition_base = self.today - relativedelta(days=self.lag) 
        self.partitions = []

    def get_execution_partitions(self):
        if self.cfg_backfill.get('enabled'):
            return self.back_fill()
        if self.cfg_reprocess.get('enabled'):
            return self.partition_reprocess()
            
        self.partitions = [self._format_partition(self.partition_base)]
        return self.partitions

    def back_fill(self):
        partitions = []
        if self.cfg_backfill.get('enabled'):
            start_date_str = self.cfg_backfill.get('start_date')
            end_date_str = self.cfg_backfill.get('end_date')
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError(f"Erro no YAML! As datas de backfill são inválidas: {e}")
                
            current_date = start_date
            while current_date <= end_date:
                partitions.append(self._format_partition(current_date))
                current_date += relativedelta(days=1)
        
        # Garante valores únicos e ordenados cronologicamente
        self.partitions = sorted(list(set(partitions)))
        return self.partitions

    def partition_reprocess(self):
        partitions = []
        if self.cfg_reprocess.get('enabled'):
            end_date = self.partition_base
            range_value = int(self.cfg_reprocess.get('range_value', 1))
            range_unit = self.cfg_reprocess.get('range_unit', 'day').lower()
            
            if range_unit == 'day':
                start_date = end_date - relativedelta(days=range_value)
            elif range_unit == 'month':
                start_date = end_date - relativedelta(months=range_value)
            elif range_unit == 'year':
                start_date = end_date - relativedelta(years=range_value)
            elif range_unit == 'hour':
                start_date = end_date - relativedelta(hours=range_value)
            else:
                start_date = end_date

            current_date = start_date
            while current_date <= end_date:
                partitions.append(self._format_partition(current_date))
                current_date += relativedelta(days=1) # Iteração contínua sendo diária ou horária
        
        # Garante valores únicos e ordenados cronologicamente
        self.partitions = sorted(list(set(partitions)))
        return self.partitions

    def _format_partition(self, date_obj):
        fmt_string = self.cfg_partition.get('format', 'YYYY-MM-DD')
        fmt_string = fmt_string.replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d')
        formatted_date = date_obj.strftime(fmt_string)
        
        if self.cfg_partition.get('type') == 'int':
            clean_date = formatted_date.replace('-', '').replace('/', '')
            return int(clean_date)
            
        return formatted_date