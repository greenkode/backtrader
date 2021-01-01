import backtrader as bt


class CommInfoFractional(bt.CommissionInfo):
    def getsize(self, price, cash):
        """Returns fractional size for cash operation @price"""
        return self.p.leverage * (cash / price)


class BinanceSizer(bt.Sizer):
    params = (('maximum_stake', 0.2),)

    def _getsizing(self, comminfo, cash, data, isbuy):

        if isbuy:
            target = self.broker.getvalue() * self.p.maximum_stake  # Ideal total value of the position
            price = data.close[0]
            size_net = target / price  # How many shares are needed to get target
            size = size_net * 0.99

            if size * price > cash:
                return 0  # Not enough money for this trade
            else:
                return size
        else:
            return self.broker.getposition(data).size
