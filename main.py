from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pandas as pd
from os import listdir
from os.path import isfile, join, dirname, basename
import sys

import backtrader as bt
from datetime import datetime

from BinanceDataFeed import BinanceCsvDataFeed
from BinanceSizers import BinanceSizer, CommInfoFractional

from Portfolio import rebalance
import numpy as np

from api.coinmarketcap import get_top_cryptos_by_market_volume


class BinanceStrategy(bt.Strategy):
    params = (('volatility_period', 20),)

    def __init__(self):
        self.dataclose = self.datas[0].close

        self.order = None
        self.buyprice = None
        self.buycomm = None

        self.window = 0
        self.minimum_momentum = 40  # 40

        self.momentum_window = 125
        self.portfolio_size = 10
        self.vola_window = 20  # 20
        self.kline = sys.argv[2]

        self.open_orders = {}

    def next(self):

        self.window = self.window + 1

        if self.window <= self.vola_window or self.is_execution_time() or len(
                self.open_orders) > self.portfolio_size:
            return

        hist, ranking_table = self.calculate_ranking_table()

        kept_positions = self.alter_kept_positions(ranking_table)

        replacement_stocks = self.portfolio_size - len(kept_positions)

        buy_list = ranking_table.loc[~ranking_table.index.isin(kept_positions)][:replacement_stocks]

        new_portfolio = self.get_new_portfolio(buy_list, ranking_table, kept_positions)
        for symbol in kept_positions:
            new_portfolio = new_portfolio.append({'symbol': symbol, 'ranking': ranking_table.loc[symbol]},
                                                 ignore_index=True)
        new_portfolio.drop_duplicates(subset='symbol', keep='first')

        vola_target_weights = self.calculate_target_weights(hist, new_portfolio)

        self.buy_logic(kept_positions, new_portfolio, ranking_table, vola_target_weights)

    def is_execution_time(self):
        return self.kline == '1d' and self.datas[0].datetime.date(0).weekday() != 6 or self.kline == '1h' and \
               self.datas[0].datetime.time(0).hour % 6 == 0

    def volatility(self, data):
        return data.pct_change().rolling(self.vola_window).std().iloc[-1]

    def calculate_ranking_table(self):
        df = pd.DataFrame()
        for datum in self.datas:
            hist = datum.close.lines[0].get(size=self.vola_window + 1)
            df[basename(datum._dataname).split('-')[1]] = hist
        ranking_table = rebalance(self, df)
        return df, ranking_table

    def calculate_target_weights(self, df, new_portfolio):
        vola_table = df[new_portfolio['symbol']].apply(self.volatility)
        inv_vola_table = 1 / vola_table
        sum_inv_vola = np.sum(inv_vola_table)
        vola_target_weights = inv_vola_table / sum_inv_vola
        return vola_target_weights

    def buy_logic(self, kept_positions, new_portfolio, ranking_table, vola_target_weights):
        for i, rank in new_portfolio.iterrows():
            symbol = rank['symbol']
            weight = vola_target_weights[symbol]
            if symbol in kept_positions or ranking_table[symbol] > self.minimum_momentum:
                self.open_orders[symbol] = self.order_target_percent(
                    data=[x for x in self.datas if symbol.split('-')[0] in x._dataname][0],
                    target=weight, symbol=symbol)

    def get_new_portfolio(self, buy_list, ranking_table, kept_positions):
        new_portfolio = pd.DataFrame(columns=["symbol", "ranking"])
        for i in range(len(buy_list)):
            if ranking_table.iloc[i] and ranking_table.index[i] not in kept_positions:
                new_portfolio.loc[i] = [ranking_table.index[i], ranking_table.iloc[i]]
        if len(new_portfolio) > 10:
            print(new_portfolio)
        return new_portfolio

    def alter_kept_positions(self, ranking_table):
        kept_positions = list(self.open_orders.keys())
        for symbol, security in self.open_orders.items():
            if symbol not in ranking_table or ranking_table[symbol] < self.minimum_momentum:
                self.open_orders[symbol] = self.sell(
                    data=[x for x in self.datas if symbol.split('-')[0] in x._dataname][0],
                    symbol=symbol)
                kept_positions.remove(symbol)
        return kept_positions

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Symbol: %s, Price: %.5f, Cost: %.5f, Comm %.5f' %
                         (order.info['symbol'], order.executed.price,
                          order.executed.value,
                          order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Symbol: %s, Price: %.5f, Cost: %.5f, Comm %.5f' %
                         (order.info['symbol'], order.executed.price,
                          order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BinanceStrategy)

    data_path = dirname(join(sys.argv[1], sys.argv[2]))

    files = [f for f in listdir(data_path) if isfile(join(data_path, f))]

    top_cryptos = get_top_cryptos_by_market_volume(15)
    for i, file in enumerate(files):
        if file.split('-')[1] in top_cryptos:
            data = BinanceCsvDataFeed(dataname=join(data_path, file),
                                      fromdate=datetime(2020, 1, 1),
                                      todate=datetime(2020, 10, 6))
            cerebro.adddata(data)

    cerebro.broker.setcash(1000.0)
    cerebro.addsizer(BinanceSizer)
    cerebro.broker.addcommissioninfo(CommInfoFractional())
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.plot(volume=False)
