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
        # must be in that format
        self.ts_start = int(datetime.strptime(self.start_date, "%m/%d/%Y %H").timestamp())
        self.ts_end = int(datetime.strptime(self.end_date, "%m/%d/%Y %H").timestamp())
        # ISO 8601 conversion
        self.ts_start_iso = datetime.fromtimestamp(self.ts_start).isoformat()
        self.ts_end_iso = datetime.fromtimestamp(self.ts_end).isoformat()

        if self.exchange in ('binance', 'ascendex', 'bitfinex'):
            self.ts_start *= 1000
            self.ts_end *= 1000
        elif 'coinbase' == self.exchange:
            self.ts_start = self.ts_start_iso
            self.ts_end = self.ts_end_iso

        self.average = 0
        self.price_database = []

        self.start()

    def fetch_klines(self, market, start, end):
        for exchange, val in {
            'binance': [
                f"https://api.binance.com/api/v3/klines?symbol={market}&interval=1h&startTime={start}&endTime={end}",
                lambda res_data: res_data, 1],
            'coinbase': [
                f"https://api.exchange.coinbase.com/products/{market}/candles?start={start}&end={end}&granularity=3600",
                lambda res_data: res_data, 3],
            'gateio': [
                f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={market}&interval=1h&from={start}&to={end}",
                lambda res_data: res_data, -1],
            'kucoin': [
                f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={market}&startAt={start}&endAt={end}",
                lambda res_data: res_data['data'], 1],
            'ascendex': [
                f"https://ascendex.com/api/pro/v1/barhist?symbol={market}&interval=60&from={start}&to={end}",
                lambda res_data: res_data['data'], None],
            'bitfinex': [
                f"https://api-pub.bitfinex.com/v2/candles/trade:1h:{market}/hist?start={start}&end={end}",
                lambda res_data: res_data, 1],
            'ftx': [
                f"https://ftx.com/api/markets/{market}/candles?resolution=3600&start_time={start}&end_time={end}",
                lambda res_data: res_data['result'], None],
        }.items():
            url = val[0]
            fetch = val[1]
            index = val[2]
            if exchange == self.exchange:
                res = rq.get(url)
                if res.status_code != 200:
                    logging.error(f"{res.status_code}, check {exchange} and {market} in the config")
                    return
                else:
                    logging.info(f"successfully fetched market {market} in {exchange}")
                    return self.get_price(exchange, fetch(res.json()), index)


    def get_price(self, exchange, open_candle, index):
        for price in open_candle:
            if exchange == 'ascendex':
                price = float(dict(price).get('data', {}).get('o'))
                logging.info(f"{price} {len(self.price_database)}")
                self.price_database.append(price)
            elif exchange == 'ftx':
                price = float(dict(price).get('open'))
                logging.info(f"{price} {len(self.price_database)}")
                self.price_database.append(price)
            else:
                price = float(price[index])
                logging.info(f"{price} {len(self.price_database)}")
                self.price_database.append(price)
        return

    def get_average(self):
        try:
            self.average = sum(self.price_database) / len(self.price_database)
            if self.average > 1:
                self.average = round(sum(self.price_database) / len(self.price_database), 5)
            logging.info(f"the amount of prices saved in the database is {len(self.price_database)} (= hours searched)")
            logging.info(f"the average price of the whole performance is {self.average}")
            return self.average
        except ZeroDivisionError as zde:
            if self.exchange == 'coinbase':
                logging.error("Check the date in config, coinbase only allows 300 hours max (12.5 days)")
            else:
                logging.error(f"The API didn't fetch any data: {zde}, check config")

    def start(self):
        if re.search('[a-zA-Z]', self.start_date + self.end_date):
            raise Exception("date config error")
        logging.info(f"start timestamp: {self.ts_start}, end timestamp: {self.ts_end}")
        self.fetch_klines(self.market, self.ts_start, self.ts_end)
        self.get_average()


if __name__ == '__main__':
    AveragePrice()
