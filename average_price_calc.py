import requests as rq
import re
from datetime import datetime
import time
import logging

import json
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)


class AveragePrice:
    def __init__(self):
        self.exchange = str(data['exchange']).lower()
        self.market = str(data['market'])  # every exchange utilizes different format
        self.start_date = data['start_date']
        self.end_date = data['end_date']
        # must be in that format
        self.ts_start = int(time.mktime(datetime.strptime(self.start_date, "%d/%m/%Y %H").timetuple()))
        self.ts_end = int(time.mktime(datetime.strptime(self.end_date, "%d/%m/%Y %H").timetuple()))
        # ISO 8601 conversion
        self.ts_start_iso = datetime.fromtimestamp(self.ts_start).isoformat()
        self.ts_end_iso = datetime.fromtimestamp(self.ts_end).isoformat()

        if 'binance' or 'ascendex' or 'bitfinex' == self.exchange.lower():  # must be in milliseconds
            self.ts_start *= 1000
            self.ts_end *= 1000
        if 'coinbase' == self.exchange.lower():
            self.ts_start = self.ts_start_iso
            self.ts_end = self.ts_end_iso

        self.average = 0
        self.price_database = []
        self.price_endpoints = {
            'binance': [
                f"https://api.binance.com/api/v3/klines?symbol={self.market}&interval=1h&startTime={str(self.ts_start)}&endTime={str(self.ts_end)}",
                lambda res_data: res_data, 1],
            'coinbase': [
                f"https://api.exchange.coinbase.com/products/{self.market}/candles?start={str(self.ts_start)}&end={str(self.ts_end)}&granularity=3600",
                lambda res_data: res_data, 3],
            'gateio': [
                f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={self.market}&interval=1h&from={str(self.ts_start)}&to={str(self.ts_end)}",
                lambda res_data: res_data, -1],
            'kucoin': [
                f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={self.market}&startAt={str(self.ts_start)}&endAt={str(self.ts_end)}",
                lambda res_data: res_data['data'], 1],
            'ascendex': [
                f"https://ascendex.com/api/pro/v1/barhist?symbol={self.market}&interval=60&from={str(self.ts_start)}&to={str(self.ts_end)}",
                lambda res_data: res_data['data']],
            'bitfinex': [
                f"https://api-pub.bitfinex.com/v2/candles/trade:1h:{self.market}/hist?start={str(self.ts_start)}&end={str(self.ts_end)}",
                lambda res_data: res_data, 1],
        }

        self.start()

    def get_price(self):
        for exchange in self.price_endpoints.keys():
            if exchange == self.exchange:
                res = rq.get(self.price_endpoints.get(exchange)[0])
                if res.status_code != 200:
                    logging.error(f"{res.status_code}, check {exchange} and {self.market} in the config")
                    return
                else:
                    for price in self.price_endpoints.get(exchange)[1](res.json()):
                        if exchange == 'ascendex':
                            price = float(dict(price).get('data', {}).get('o'))
                            self.price_database.append(price)
                        else:
                            index = self.price_endpoints.get(exchange)[2]
                            price = float(price[index])
                            self.price_database.append(price)
                    logging.info(f"successfully fetched market {self.market} in {exchange}")
                    return

    def get_average(self):
        self.average = sum(self.price_database) / len(self.price_database)
        if self.average > 1:
            self.average = round(sum(self.price_database) / len(self.price_database), 5)
        logging.info(f"the amount of prices saved in the database is {len(self.price_database)} (= hours searched)")
        logging.info(f"the average price of the whole performance is {self.average}")
        return self.average

    def start(self):
        if self.exchange not in self.price_endpoints or re.search('[a-zA-Z]', self.start_date + self.end_date):
            raise Exception("config error")
        logging.info(f"start timestamp: {self.ts_start}, end timestamp: {self.ts_end}")
        self.get_price()
        self.get_average()


if __name__ == '__main__':
    AveragePrice()
