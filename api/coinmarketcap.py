import os

from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import pandas as pd
from datetime import datetime

filename = 'market_cap.json'


def get_top_cryptos_by_market_volume(number):
    if redownload():
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        parameters = {
            'start': '1',
            'convert': 'USD'
        }
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': '',
        }

        session = Session()
        session.headers.update(headers)

        try:
            response = session.get(url, params=parameters)
            data = json.loads(response.text)
            save_json_to_file(data)

        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)

    return ["{}{}".format(coin['symbol'], 'USDT') for coin in get_data_from_file()['data']
            if not coin['symbol'].startswith('USD') and has_enough_data(coin)][:number]


def has_enough_data(coin):
    return (datetime.now() - pd.to_datetime(coin['date_added']).to_pydatetime().replace(tzinfo=None)).days > 365


def save_json_to_file(data):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)


def get_data_from_file():
    with open(filename, 'r') as json_data:
        return json.load(json_data)


def redownload():
    if not os.path.isfile(filename):
        return True
    data = get_data_from_file()
    return (datetime.now() - pd.to_datetime(data['status']['timestamp']).to_pydatetime().replace(tzinfo=None)).days > 1
