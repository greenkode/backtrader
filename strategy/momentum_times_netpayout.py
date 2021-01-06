import argparse
import os

import backtrader as bt
from datetime import datetime
import glob
import pandas as pd

from domain.analysis import AlphalensAnalyzer, QuantStatsAnalyzer
from domain.commission import CryptoSpotCommissionInfo
from exports.exports import save_for_alphalens, save_for_pyfolio, export_quantstats


class RebalancingStrategy(bt.Strategy):
    params = dict(
        selcperc=0.10,  # percentage of stocks to select from the universe
        rperiod=1,  # period for the returns calculation, default 1 period
        vperiod=36,  # lookback period for volatility - default 36 periods
        mperiod=12,  # lookback period for momentum - default 12 periods
        reserve=0.05  # 5% reserve capital
    )

    def __init__(self):
        # calculate 1st the amount of stocks that will be selected
        self.selnum = int(len(self.datas) * self.p.selcperc)

        # allocation per stock
        # reserve kept to make sure orders are not rejected due to
        # margin. Prices are calculated when known (close), but orders can only
        # be executed next day (opening price). Price can gap upwards
        self.perctarget = (1.0 - self.p.reserve) % self.selnum

        # returns, volatilities and momentum
        rs = [bt.ind.PctChange(d, period=self.p.rperiod) for d in self.datas]
        vs = [bt.ind.StdDev(ret, period=self.p.vperiod) for ret in rs]
        ms = [bt.ind.ROC(d, period=self.p.mperiod) for d in self.datas]

        # simple rank formula: (momentum * net payout) / volatility
        # the highest ranked: low vol, large momentum, large payout
        self.ranks = {d: 5 * m / v for d, v, m in zip(self.datas, vs, ms)}

        self.started = False

    def next(self):

        self.started = True
        # sort data and current rank
        ranks = sorted(
            self.ranks.items(),  # get the (d, rank), pair
            key=lambda x: x[1][0],  # use rank (elem 1) and current time "0"
            reverse=True  # highest ranked 1st ... please
        )

        # put top ranked in dict with data as key to test for presence
        rtop = dict(ranks[:self.selnum])

        # For logging purposes of stocks leaving the portfolio
        rbot = dict(ranks[self.selnum:])

        # prepare quick lookup list of stocks currently holding a position
        posdata = [d for d, pos in self.getpositions().items() if pos]

        # remove those no longer top ranked
        # do this first to issue sell orders and free cash
        for d in (d for d in posdata if d not in rtop):
            # self.log('Exit {} - Rank {:.2f}'.format(d._name, rbot[d][0]))
            self.order_target_percent(d, target=0.0)

        # rebalance those already top ranked and still there
        for d in (d for d in posdata if d in rtop):
            # self.log('Rebal {} - Rank {:.2f}'.format(d._name, rtop[d][0]))
            self.order_target_percent(d, target=self.perctarget)
            del rtop[d]  # remove it, to simplify next iteration

        # issue a target order for the newly top ranked stocks
        # do this last, as this will generate buy orders consuming cash
        for d in rtop:
            # self.log('Enter {} - Rank {:.2f}'.format(d._name, rtop[d][0]))
            self.order_target_percent(d, target=self.perctarget)

    def notify_order(self, order):
        if order.alive():
            return

        otypetxt = 'Buy ' if order.isbuy() else 'Sell'
        if order.status == order.Completed:
            self.log(
                '{} Order Completed - Size: {} @Price: {} Value: {:.2f} Comm: {:.2f}'.format(
                    otypetxt, order.executed.size, order.executed.price,
                    order.executed.value, order.executed.comm
                ))
        # else:
        #     self.log('{} Order rejected'.format(otypetxt))

    def log(self, arg):
        print(f'{self.datetime.date(), arg}')


def run(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro()

    # Data feed kwargs
    dkwargs = dict(**eval('dict(' + args.dargs + ')'))

    # Parse from/to-date
    dtfmt, tmfmt = '%Y-%m-%d', 'T%H:%M:%S'
    if args.fromdate:
        fmt = dtfmt + tmfmt * ('T' in args.fromdate)
        dkwargs['fromdate'] = datetime.datetime.strptime(args.fromdate, fmt)

    # Simulate the header row isn't there if noheaders requested
    skiprows = 1 if args.noheaders else 0
    header = None if args.noheaders else 0

    if args.todate:
        fmt = dtfmt + tmfmt * ('T' in args.todate)
        dkwargs['todate'] = datetime.datetime.strptime(args.todate, fmt)

    # add all the data files available in the directory datadir
    for fname in glob.glob(os.path.join(args.datadir, '*')):

        dataframe = pd.read_csv(fname, skiprows=skiprows,
                                header=header,
                                parse_dates=True,
                                index_col=0)

        if len(dataframe) > 1000:
            data = bt.feeds.GenericCSVData(
                dataname=fname,
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
                name=fname.split('_')[1]
            )

            if not args.noprint:
                print('--------------------------------------------------')
                print(dataframe)
                print('--------------------------------------------------')

            cerebro.adddata(data)

    # add strategy
    cerebro.addstrategy(RebalancingStrategy, **eval('dict(' + args.strat + ')'))

    # set the cash
    cerebro.broker.setcash(args.cash)
    if args.fractional:
        cerebro.broker.addcommissioninfo(CryptoSpotCommissionInfo())

    cerebro.addanalyzer(QuantStatsAnalyzer, _name="quantstats")
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(AlphalensAnalyzer, _name="alphalens")

    results = cerebro.run()  # execute it all

    save_for_alphalens(results[0])
    save_for_pyfolio(results[0])
    export_quantstats(results[0])

    # Basic performance evaluation ... final value ... minus starting cash
    pnl = cerebro.broker.get_value() - args.cash
    print('Profit ... or Loss: {:.2f}'.format(pnl))

    if args.plot:  # Plot if requested to
        cerebro.plot(**eval('dict(' + args.plot + ')'))


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('Rebalancing with the Conservative Formula'),
    )

    parser.add_argument('--datadir', required=True,
                        help='Directory with data files')

    parser.add_argument('--dargs', default='',
                        metavar='kwargs', help='kwargs in k1=v1,k2=v2 format')

    # Defaults for dates
    parser.add_argument('--fromdate', required=False, default='',
                        help='Date[time] in YYYY-MM-DD[THH:MM:SS] format')

    parser.add_argument('--todate', required=False, default='',
                        help='Date[time] in YYYY-MM-DD[THH:MM:SS] format')

    parser.add_argument('--cerebro', required=False, default='',
                        metavar='kwargs', help='kwargs in k1=v1,k2=v2 format')

    parser.add_argument('--cash', default=10000.0, type=float,
                        metavar='kwargs', help='kwargs in k1=v1,k2=v2 format')

    parser.add_argument('--strat', required=False, default='',
                        metavar='kwargs', help='kwargs in k1=v1,k2=v2 format')

    parser.add_argument('--noheaders', action='store_true', default=False,
                        required=False,
                        help='Do not use header rows')

    parser.add_argument('--noprint', action='store_true', default=False,
                        help='Print the dataframe')

    parser.add_argument('--fractional', action='store_true',
                        help='Use fractional commission info')

    return parser.parse_args(pargs)


if __name__ == '__main__':
    run()
