import backtrader as bt


class CryptoSpotCommissionInfo(bt.CommissionInfo):
    params = (
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_PERC),  # apply % commission
    )

    def __init__(self):
        assert abs(self.p.commission) < 1.0  # commission is a percentage
        assert self.p.mult == 1.0
        assert self.p.margin is None
        assert self.p.commtype == bt.CommInfoBase.COMM_PERC
        assert self.p.stocklike
        assert self.p.percabs
        assert self.p.leverage == 1.0
        assert not self.p.automargin

        super().__init__()

    def getsize(self, price, cash):
        return self.p.leverage * (cash / price)

    def getcommission(self, size, price):
        return abs(size) * price * 0.001


class CryptoContractCommissionInfo(bt.CommissionInfo):
    params = (
        ('stocklike', False),
        ('commtype', bt.CommInfoBase.COMM_PERC),  # apply % commission
    )

    def __init__(self):
        assert abs(self.p.commission) < 1.0  # commission is a percentage
        assert self.p.mult > 1.0
        assert self.p.margin is None
        assert self.p.commtype == bt.CommInfoBase.COMM_PERC
        assert not self.p.stocklike
        assert self.p.percabs
        assert self.p.leverage == 1.0
        self.p.automargin = 1 / self.p.mult

        super().__init__()

    def getsize(self, price, cash):
        return self.p.leverage * (cash / price)

    def _getcommission(self, size, price, pseudoexec):
        return abs(size) * self.p.commission * price * self.p.mult
