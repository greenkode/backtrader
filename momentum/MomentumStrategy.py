import collections
import glob
import os

import pandas as pd
import backtrader as bt

from momentum.domain import Momentum


class MomentumStrategy(bt.Strategy):
    params = dict(
        momentum=Momentum,
        momentum_period=90,

        movav=bt.ind.SMA,
        idx_period=200,
        stock_period=100,

        volatr=bt.ind.ATR,
        vol_period=20,
        rebal_weekday=5,
    )

    def __init__(self):
        self.inds = collections.defaultdict(dict)

        self.stocks = self.datas[1:]

        self.idx_mav = self.p.movav(self.data0, period=self.p.idx_period)
        for d in self.stocks:
            self.inds[d]['mom'] = self.p.momentum(d, period=self.momentum_period)
            self.inds[d]['mav'] = self.p.movav(d, period=self.p.stock_period)
            self.inds[d]['vol'] = self.p.volatr(d, period=self.p.vol_period)

        self.d_with_len = []

        self.spy_filter = self.spe < self.spy_sma200

        self.add_timer(
            when=bt.Timer.SESSION_START,
            weekdays=[self.p.rebal_weekday],
            weekcarry=True,
        )

    def prenext(self):
        self.d_with_len = [d for d in self.datas if len(d)]
        self.next()

    def next(self):
        l = len(self)
        if l % 5 == 0:
            self.rebalance_portfolio()
        if l % 10 == 0:
            self.rebalance_positions()

    def rebalance_portfolio(self):
        # only look at data that we can have indicators for
        self.rankings = list(filter(lambda d: len(d) > 100, self.stocks))
        self.rankings.sort(key=lambda d: self.inds[d]["momentum"][0])
        num_stocks = len(self.rankings)

        # sell stocks based on criteria
        for i, d in enumerate(self.rankings):
            if self.getposition(self.data).size:
                if i > num_stocks * 0.2 or d < self.inds[d]["sma100"]:
                    self.close(d)

        if self.spy < self.spy_sma200:
            return

        # buy stocks with remaining cash
        for i, d in enumerate(self.rankings[:int(num_stocks * 0.2)]):
            cash = self.broker.get_cash()
            value = self.broker.get_value()
            if cash <= 0:
                break
            if not self.getposition(self.data).size:
                size = value * 0.001 / self.inds[d]["atr20"]
                self.buy(d, size=size)

    def rebalance_positions(self):
        num_stocks = len(self.rankings)

        if self.spy < self.spy_sma200:
            return

        # rebalance all stocks
        for i, d in enumerate(self.rankings[:int(num_stocks * 0.2)]):
            cash = self.broker.get_cash()
            value = self.broker.get_value()
            if cash <= 0:
                break
            size = value * 0.001 / self.inds[d]["atr20"]
            self.order_target_size(d, size)


def run():
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.set_coc(True)

    # add all the data files available in the directory datadir
    for fname in glob.glob(os.path.join("/Volumes/Seagate Expansion Drive/binance/data/full_columns", '*')):
        df = pd.read_csv(fname, skiprows=0,
                         header=0,
                         parse_dates=True,
                         index_col=0)

        if len(df) > 100:
            cerebro.adddata(bt.feeds.PandasData(dataname=df, plot=False))

    cerebro.addobserver(bt.observers.Value)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.Returns)
    cerebro.addanalyzer(bt.analyzers.DrawDown)
    cerebro.addstrategy(MomentumStrategy)
    results = cerebro.run()

    cerebro.plot(iplot=False)[0][0]
    print(f"Sharpe: {results[0].analyzers.sharperatio.get_analysis()['sharperatio']:.3f}")
    print(f"Norm. Annual Return: {results[0].analyzers.returns.get_analysis()['rnorm100']:.2f}%")
    print(f"Max Drawdown: {results[0].analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")


if __name__ == '__main__':
    run()
