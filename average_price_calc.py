import requests as rq
import re
from datetime import datetime
import logging

import json
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)
    

def calc_date_for_exchange(date, exchange):
    ts = int(datetime.strptime(date, "%m/%d/%Y %H").timestamp())
    if exchange in ('binance', 'ascendex', 'bitfinex'):
        ts *= 1000
    elif exchange == 'coinbase':
        # ISO 8601 conversion
        ts = datetime.fromtimestamp(ts).isoformat()
    return ts


def send_file_to_telegram(file: str, bot_id, conf):
    send_file = open(file, 'rb')
    res = rq.get(url=f"https://api.telegram.org/bot{bot_id}/sendDocument",
                 data={"chat_id": conf.get('chat_id')},
                 files={"document": send_file})
    logging.info('sent file to telegram') and send_file.close() if res.status_code == 200 else logging.error(
        f"couldn't send file to telegram, status: {res.status_code}, make sure your chat_id is correct")


def hours_from_ts(start, end) -> int:
    difference = datetime.strptime(end, "%m/%d/%Y %H") - datetime.strptime(start, "%m/%d/%Y %H")
    hours = int(difference.total_seconds() / 3600)
    return hours

class AveragePrice:
    def __init__(self):
        logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # formatting is crucial here
        self.market = str(data['market'])
        self.exchange = str(data['exchange']).lower()

        self.start_date = data['start_date']
        self.end_date = data['end_date']

        # must be in that format
        self.ts_start = calc_date_for_exchange(self.start_date, self.exchange)
        self.ts_end = calc_date_for_exchange(self.end_date, self.exchange)

        self.limit = hours_from_ts(self.start_date, self.end_date)
        self.average = 0
        self.price_database = []

        # TODO: pagination
        self.supported_exchanges = {
            'binance': [
                f"https://api.binance.com/api/v3/klines?symbol={self.market}&interval=1h&startTime={self.ts_start}&endTime={self.ts_end}",
                lambda res_data: res_data, 1],
            'coinbase': [lambda: rq.get(
                url='https://api.exchange.coinbase.com/'
                    f'products/{self.market}/candles',
                params={
                    'start': self.ts_start,
                    'end': self.ts_end,
                    'granularity': '3600',
                }
            ).json() if self.limit <= 300 else logging.error(f"your scope is too wide, max allowed is 300, "
                                                             f"yours is {self.limit}"), 3],
            'gateio': [lambda: rq.get(
                url='https://api.gateio.ws/api/v4/'
                    'spot/candlesticks',
                params={
                    'currency_pair': self.market,
                    'interval': '1h',
                    'from': self.ts_start,
                    'to': self.ts_end,
                }
            ).json() if self.limit <= 1000 else logging.error(f"your scope is too wide, max allowed is 1000, "
                                                              f"yours is {self.limit}"), 5],
            'kucoin': [lambda: rq.get(
                url='https://api.kucoin.com/api/v1/'
                    'market/candles',
                params={
                    'type': '1hour',
                    'symbol': self.market,
                    'startAt': self.ts_start,
                    'endAt': self.ts_end,
                }
            ).json()['data'] if self.limit <= 1500 else logging.error(f"your scope is too wide, max allowed is 1500, "
                                                                      f"yours is {self.limit}"), 1],
            'ascendex': [
                f"https://ascendex.com/api/pro/v1/barhist?symbol={self.market}&interval=60&from={self.ts_start}&to={self.ts_end}",
                lambda res_data: res_data['data'], None],
            'bitfinex': [lambda: rq.get(
                url='https://api-pub.bitfinex.com/v2/'
                    f'candles/trade:1h:{self.market}/hist',
                params={
                    'start': self.ts_start,
                    'end': self.ts_end,
                    'limit': '250',
                }
            ).json() if self.limit <= 250 else logging.error(f"your scope is too wide, max allowed is 250, "
                                                             f"yours is {self.limit}"), 1],
            'ftx': [
                f"https://ftx.com/api/markets/{self.market}/candles?resolution=3600&start_time={self.ts_start}&end_time={self.ts_end}",
                lambda res_data: res_data['result'], None],
            'bitmart': [lambda: rq.get(
                url='https://api-cloud.bitmart.com/'
                    'spot/v1/symbols/kline',
                params={
                    'symbol': self.market,
                    'step': '60',
                    'from': self.ts_start,
                    'to': self.ts_end,
                }
            ).json()['data']['klines'] if self.limit <= 500 else logging.error(f"your scope is too wide, max allowed is"
                                                                               f" 500, yours is {self.limit}"), 'open'],
        }

        self.start()

    def fetch_klines(self):
        vals = self.supported_exchanges[self.exchange]
        res, index, *_ = vals
        try:
            self.get_price(self.exchange, res(), index)
            logging.info(f"successfully fetched market {self.market} in {self.exchange}")
        except Exception as e:
            logging.error(f"{e}, check {self.exchange} and {self.market} in the config")

    def get_price(self, exchange: str, response: dict, index: int = None):
        for candle in (reversed(response) if exchange == 'kucoin' else response):
            if exchange == 'ascendex':
                price = float(dict(candle).get('data', {}).get('o'))
            elif exchange == 'ftx':
                price = float(dict(candle).get('open'))
            else:
                price = float(candle[index])

            if self.export_to_telegram:
                write_to_csv("a", exchange, self.market, price, len(self.price_database))

            logging.info(f"{price} {len(self.price_database)}")
            self.price_database.append(price)

    def get_average(self):
        if not self.price_database:
            logging.error(f"The API didn't fetch any data, check config")
        else:
            self.average = mean(self.price_database)
            if self.average > 1:
                self.average = round(self.average, 5)
            if self.export_to_telegram:
                write_to_csv("a", 'total hours:', len(self.price_database), 'average price:', self.average)

            logging.info(f"the amount of prices saved in the database is {len(self.price_database)} (= hours searched)")
            logging.info(f"the average price of the whole performance is {self.average}")

    def start(self):
        if self.exchange not in self.supported_exchanges.keys() or re.search('[a-zA-Z]',
                                                                             self.start_date + self.end_date):
            raise Exception("You have a typo in config or exchange is not supported, contact Mike")
        logging.info(f"start timestamp: {self.ts_start}, end timestamp: {self.ts_end}")

        if self.export_to_telegram:
            # WRITE HEADER
            write_to_csv("w", 'exchange', 'token', 'price', 'hour')

        self.fetch_klines()
        self.get_average()

        if self.export_to_telegram:
            send_file_to_telegram(file="average_price_calc.csv", bot_id=config.ef_reports_telegram, conf=self.config)


if __name__ == '__main__':
    AveragePrice()
