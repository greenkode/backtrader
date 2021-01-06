import backtrader as bt


class AlphalensAnalyzer(bt.analyzers.Analyzer):
    def start(self):
        super(AlphalensAnalyzer, self).start()

    def next(self):
        if self.strategy.started:
            for k, v in self.strategy.ranks.items():
                self.ranks.append({'date': self.strategy.datetime.date(),
                                   'value': v.get()[0], 'asset': k._name})
            prices = {}
            for data in self.datas:
                prices[data._name] = data.close[0]
            self.prices[self.strategy.datetime.date()] = prices

    def create_analysis(self):
        self.rets = {}
        self.prices = {}
        self.ranks = []
        self.vals = 0.0

    def notify_cashvalue(self, cash, value):
        self.vals = (cash, value)
        self.rets[self.strategy.datetime.datetime()] = self.vals

    def get_analysis(self):
        return self.ranks, self.prices


class CashMarket(bt.analyzers.Analyzer):
    def start(self):
        super(CashMarket, self).start()

    def create_analysis(self):
        self.rets = {}
        self.vals = 0.0

    def notify_cashvalue(self, cash, value):
        self.vals = (cash, value)
        self.rets[self.strategy.datetime.datetime()] = self.vals

    def get_analysis(self):
        return self.rets
