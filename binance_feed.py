# IMPORTS

import math
import os.path
from datetime import datetime

import pandas as pd
from binance.client import Client
from dateutil import parser
from api import coinmarketcap


binsizes = {"1m": 1, "5m": 5, "1h": 60, "1d": 1440}
batch_size = 1000
binance_client = Client(api_key='', api_secret='')

start = '1 Sep 2017'


def minutes_of_new_data(symbol, kline_size, data, source):
    if len(data) > 0:
        old = parser.parse(data["timestamp"].iloc[-1])
    else:
        old = datetime.strptime(start, '%d %b %Y')
    new = pd.to_datetime(binance_client.get_klines(symbol=symbol, interval=kline_size)[-1][0], unit='ms')
    return old, new


def get_all_binance(symbol, kline_size, save=False):
    filename = '/Volumes/Seagate Expansion Drive/binance/data/%s/%s-%s-data.csv' % (kline_size, symbol, kline_size)
    if os.path.isfile(filename):
        data_df = pd.read_csv(filename)
    else:
        data_df = pd.DataFrame()
    oldest_point, newest_point = minutes_of_new_data(symbol, kline_size, data_df, source="binance")
    delta_min = (newest_point - oldest_point).total_seconds() / 60
    available_data = math.ceil(delta_min / binsizes[kline_size])
    if oldest_point == datetime.strptime(start, '%d %b %Y'):
        print('Downloading all available %s data for %s. Be patient..!' % (kline_size, symbol))
    else:
        print('Downloading %d minutes of new data available for %s, i.e. %d instances of %s data.' % (
            delta_min, symbol, available_data, kline_size))
    klines = binance_client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"),
                                                  newest_point.strftime("%d %b %Y %H:%M:%S"))
    data = pd.DataFrame(klines,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av',
                                 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])

    data['timestamp'] = pd.to_datetime(data['timestamp'], format='%Y-%m-%d %H:%M:%S')
    # data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    if len(data_df) > 0:
        temp_df = pd.DataFrame(data)
        data_df = data_df.append(temp_df)
    else:
        data_df = data
    data_df.set_index('timestamp', inplace=True)
    if save:
        data_df.to_csv(filename)
    print('All caught up..!')
    return data_df


def get_top(number):
    results = []
    for result in coinmarketcap.get_top_cryptos_by_market_volume(number):
        results.append(result['symbol'])
    return results


def get_symbols():
    info = binance_client.get_exchange_info()
    # top = get_top(20)

    filtered_symbols = []
    for symbol in info['symbols']:
        if symbol['quoteAsset'] == 'USDT':
            filtered_symbols.append(symbol['symbol'])
    return filtered_symbols


for symbol in get_symbols():
    get_all_binance(symbol, '1h', save=True)
