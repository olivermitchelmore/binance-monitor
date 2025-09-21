import json
from binanceApi import binanceApi


class _Config:
    def __init__(self):
        self.tg_bot_token = None
        self.max_orders_per_symbol = None
        self.max_total_orders = None
        self.max_exposure_per_symbol = None
        self.max_total_exposure = None
        self.health_check_frequency = None
        self.api_key = None
        self.api_secret = None
        self.ignore_symbols = None
        self.ignore_funding_symbols = None
        self.white_listed_ids = None
        self.load_config()

    def load_config(self):
        with open('binanceApi/config.json', 'r') as f:
            config = json.load(f)

        self.tg_bot_token = str(config["botToken"])
        self.max_orders_per_symbol = int(config['maxOrdersPerSymbol'])
        self.max_total_orders = int(config['maxTotalOrders'])
        self.max_exposure_per_symbol = float(config['maxExposurePerSymbol'])
        self.max_total_exposure = float(config['maxTotalExposure'])
        self.health_check_frequency = int(config["healthCheckFrequency"])
        self.api_key = str(config["apiKey"])
        self.api_secret = str(config["apiSecret"])
        self.ignore_symbols = list(config["ignoreList"])
        self.ignore_funding_symbols = list(config["ignoreFunding"])
        self.white_listed_ids = set(config["whitelistedChatIds"])

        binanceApi.set_api_keys(self.api_key, self.api_secret)

    def update_ignore_list(self, symbol_to_update, add):
        if add:
            if symbol_to_update not in self.ignore_symbols:
                self.ignore_symbols.append(symbol_to_update)
        else:
            if symbol_to_update in self.ignore_symbols:
                self.ignore_symbols.remove(symbol_to_update)

        with open('binanceApi/config.json', 'r+') as f:
            config = json.load(f)
            config['ignoreList'] = self.ignore_symbols
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()

    def update_ignore_funding_list(self, symbol_to_update, add):
        if add:
            if symbol_to_update not in self.ignore_funding_symbols:
                self.ignore_funding_symbols.append(symbol_to_update)
        else:
            if symbol_to_update in self.ignore_funding_symbols:
                self.ignore_funding_symbols.remove(symbol_to_update)

        with open('binanceApi/config.json', 'r+') as f:
            config = json.load(f)
            config['ignoreFunding'] = self.ignore_funding_symbols
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()

config = _Config()