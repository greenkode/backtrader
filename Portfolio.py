import numpy as np
from scipy import stats


def rebalance(context, hist):
    # output_progress(context)
    return hist.apply(momentum_score).sort_values(ascending=False)


def momentum_score(data):
    x = np.arange(len(data))
    log_ts = np.log(data)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_ts)
    annualized_slope = (np.power(np.exp(slope), 365) - 1) * 100
    return annualized_slope * (r_value ** 2)


def output_progress(context):
    perf_pct = (context.portfolio.portfolio_value / context.last_month) - 1
    print("{} - Last Month Result: {:.2%}".format(context.todays_date, perf_pct))
    context.last_month = context.portfolio.portfolio_value


def sell_logic():
    pass


def buy_logic():
    pass


def volatilities():
    pass
