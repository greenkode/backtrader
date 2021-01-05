import pandas as pd
import quantstats as qs
import os


def save_for_pyfolio(strat):
    pyfolio = strat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfolio.get_pf_items()

    benchmark = pd.read_csv('/Users/umoh/Data/Binance/1d/Binance_BTCUSDT_1d.csv', parse_dates=True, index_col=0)
    benchmark = benchmark.tz_localize(tz='utc')

    export_directory = "/Users/umoh/Data/pyfolio/"
    if not os.path.isdir(export_directory):
        os.mkdir(export_directory)

    pd.to_pickle(returns, os.path.join(export_directory, "returns.pkl"))
    pd.to_pickle(positions, os.path.join(export_directory, "positions.pkl"))
    pd.to_pickle(transactions, os.path.join(export_directory, "transactions.pkl"))
    pd.to_pickle(gross_lev, os.path.join(export_directory, "gross_lev.pkl"))
    pd.to_pickle(benchmark, os.path.join(export_directory, "benchmark.pkl"))


def export_quantstats(strat):
    qs.extend_pandas()

    # ---- Format the values from results ----
    df_values = pd.DataFrame(strat.analyzers.getbyname("cash_market").get_analysis()).T
    df_values = df_values.iloc[:, 1]
    returns = qs.utils.to_returns(df_values)
    returns.index = pd.to_datetime(returns.index)
    # ----------------------------------------

    # ---- Format the benchmark ----
    benchmark = pd.read_csv('/Users/umoh/Data/Binance/1d/Binance_BTCUSDT_1d.csv',
                            parse_dates=True, index_col=0)['close']
    benchmark.index = pd.to_datetime(benchmark.index) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=11)
    benchmark = qs.utils.to_returns(benchmark)

    qs.reports.html(returns, benchmark=benchmark, output="qs.html")
