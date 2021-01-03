import backtrader as bt
import numpy as np
from scipy.stats import linregress


def momentum_func(self, the_array):
    r = np.log(the_array)
    slope, _, rvalue, _, _ = linregress(np.arange(len(r)), r)
    annualized = (1 + slope) ** 365
    return annualized * (rvalue ** 2)


class Momentum(bt.ind.PeriodN):
    lines = ('trend',)
    params = dict(period=50)
    func = momentum_func
