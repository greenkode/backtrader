import argparse
import logging
import sys
from datetime import datetime

import backtrader as bt

from analyzers import CashMarket
from commissions import CryptoSpotCommissionInfo
from strategy_analysis import save_for_pyfolio, export_quantstats


class St(bt.Strategy):
    params = dict(
        p1=10, p2=30,  # periods for crossover
        ma=bt.ind.SMA,  # moving average to use
        target=0.5,  # percentage of value to use
    )

    def __init__(self):
        ma1, ma2 = [self.p.ma(period=p) for p in (self.p.p1, self.p.p2)]
        self.cross = bt.ind.CrossOver(ma1, ma2)

    def next(self):
        # self.logdata()
        if self.cross > 0:
            self.loginfo('Enter Long')
            self.order_target_percent(target=self.p.target)
        elif self.cross < 0:
            self.loginfo('Enter Short')
            self.order_target_percent(target=-self.p.target)
        print(f"Strategy - {self.data.datetime.date()}")

    def notify_trade(self, trade):
        if trade.justopened:
            self.loginfo('Trade Opened  - Size {} @Price {}',
                         trade.size, trade.price)
        elif trade.isclosed:
            self.loginfo('Trade Closed  - Profit {}', trade.pnlcomm)

        else:  # trade updated
            self.loginfo('Trade Updated - Size {} @Price {}',
                         trade.size, trade.price)

    def notify_order(self, order):
        if order.alive():
            return

        otypetxt = 'Buy ' if order.isbuy() else 'Sell'
        if order.status == order.Completed:
            self.loginfo(
                ('{} Order Completed - '
                 'Size: {} @Price: {} '
                 'Value: {:.2f} Comm: {:.2f}'),
                otypetxt, order.executed.size, order.executed.price,
                order.executed.value, order.executed.comm
            )
        else:
            self.loginfo('{} Order rejected', otypetxt)

    def loginfo(self, txt, *args):
        out = [self.datetime.date().isoformat(), txt.format(*args)]
        logging.info(','.join(out))

    def logerror(self, txt, *args):
        out = [self.datetime.date().isoformat(), txt.format(*args)]
        logging.error(','.join(out))

    def logdebug(self, txt, *args):
        out = [self.datetime.date().isoformat(), txt.format(*args)]
        logging.debug(','.join(out))

    def logdata(self):
        txt = []
        txt += ['{:.2f}'.format(self.data.open[0])]
        txt += ['{:.2f}'.format(self.data.high[0])]
        txt += ['{:.2f}'.format(self.data.low[0])]
        txt += ['{:.2f}'.format(self.data.close[0])]
        txt += ['{:.2f}'.format(self.data.volume[0])]
        self.loginfo(','.join(txt))


def run(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro()

    data = bt.feeds.GenericCSVData(
        dataname=args.data,
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
        openinterest=-1
    )
    cerebro.adddata(data)  # create and add data feed

    cerebro.addstrategy(St)  # add the strategy

    cerebro.broker.set_cash(args.cash)  # set broker cash

    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(CashMarket, _name="cash_market")

    if args.fractional:  # use the fractional scheme if requested
        cerebro.broker.addcommissioninfo(CryptoSpotCommissionInfo())

    results = cerebro.run()  # execute
    save_for_pyfolio(results[0])
    export_quantstats(results[0])

    if args.plot:  # Plot if requested to
        cerebro.plot(**eval('dict(' + args.plot + ')'))


def logconfig(pargs):
    if pargs.quiet:
        verbose_level = logging.ERROR
    else:
        verbose_level = logging.INFO - pargs.verbose * 10  # -> DEBUG

    logger = logging.getLogger()
    for h in logger.handlers:  # Remove all loggers from root
        logger.removeHandler(h)

    stream = sys.stdout if not pargs.stderr else sys.stderr  # choose stream

    logging.basicConfig(
        stream=stream,
        format="%(message)s",  # format="%(levelname)s: %(message)s",
        level=verbose_level,
    )


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Fractional Sizes with CommInfo',
    )

    pgroup = parser.add_argument_group('Data Options')
    parser.add_argument('--data', default='/Users/umoh/Data/Binance/1d/Binance_BTCUSDT_1d.csv',
                        help='Data to read in')

    pgroup = parser.add_argument_group(title='Broker Arguments')
    pgroup.add_argument('--cash', default=1000.0, type=float,
                        help='Starting cash to use')

    pgroup.add_argument('--fractional', action='store_true', default=True,
                        help='Use fractional commission info')

    pgroup = parser.add_argument_group(title='Plotting Arguments')
    pgroup.add_argument('--plot', default='', nargs='?', const='{}',
                        metavar='kwargs', help='kwargs: "k1=v1,k2=v2,..."')

    pgroup = parser.add_argument_group('Verbosity Options')
    pgroup.add_argument('--stderr', action='store_true',
                        help='Log to stderr, else to stdout')
    pgroup = pgroup.add_mutually_exclusive_group()
    pgroup.add_argument('--quiet', '-q', action='store_true',
                        help='Silent (errors will be reported)')
    pgroup.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity level')

    # Parse and process some args
    pargs = parser.parse_args(pargs)
    logconfig(pargs)  # config logging
    return pargs


if __name__ == '__main__':
    run()
