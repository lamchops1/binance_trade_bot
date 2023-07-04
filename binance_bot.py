from binance import Client
from datetime import datetime
import math
import time
import win32api
import json

class binance_bot:
    def __init__(self):
        self.api_key = '6JF4sLJSNDTqs8q8RQKprpFZkd1H4VMgLiiQkhqKUloDlael58OOGQGfL3WXfWRq'
        self.secret_key = 'lbvbRQVjAVig6Xrkzhcmdz5ZYJuC78NlPSkryl8xjvGyxFqJ9Wq9NuRKU6ZBxeDn'
        self.total_value_aud = 0
        self.total_value_busd = 0
        self.busd_threshold = 0.3
        self.wallet_limit = 5
        self.wallet = {}

    def get_server_time(self, client):
        get_time = client.get_server_time()
        set_time=time.gmtime(int((get_time["serverTime"])/1000))
        win32api.SetSystemTime(set_time[0], set_time[1], 0, set_time[2], set_time[3], set_time[4], set_time[5], 0)
        time.sleep(1)

    def binance_login(self):
        client = Client(self.api_key, self.secret_key)
        print("Successfully logged in!\n")
        time.sleep(1)
        return client

    def load_coin_list(self):
        with open("coin_list.txt") as f:
            coin_list = f.readlines()
        coins = [coin.strip() + "BUSD" for coin in coin_list]
        print("Coin list succesfully loaded!\n")
        time.sleep(1)
        return coins

    def get_account_summary(self, client):
        account = client.get_account()
        self.open_wallet()
        for balance in account['balances']:
            aud_value = self.convert_to_aud(client, balance)
            if aud_value > 0.5:
                self.total_value_aud += aud_value
        print("COINS CURRENTLY OWNED:", self.wallet)
        print("TOTAL ACCOUNT VALUE:", "$", self.total_value_aud, "AUD\n")
        time.sleep(2)

    def convert_to_aud(self, client, balance):
        if float(balance['free']) > 0.0000001 and balance['asset'] != "LUN":

            if balance['asset'] == "AUD":
                value = (float(balance['free']))
            elif balance['asset'] == "BUSD":
                value = (float(balance['free']) / float(client.get_symbol_ticker(symbol="BTCBUSD")['price'])) * float(client.get_symbol_ticker(symbol="BTCAUD")['price'])
            elif balance['asset'] == "BTC":
                value = (float(balance['free']) * float(client.get_symbol_ticker(symbol="BTCAUD")['price']))
            else:
                try:
                    value = (float(balance['free']) * float(client.get_symbol_ticker(symbol=balance['asset'] + "BTC")['price'])) * float(client.get_symbol_ticker(symbol="BTCAUD")['price'])
                except:
                    value = ((float(balance['free']) * float(client.get_symbol_ticker(symbol=balance['asset'] + "BUSD")['price'])) / float(client.get_symbol_ticker(symbol="BTCBUSD")['price'])) * float(client.get_symbol_ticker(symbol="BTCAUD")['price'])
            return value
        else:
            return 0

    def open_wallet(self):
        with open('binance_trades.json', 'r') as file:
            try:
                self.wallet = json.load(file)
            except:
                pass

    def store_coin(self, coin_name, buy_price):
        self.wallet[coin_name] = buy_price
        with open('binance_trades.json', 'w') as file:
            json.dump(self.wallet, file)

    def remove_coin(self, coin_name):
        self.wallet.pop(coin_name)
        with open('binance_trades.json', 'w') as file:
            json.dump(self.wallet, file)

    def get_coin_prices(self, client, coin):
        prices = client.get_historical_klines(coin, Client.KLINE_INTERVAL_1MINUTE, "5 minutes ago UTC")
        return prices

    def get_kline_summary(self, kline):
        clock = datetime.fromtimestamp(kline[0]/1000)
        open_price = float(kline[1])
        highest_price = float(kline[2])
        lowest_price = float(kline[3])
        close_price = float(kline[4])
        return clock, open_price, highest_price, lowest_price, close_price

    def check_buy_eligibility(self, client, coin_name): # 1) Must have more than 40% of BUSD   2) Must not already have that coin  3) Wallet must not be full (6 coins)
        print("Found coin:", coin_name, "...")
        busd_value = float(client.get_asset_balance("BUSD")['free'])
        self.total_value_busd = self.convert_aud_to_busd(client, self.total_value_aud)

        condition_one = True if (busd_value/self.total_value_busd > self.busd_threshold) else False
        condition_two = True if coin_name not in self.wallet else False
        condition_three = True if len(self.wallet) < self.wallet_limit else False
        self.fail_reason(condition_one, condition_two, condition_three)
        return True if condition_one and condition_two and condition_three is True else False

    def fail_reason(self, condition_one, condition_two, condition_three):
        if not condition_one and not condition_two and not condition_three:
            print("Unable to buy coin, spend limit exceeded, coin already bought and wallet is full!\n")
        elif not condition_one and not condition_two and condition_three:
            print("Unable to buy coin, spend limit exceeded and coin already bought!\n")
        elif not condition_one and condition_two and not condition_three:
            print("Unable to buy coin, spend limit exceeded and wallet is full!\n")
        elif condition_one and not condition_two and not condition_three:
            print("Unable to buy coin, coin already bought and wallet is full!\n")
        else:
            if not condition_one:
                print("Unable to buy coin, spend limit exceeded!\n")
            if not condition_two:
                print("Unable to buy coin, coin already bought!\n")
            if not condition_three:
                print("Unable to buy coin, wallet is full!\n")

    def check_sell_eligibility(self, coin, sell_price):
        if coin in self.wallet:
            buy_price = float(self.wallet[coin])
            profit = ((sell_price - buy_price) / sell_price) * 100
            return True if profit > 0.5 else False
        return False

    def convert_aud_to_busd(self, client, aud_coin):
        busd_coin = (aud_coin / float(client.get_symbol_ticker(symbol="BTCAUD")['price'])) * float(client.get_symbol_ticker(symbol="BTCBUSD")['price'])
        return busd_coin

    def buy_coin(self, client, coin_name, buy_price):
        print("Buying", coin_name, "...")
        busd_value = float(client.get_asset_balance("BUSD")['free'])
        buy_quantity = round(busd_value / self.wallet_limit / buy_price, 6)
        buy_quantity = self.transaction_filters(client, coin_name, buy_quantity, buy_price)
        order = client.order_market_buy(symbol=coin_name, quantity=buy_quantity)
        order_id = order['orderId']
        for i in order['fills']:
            buy_price = i['price']
        while True:
            time.sleep(4)
            confirm_order = client.get_order(symbol=coin_name, orderId=order_id)
            if confirm_order['status'] == 'FILLED':
                self.store_coin(coin_name, buy_price)
                print("Coin bought!\n")
                break

    def sell_coin(self, client, coin_name, sell_price):
        print("Selling", coin_name, "...")
        account = client.get_account()
        for balance in account['balances']:
            if balance["asset"] + "BUSD" == coin_name:
                sell_quantity = float(balance["free"])
        sell_quantity = self.transaction_filters(client, coin_name, sell_quantity, sell_price)
        order = client.order_market_sell(symbol=coin_name, quantity=sell_quantity)
        sell_price, buy_price = 0, 0
        order_id = order['orderId']
        for i in order['fills']:
            sell_price = float(i['price'])
            buy_price = float(self.wallet[coin_name])
        while True:
            time.sleep(4)
            confirm_order = client.get_order(symbol=coin_name, orderId=order_id)
            if confirm_order['status'] == 'FILLED':
                self.remove_coin(coin_name)
                profit = ((sell_price - buy_price) / sell_price) * 100
                print("Coin sold! Profit:", round(profit, 4), "%\n")
                break

    def transaction_filters(self, client, coin_name, quantity, price):
        print("quantity:", quantity)
        print("price:", price)
        step_size, step_size_mod = 0, 0
        coin_info = client.get_symbol_info(coin_name)
        for i in coin_info['filters']:
            if i['filterType'] == 'LOT_SIZE':
                step_size = float(i['stepSize'])
                step_size_mod = i['stepSize'].find('1') - 2
                print(step_size)
                quantity = math.floor(quantity * 10 ** step_size_mod) / float(10 ** step_size_mod)
            if i['filterType'] == 'MIN_NOTIONAL':
                print("price * quantity:", price * quantity)
                print("minNotional:",float(i['minNotional']) )
                if price * quantity < float(i['minNotional']):
                    print("step size", step_size)
                    quantity = float(i['minNotional']) / price
                    quantity = math.ceil(quantity * 10 ** step_size_mod) / float(10 ** step_size_mod)
        print("quantity:", quantity)
        return quantity


    def price_changes(self, coin_name, sell_price):
        if coin_name in self.wallet:
            buy_price = float(self.wallet[coin_name])
            profit = ((sell_price - buy_price) / sell_price) * 100
            print(coin_name, profit, "%")
