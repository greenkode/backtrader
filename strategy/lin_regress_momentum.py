import sys
from datetime import datetime
from os import listdir
from os.path import isfile, join, dirname, basename

import backtrader as bt
import numpy as np
import pandas as pd
from scipy import stats

from api.coinmarketcap import get_top_cryptos_by_market_volume
from domain.analysis import QuantStatsAnalyzer, AlphalensAnalyzer
from domain.commission import CryptoSpotCommissionInfo
from domain.data import BinanceCsvDataFeed
from domain.sizer import BinanceSizer
from exports.exports import save_for_alphalens, save_for_pyfolio, export_quantstats


class BinanceStrategy(bt.Strategy):
    params = dict(stop_loss=0.02,
                  maximum_stake=0.2,
                  trail=False,
                  volatility_window=20,
                  minimum_momentum=40,
                  portfolio_size=10,
                  reserve= 0.05)

    def __init__(self):
        self.dataclose = self.datas[0].close

        self.order = None
        self.buyprice = None
        self.buycomm = None

        self.open_orders = {}
        self.window = 0
        self.started = False

        self.perctarget = (1.0 - self.p.reserve) % self.p.portfolio_size


    def next(self):

        self.started = True

        self.window = self.window + 1

        if self.window <= self.p.volatility_window:
            return

        hist, ranking_table = self.calculate_ranking_table()

        kept_positions = self.alter_kept_positions(ranking_table)

        replacement_stocks = self.p.portfolio_size - len(kept_positions)

        buy_list = ranking_table.loc[~ranking_table.index.isin(kept_positions)][:replacement_stocks]

        new_portfolio = self.get_new_portfolio(buy_list, ranking_table, kept_positions)

        if len(kept_positions) > 0 and not self.is_trading_day():
            new_portfolio = new_portfolio.iloc[0:0]

        for symbol in kept_positions:
            new_portfolio = new_portfolio.append({'symbol': symbol, 'ranking': ranking_table.loc[symbol]},
                                                 ignore_index=True)
        new_portfolio.drop_duplicates(subset='symbol', keep='first')

        vola_target_weights = self.calculate_target_weights(hist, new_portfolio)

        self.buy_logic(kept_positions, new_portfolio, ranking_table, vola_target_weights)

    def is_trading_day(self):
        return self.datas[0].datetime.date(0).weekday() == 6

    def volatility(self, data):
        return data.pct_change().rolling(self.p.volatility_window).std().iloc[-1]

    def calculate_ranking_table(self):
        df = pd.DataFrame()
        for datum in self.datas:
            hist = datum.close.lines[0].get(size=self.p.volatility_window + 1)
            df[datum._name] = hist
        ranking_table = rebalance(self, df)
        return df, ranking_table

    def calculate_target_weights(self, df, new_portfolio):
        vola_table = df[new_portfolio['symbol']].apply(self.volatility)
        inv_vola_table = 1 / vola_table
        sum_inv_vola = np.sum(inv_vola_table)
        vola_target_weights = inv_vola_table / sum_inv_vola
        return vola_target_weights.apply(lambda x: min(x, self.p.maximum_stake))

    def buy_logic(self, kept_positions, new_portfolio, ranking_table, vola_target_weights):
        for i, rank in new_portfolio.iterrows():
            symbol = rank['symbol']
            weight = vola_target_weights[symbol]
            if symbol in kept_positions or ranking_table[symbol] > self.p.minimum_momentum:
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
            if symbol not in ranking_table or ranking_table[symbol] < self.p.minimum_momentum:
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
                # self.set_stop_loss(order)

            else:  # Sell
                self.log('SELL EXECUTED, Symbol: %s, Price: %.5f, Cost: %.5f, Comm %.5f' %
                         (order.info['symbol'], order.executed.price,
                          order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order %s' % order.Status[order.status])
        pass

    def set_stop_loss(self, order):
        if not self.p.trail:
            stop_price = order.executed.price * (1.0 - self.p.stop_loss)
            self.sell(exectype=bt.Order.Stop, price=stop_price)
        else:
            self.sell(exectype=bt.Order.StopTrail, trailamount=self.p.trail)

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        if trade.pnl < 0:
            self.log('%s, OPERATION PROFIT, GROSS %.2f, NET %.2f' % (
                trade.data._name, trade.pnl, trade.pnlcomm))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))


def rebalance(context, hist):
    # output_progress(context)
    return hist.apply(momentum_score).sort_values(ascending=False)


def momentum_score(data):
    x = np.arange(len(data))
    log_ts = np.log(data)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_ts)
    annualized_slope = (np.power(np.exp(slope), 365) - 1) * 100
    return annualized_slope * (r_value ** 2)


def output_progress(context):
    perf_pct = (context.portfolio.portfolio_value / context.last_month) - 1
    print("{} - Last Month Result: {:.2%}".format(context.todays_date, perf_pct))
    context.last_month = context.portfolio.portfolio_value


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BinanceStrategy)

    data_path = dirname(join(sys.argv[1], sys.argv[2]))

    files = [f for f in listdir(data_path) if isfile(join(data_path, f))]

    top_cryptos = get_top_cryptos_by_market_volume(20)
    # exclusion = ['XMRUSDT', 'XTZUSDT', 'EOSUSDT', 'LINKUSDT', 'TRXUSDT', 'BCHUSDT', 'ATOMUSDT']
    # top_cryptos = [e for e in top_cryptos if e not in exclusion]
    for i, file in enumerate(files):
        if file.split('_')[1] in top_cryptos:
            data = bt.feeds.GenericCSVData(
                dataname=join(data_path, file),
                fromdate=datetime(2017, 10, 1),
                todate=datetime(2020, 12, 31),
                nullvalue=0.0,
                dtformat='%Y-%m-%d %H:%M:%S',
                datetime=0,
                high=1,
                low=2,
                open=3,
                close=4,
                volume=5,
                openinterest=-1,
                name=file.split('_')[1]
            )
            cerebro.adddata(data)

    cerebro.broker.setcash(10000.0)
    cerebro.broker.addcommissioninfo(CryptoSpotCommissionInfo())

    cerebro.addanalyzer(QuantStatsAnalyzer, _name="quantstats")
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(AlphalensAnalyzer, _name="alphalens")

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    save_for_alphalens(results[0])
    save_for_pyfolio(results[0])
    export_quantstats(results[0])
