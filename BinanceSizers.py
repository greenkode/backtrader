import backtrader as bt


class CommInfoFractional(bt.CommInfoBase):
    params = (
        ('stocklike', True),
        ('commission', 0.001),
        ('commtype', bt.CommInfoBase.COMM_PERC),
    )

    def _getcommission(self, size, price, pseudoexec):
        return abs(size * price * self.p.commission)


class BinanceSizer(bt.Sizer):
    params = (('prop', 0.2),)

    def _getsizing(self, comminfo, cash, data, isbuy):

        if isbuy:
            if 'BTCUSDT' in data._dataname:
                print('in bitcoin')

            target = self.broker.getvalue() * self.p.prop  # Ideal total value of the position
            price = data.close[0]
            size_net = target / price  # How many shares are needed to get target
            size = size_net * 0.99

            if size * price > cash:
                return 0  # Not enough money for this trade
            else:
                return size
        else:
            return self.broker.getposition(data).size
