import os
import glob
from datetime import datetime
import backtrader as bt
import pandas as pd
import numpy as np

import pyarrow.parquet as pq

import backtrader.feeds as btfeed


class BinanceCsvDataFeed(btfeed.GenericCSVData):
    params = (
        ('fromdate', datetime(2017, 7, 1)),
        ('todate', datetime.now()),
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
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
    )


def load_data_into_cerebro(cerebro, period='1d', start=None, end=None, filter_list=[], exclusion_list=[]):
    for fname in glob.glob(os.path.join(f"/Users/umoh/Data/Binance/{period}", '*')):

        if period == '1d':
            name = os.path.basename(fname).split('_')[1]
            if name in exclusion_list:
                pass
            if len(filter_list) == 0 or name in filter_list:
                data = bt.feeds.GenericCSVData(
                    dataname=fname,
                    fromdate=start,
                    todate=end,
                    nullvalue=0.0,
                    dtformat='%Y-%m-%d %H:%M:%S',
                    datetime=0,
                    high=1,
                    low=2,
                    open=3,
                    close=4,
                    volume=5,
                    openinterest=-1,
                    name=name
                )
                cerebro.adddata(data)
        elif period == '1m':
            name = os.path.basename(fname).replace('-', '').split('.')[0]
            if name in exclusion_list:
                pass

            if len(filter_list) == 0 or name in filter_list:
                df = pq.read_table(fname).to_pandas()
                df = df.loc[pd.to_datetime(start): pd.to_datetime(end)]
                data = PandasData(dataname=df, name=name)
                cerebro.adddata(data)
