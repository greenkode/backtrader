import collections

import backtrader as bt
from backtrader.indicators import MovingAverageSimple

from domain.indicator import Momentum


class MinuteMomentumStrategy(bt.Strategy):
    params = dict(
        momentum=Momentum,
        momentum_period=10,
        vol_period=20,
        minimum_momentum=40,
        reserve=0.05,
        maximum_stake=0.2,
        trail=False,
        stop_loss=0.02
    )

    def __init__(self):
        self.sma = bt.ind.SMA(self.data, period=self.p.vol_period)
        self.momentum = self.p.momentum(self.sma, period=self.p.momentum_period)
        pct_change = bt.ind.PctChange(self.sma, period=self.p.vol_period)
        self.volatility = bt.ind.StdDev(pct_change, period=self.p.vol_period)

    def next(self):
        cash = self.broker.get_cash()

        if cash <= 0:
            return

        if self.momentum > 40:
            self.order_target_percent(self.data, target=self.calculate_target_weight(), symbol=self.data._name)

    def calculate_target_weight(self):
        weight = 1 / (self.momentum * self.volatility)
        return weight / (weight + self.p.reserve)

    def notify_order(self, order):
        if order.alive():
            return

        otypetxt = 'Buy' if order.isbuy() else 'Sell'
        if order.status == order.Completed:
            self.log(
                '{} Order Completed - Symbol: {} Size: {} @Price: {} Value: {:.2f} Comm: {:.2f}'.format(
                    otypetxt, order.info['symbol'], order.executed.size, order.executed.price,
                    order.executed.value, order.executed.comm
                ))
        else:
            self.log('{} Order rejected'.format(otypetxt))

    def log(self, arg):
        print(f'{self.datetime.date(), arg}')
