import backtrader as bt
import numpy as np
from scipy.stats import linregress


@staticmethod
def momentum_func(data):
    r = np.log(data)
    slope, _, rvalue, _, _ = linregress(np.arange(len(r)), r)
    # annualized = (1 + slope) ** 252
    annualized = (np.power(np.exp(slope), 365) - 1) * 100
    return annualized * (rvalue ** 2)


class Momentum(bt.ind.OperationN):
    lines = ('trend',)
    params = dict(period=20)
    func = momentum_func
