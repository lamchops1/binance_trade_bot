from binance_bot import binance_bot
import time

while True:
    try:
        bot = binance_bot()

        print("Logging into Binance...")
        client = bot.binance_login()

        print("Getting server time...\n")
        bot.get_server_time(client)

        print("Loading coin list...")
        coin_list = bot.load_coin_list()

        print("BINANCE ACCOUNT SUMMARY:\n========================")
        bot.get_account_summary(client)

        while True:
            for coin in coin_list:
                old_price, new_price = 0, 0
                prices = bot.get_coin_prices(client, coin)
                red_candles = 0
                for kline in prices:
                    clock, open_price, highest_price, lowest_price, close_price = bot.get_kline_summary(kline)
                    if close_price < open_price:
                        red_candles += 1
                if red_candles >= 4:
                    buy_verdict = bot.check_buy_eligibility(client, coin)
                    if buy_verdict:
                        bot.buy_coin(client, coin, close_price)
                sell_verdict = bot.check_sell_eligibility(coin, close_price)
                if sell_verdict:
                    bot.sell_coin(client, coin, close_price)
                bot.price_changes(coin, close_price)
    except:
        print("Unable to connect to Binance, trying again...")
        time.sleep(10)
