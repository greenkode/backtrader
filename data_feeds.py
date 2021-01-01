import datetime
import backtrader as bt

import backtrader.feeds as btfeed


class BinanceCsvDataFeed(btfeed.GenericCSVData):
    params = (
        ('fromdate', datetime.datetime(2017, 7, 1)),
        ('todate', datetime.datetime.now()),
        ('nullvalue', float('NaN')),
        ('dtformat', '%Y-%m-%d'),
        ('tmformat', '%H:%M:%S'),
        ('timestamp', 0),
        ('high', 1),
        ('low', 2),
        ('open', 3),
        ('close', 4),
        ('volume', 5),
        ('close_time', 6),
        ('quote_av', 7),
        ('trades', 8),
        ('tb_base_av', 9),
        ('tb_quote_av', 10),
        ('ignore', 11)
    )


class BinancePandasDataFeed(btfeed.DataBase):
    params = (
        ('timestamp', -1),
        ('high', -1),
        ('low', -1),
        ('open', -1),
        ('close', -1),
        ('volume', -1),
        ('npy', -1),
        ('close_time', -1),
        ('quote_av', -1),
        ('trades', -1),
        ('tb_base_av', -1),
        ('tb_quote_av', -1),
        ('ignore', -1)
    )


class PandasData(bt.feeds.PandasData):
    lines = ('npy',)
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('npy', 'npy'),
    )
