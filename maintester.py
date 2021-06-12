from datetime import datetime
import os
import matplotlib

import backtrader as bt
import backtrader.feeds as btfeeds

from binancedata import get_historical_data, Client

# Overall account balance
account_balance = 100000

# size of each trade in native currency
# ie if backtesting on ETH, each trade will be 1ETH in size
trade_size = 1

# in %
take_profit = 10
stop_loss = 5
# The difference betweent the current candle price compared to the previous one
# If higher than 1% we will buy
buy_trigger = 1

# Get historical data and store filename
# No need to run this if you already have historical data
# Simply comment out and re-assign your filename to 'ETHUSDT_1 Jan 2021.csv' for example
filename = get_historical_data('ETHUSDT', '1 Jan 2021', Client.KLINE_INTERVAL_1MINUTE)


# Create a Stratey
class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # open a position if the current candle price is higher by at least 1%
            # compared to the previous candle
            if self.dataclose[0] > self.dataclose[-1] + (self.dataclose[-1]*buy_trigger/100):

                    self.log('BUY CREATE, %.2f' % self.dataclose[0])

                    # Keep track of the created order to avoid a 2nd order
                    self.buy(size=trade_size, exectype=bt.Order.Market)
                    self.order = self.buy()

                    print(f'EXECUTED PRICE IS:{self.order.executed.price}')

        if self.position:
            if self.dataclose[0] > self.position.price + (self.position.price*take_profit/100) or  self.dataclose[0] < self.position.price - (self.position.price*stop_loss/100):

                # Already in the market ... we might sell
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.sell(size=trade_size, exectype=bt.Order.Market)
                self.order = self.sell()


if __name__ == '__main__':

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # load data from our CSV file
    data = btfeeds.GenericCSVData(

    # Create a Data Feed
    dataname=filename,
    fromdate=datetime(2021, 1, 1),
    todate=datetime(2021, 5, 24),
    nullvalue=0.0,
    dtformat=lambda x: datetime.utcfromtimestamp(float(x) / 1000.0),
    datetime=0,
    high=1,
    low=2,
    open=3,
    close=4,
    volume = -1,
    openinterest=-1
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(account_balance)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()
    cerebro.plot()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
