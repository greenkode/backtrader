import argparse
from datetime import datetime

import backtrader as bt

from domain.analysis import AlphalensAnalyzer, QuantStatsAnalyzer
from domain.commission import CryptoSpotCommissionInfo
from domain.data import load_data_into_cerebro
from exports.exports import save_for_alphalens, save_for_pyfolio, export_quantstats
from strategy.MinuteMomentumStrategy import MinuteMomentumStrategy
from strategy.RebalancingStrategy import RebalancingStrategy


def run(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro()

    load_data_into_cerebro(cerebro, period='1m', start=datetime(2018, 1, 1), end=datetime(2020, 12, 31),
                           filter_list=['ETHUSDT'])

    # add strategy
    # cerebro.addstrategy(RebalancingStrategy, **eval('dict(' + args.strat + ')'))
    cerebro.addstrategy(MinuteMomentumStrategy)

    # set the cash
    cerebro.broker.setcash(args.cash)
    if args.fractional:
        cerebro.broker.addcommissioninfo(CryptoSpotCommissionInfo())

    # cerebro.addanalyzer(QuantStatsAnalyzer, _name="quantstats")
    # cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    # cerebro.addanalyzer(AlphalensAnalyzer, _name="alphalens")

    results = cerebro.run()  # execute it all

    # save_for_alphalens(results[0])
    # save_for_pyfolio(results[0])
    # export_quantstats(results[0])

    # Basic performance evaluation ... final value ... minus starting cash
    pnl = cerebro.broker.get_value() - args.cash
    print('Profit ... or Loss: {:.2f}'.format(pnl))

    if args.plot:  # Plot if requested to
        cerebro.plot(**eval('dict(' + args.plot + ')'))


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Rebalancing with the Conservative Formula',
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

    parser.add_argument('--cash', default=10.0, type=float,
                        metavar='kwargs', help='kwargs in k1=v1,k2=v2 format')

    parser.add_argument('--strat', required=False, default='',
                        metavar='kwargs', help='kwargs in k1=v1,k2=v2 format')

    parser.add_argument('--noprint', action='store_true', default=False,
                        help='Print the dataframe')

    parser.add_argument('--fractional', action='store_true', default=True,
                        help='Use fractional commission info')

    parser.add_argument('--plot', action='store_true', default=False,
                        help='Plot chart at the end')

    return parser.parse_args(pargs)


if __name__ == '__main__':
    run()
