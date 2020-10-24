from backtrader import bt
import math


class InverseVolatility(bt.Indicator):
    lines = ('volatilities',)
    params = (('period', 10),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        datasum = math.fsum(self.data.get(size=self.p.period))
        self.lines.volatilities[0] = datasum / self.p.period
