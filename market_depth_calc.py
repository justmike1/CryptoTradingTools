import requests as rq

import json
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)

# TODO: add utilization for each exchange, add logging


class DepthCALC:
    def __init__(self):
        self.asset = data['asset']
        
        book = rq.get(f"https://data.gateapi.io/api2/1/orderBook/{self.asset}_usdt")
        asset_data = rq.get(f"https://data.gateapi.io/api2/1/ticker/{self.asset}_usdt")
        asset_price = json.loads(asset_data.content)
        
        self.orderbook = json.loads(book.content)
        self.first_ask_layer = self.orderbook['asks'][-1]
        self.first_ask_layer_usdt = float(self.first_ask_layer[0]) * float(self.first_ask_layer[1])
        self.mid_price = float(asset_price['last'])     # every exchange utilizing it differently
        self.first_bid_layer = self.orderbook['bids'][0]
        self.first_bid_layer_usdt = float(self.first_bid_layer[0]) * float(self.first_bid_layer[1])

    def first_layer(self):      # made for testing, if wanted call it in if __name__ == '__main__':
        print(f"first_ask_layer: {self.first_ask_layer} in USDT: {round(self.first_ask_layer_usdt, 4)}"
              f"\nmid_price: {self.mid_price}"
              f"\nfirst_bid_layer: {self.first_bid_layer} in USDT: {round(self.first_bid_layer_usdt, 4)}")

    def get_depth(self):
        ask_layers = []
        bid_layers = []
        ask_total = 0
        bid_total = 0
        percentage = 5      # the num that divides with 100 is the %
        depth = round((self.mid_price * float(percentage / 100)), 5)
        bid_depth = round(self.mid_price - depth, 5)
        ask_depth = round(self.mid_price + depth, 5)
        print(f"{percentage}% depth: {depth}; bid depth: {bid_depth}; ask depth: {ask_depth}")
        for ask_layer in self.orderbook['asks']:
            if ask_depth >= float(ask_layer[0]):
                print(f"ask layer: {ask_layer}")      # USE IF YOU WANT TO SEE LAYERS & TESTING
                ask_layers.append(ask_layer)
                cum_vol_asset = [ask_layers[-1][1]]
                cum_vol_asset = map(float, cum_vol_asset)
                for i in cum_vol_asset:
                    ask_total += float(i)
        print(f"total ASK cumulative volume of the base asset {self.asset.upper()} at {percentage}%:"
              f" {round(ask_total, 5)} ASSET {round(ask_total * self.mid_price, 5)} USDT")
        print(f"mid/last price: {self.mid_price}")
        for bid_layer in self.orderbook['bids']:
            if bid_depth <= float(bid_layer[0]):
                print(f"bid layer: {bid_layer}")      # USE IF YOU WANT TO SEE LAYERS & TESTING
                bid_layers.append(bid_layer)
                cum_vol_asset = [bid_layers[-1][1]]
                cum_vol_asset = map(float, cum_vol_asset)
                for i in cum_vol_asset:
                    bid_total += float(i)
        print(f"total BID cumulative volume of the base asset {self.asset.upper()} at {percentage}%:"
              f" {round(bid_total, 5)} ASSET {round(bid_total * self.mid_price, 5)} USDT")


if __name__ == '__main__':
    DepthCALC().get_depth()
