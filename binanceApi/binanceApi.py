import logging
from binance_common.configuration import ConfigurationRestAPI
from binance_common.constants import DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL
from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
import requests
import asyncio
import aiohttp

logging.basicConfig(level=logging.INFO)

client = None

def set_api_keys(api_key, api_secret):
    global client
    configuration = ConfigurationRestAPI(api_key=api_key, api_secret=api_secret, base_path=DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL)
    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

async def get_exposures(symbols_and_positions, symbols):
    try:
        usdt_pairs = {}
        usdc_pairs = {}

        prices = await get_prices_concurrently(symbols)

        for symbol, amount in symbols_and_positions.items():
            
            if symbol == ("USDCUSDT"):
                continue
            if symbol.endswith("USDT"):
                usdt_pairs[symbol.removesuffix("USDT")] = amount * prices[symbol]
            elif symbol.endswith("USDC"):
                usdc_pairs[symbol.removesuffix("USDC")] = amount * prices[symbol]
            else:
                print(f"Symbol {symbol} does not end with USDT or USDC")
        
        exposures = {}
        total_exposure = 0
        all_keys = set(usdt_pairs.keys()) | set(usdc_pairs.keys())

        for key in all_keys:
            usdt_amount = usdt_pairs.get(key, 0)
            usdc_amount = usdc_pairs.get(key, 0)
            
            combined_exposure = usdt_amount + usdc_amount
            exposures[key] = combined_exposure
            total_exposure += combined_exposure

            if usdt_amount == 0:
                print(f"Unhedged position (USDC only): {key}USDC Amount: {usdc_amount}")
            elif usdc_amount == 0:
                print(f"Unhedged position (USDT only): {key}USDT Amount: {usdt_amount}")

        return exposures, total_exposure



    except Exception as e:
        logging.error(f"Error getting account exposures: {e}")
        return None


def check_exposures(max_exposure, total_exposure_limit):
    exposures = get_exposures()
    if exposures is None:
        logging.warning("get_exposures returned None.")
        return

    total = 0
    for key, amount in exposures.items():
        total += amount
        if abs(amount) > max_exposure:
            print(f"Exposure for {key}({amount}) above max exposure({max_exposure})")
            
    if abs(total) > total_exposure_limit:
        print(f"Total Exposure({total}) breaching limit of({total_exposure_limit})")
        
def check_api():
    server_time = client.rest_api.check_server_time().data().server_time
    print(f"Server time: {server_time}")
    return server_time


def get_open_orders(open_orders):
    open_orders_per_symbol = {}
    try:
        order_counts = {}
        total_orders = 0
        for order in open_orders:
            symbol = order.symbol
            order_counts[symbol] = order_counts.get(symbol, 0) + 1
            total_orders += 1

        for symbol, count in order_counts.items():
            open_orders_per_symbol[symbol] = count

    except Exception as e:
        logging.error(f"Error getting open orders: {e}")
    return open_orders_per_symbol, total_orders


def get_symbols_and_positions():
    positions = {}

    try:
        account_info = client.rest_api.account_information_v3().data()
        for position in account_info.positions:
            position_amount = float(position.position_amt)
            if (position_amount) == 0:
                continue
            positions[position.symbol] = position_amount

    except Exception as e:
        logging.error(f"Error getting account info for funding prediction {e}")

    return positions



async def fetch_data(session, symbol):
    try:
        async with session.get(f"https://fapi.binance.com/fapi/v2/ticker/price?symbol={symbol}") as response:
            return await response.json()
    except aiohttp.ClientError as e:
        print(f"Error fetching {symbol} price: {e}")
        return None


async def fetch_funding_rates(session, symbol):
    try:
        async with session.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}") as response:
            return await response.json()
    except aiohttp.ClientError as e:
        print(f"Error fetching {symbol} price: {e}")
        return None



async def get_prices_concurrently(symbols: list):
    async def _fetch_all():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_data(session, symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks)
            price_list = {}
            for symbol, result in zip(symbols, results):
                if result and 'price' in result:
                    price_list[symbol] = float(result['price'])
            return price_list
    return await _fetch_all()


async def get_funding_rates_concurrently(symbols: list):
    async def _fetch_all():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_funding_rates(session, symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks)
            funding_rate_list = {}
            mark_price_list = {}
            for symbol, result in zip(symbols, results):
                if result and 'lastFundingRate' in result:
                    funding_rate_list[symbol] = float(result['lastFundingRate'])
                    mark_price_list[symbol] = float(result['markPrice'])
            return funding_rate_list, mark_price_list
    return await _fetch_all()


async def get_current_funding_prediction():
    positions = get_symbols_and_positions()
    symbols = []
    eight_hour_funding_payment_list = {}
    net_funding_payments = {}
    eight_hour_cum_funding = 0
    
    for key, amount in positions.items():
        symbols.append(key)
    funding_rates, mark_prices = await get_funding_rates_concurrently(symbols)
    funding_intervals = get_funding_info(symbols)
    eight_hour_usdcusdt_funding = 0
    
    for key, amount in positions.items():
        funding_payment = (amount * mark_prices[key]) * -funding_rates[key]
        funding_payment *= (8 / funding_intervals[key])
        eight_hour_funding_payment_list[key] = funding_payment
        if key == "USDCUSDT":
            eight_hour_usdcusdt_funding = funding_payment
            continue
        eight_hour_cum_funding += funding_payment

    return eight_hour_funding_payment_list, eight_hour_cum_funding, eight_hour_usdcusdt_funding

def get_funding_info(symbols):
    funding_info = requests.get("https://fapi.binance.com/fapi/v1/fundingInfo").json()
    funding_info_list = {}
    for info in funding_info:
        for symbol in symbols:
            if symbol == info["symbol"]:
                funding_info_list[symbol] = info["fundingIntervalHours"]
    return funding_info_list

def close_all_open_orders(symbol):
    result = f"successfully closed all open orders for symbol: {symbol}"
    try:
        client.rest_api.cancel_all_open_orders(symbol)
    except Exception as e:
        result = f"failed to close open orders for symbol {symbol} error: {e}"
        print(f"failed to close open orders for {symbol} error: {e}")
    return result



async def health_check():
    health = {}
    symbols = []
    symbols_and_positions = get_symbols_and_positions()
    account_info = client.rest_api.account_information_v3().data()
    open_orders = client.rest_api.current_all_open_orders().data()
    
    for symbol in symbols_and_positions.keys():
        symbols.append(symbol)

    exposures, total_exposure = await get_exposures(symbols_and_positions, symbols)
    open_orders_per_symbol, total_open_orders = get_open_orders(open_orders)
    eight_hour_funding_payment_list, eight_hour_cum_funding, eight_hour_usdcusdt_funding = await get_current_funding_prediction()


    health["totalExposure"] = total_exposure
    health["exposures"] = exposures
    health["openOrdersPerSymbol"] = open_orders_per_symbol
    health["totalOpenOrders"] = total_open_orders
    health["eightHourFundingPredictionPerSymbol"] = eight_hour_funding_payment_list
    health["eightHourCumFunding"] = eight_hour_cum_funding

    if eight_hour_usdcusdt_funding != 0:
        health["eightHourUsdcUsdtFunding"] = eight_hour_usdcusdt_funding

    

    return health 