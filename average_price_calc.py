import requests as rq
import re
from datetime import datetime
import logging

import json
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)


class AveragePrice:
    def __init__(self):
        logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        self.exchange = str(data['exchange']).lower()
        self.market = str(data['market'])  # every exchange utilizes different format
        self.start_date = data['start_date']
        self.end_date = data['end_date']

        def calc_date_for_exchange(date, exchange):
            # must be in that format
            ts = int(datetime.strptime(date, "%m/%d/%Y %H").timestamp())
            if exchange in ('binance', 'ascendex', 'bitfinex'):
                ts *= 1000
            elif exchange == 'coinbase':
                # ISO 8601 conversion
                ts = datetime.fromtimestamp(ts).isoformat()
            return ts

        self.ts_start = calc_date_for_exchange(self.start_date, self.exchange)
        self.ts_end = calc_date_for_exchange(self.end_date, self.exchange)

        self.average = 0
        self.price_database = []

        self.price_endpoints = {
            'binance': [
                f"https://api.binance.com/api/v3/klines?symbol={self.market}&interval=1h&startTime={self.ts_start}&endTime={self.ts_end}",
                lambda res_data: res_data, 1],
            'coinbase': [
                f"https://api.exchange.coinbase.com/products/{self.market}/candles?start={self.ts_start}&end={self.ts_end}&granularity=3600",
                lambda res_data: res_data, 3],
            'gateio': [
                f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={self.market}&interval=1h&from={self.ts_start}&to={self.ts_end}",
                lambda res_data: res_data, -1],
            'kucoin': [
                f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={self.market}&startAt={self.ts_start}&endAt={self.ts_end}",
                lambda res_data: res_data['data'], 1],
            'ascendex': [
                f"https://ascendex.com/api/pro/v1/barhist?symbol={self.market}&interval=60&from={self.ts_start}&to={self.ts_end}",
                lambda res_data: res_data['data'], None],
            'bitfinex': [
                f"https://api-pub.bitfinex.com/v2/candles/trade:1h:{self.market}/hist?start={self.ts_start}&end={self.ts_end}",
                lambda res_data: res_data, 1],
            'ftx': [
                f"https://ftx.com/api/markets/{self.market}/candles?resolution=3600&start_time={self.ts_start}&end_time={self.ts_end}",
                lambda res_data: res_data['result'], None],
        }

        self.start()

    def fetch_klines(self):
        vals = self.price_endpoints[self.exchange]
        url, fetch, index, *_ = vals
        res = rq.get(url)
        if res.status_code != 200:
            logging.error(f"{res.status_code}, check {self.exchange} and {self.market} in the config")
        else:
            logging.info(f"successfully fetched market {self.market} in {self.exchange}")
            return self.get_price(self.exchange, fetch(res.json()), index)

    def get_price(self, exchange, open_candle, index):
        for price in open_candle:
            if exchange == 'ascendex':
                price = float(dict(price).get('data', {}).get('o'))
            elif exchange == 'ftx':
                price = float(dict(price).get('open'))
            else:
                price = float(price[index])

            logging.info(f"{price} {len(self.price_database)}")
            self.price_database.append(price)

    def get_average(self):
        if len(self.price_database) == 0:
            if self.exchange == 'coinbase':
                logging.error("Check the date in config, coinbase only allows 300 hours max (12.5 days)")
            else:
                logging.error(f"The API didn't fetch any data, check config, if persists contact Mike")
        else:
            self.average = sum(self.price_database) / len(self.price_database)
            if self.average > 1:
                self.average = round(self.average, 5)
            logging.info(f"the amount of prices saved in the database is {len(self.price_database)} (= hours searched)")
            logging.info(f"the average price of the whole performance is {self.average}")

    def start(self):
        if self.exchange not in self.price_endpoints.keys() or re.search('[a-zA-Z]', self.start_date + self.end_date):
            raise Exception("You have a typo in config or exchange is not supported, contact Mike")
        logging.info(f"start timestamp: {self.ts_start}, end timestamp: {self.ts_end}")
        self.fetch_klines()
        self.get_average()


if __name__ == '__main__':
    AveragePrice()
