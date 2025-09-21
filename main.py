import json
import asyncio
from typing import Optional, List

from attr import dataclass
from binanceApi import binanceApi
from binanceApi.telegramBot import tg_bot
from config_handler import config


@dataclass
class Alert:
    breached_parameter: str
    breach_value: float
    breach_paramater_value: float
    symbol: Optional[str] = None
    action: Optional[str] = None


async def run_periodic_health_check(application):
    while True:
        print("performing health check")
        try:
            alerts: List[Alert] = []
            health_data = await binanceApi.health_check()
            exposures = health_data["exposures"]
            for key, exposure in exposures.items():
                if exposure > config.max_exposure_per_symbol:
                    alerts.append(Alert("Max exposure per symbol", exposure, config.max_exposure_per_symbol, key))

            open_orders_per_symbol = health_data["openOrdersPerSymbol"]
            for key, open_orders in open_orders_per_symbol.items():
                if open_orders > config.max_orders_per_symbol:
                    result = binanceApi.close_all_open_orders(key)
                    alerts.append(Alert("Max order per symbol", open_orders, config.max_orders_per_symbol, key, result))
            
            total_orders = health_data["totalOpenOrders"]
            if total_orders > config.max_total_orders:
                alerts.append(Alert("Max total orders breached", total_orders, config.max_total_orders))
            
            total_exposure = health_data["totalExposure"]
            if total_exposure > config.max_total_exposure:
                alerts.append(Alert("Max total exposure", total_exposure, config.max_total_exposure))


            if alerts:
                for alert in alerts:
                    if alert.symbol in config.ignore_symbols:
                        continue
                    
                    alert_message = "*ALERT* "
                    if alert.symbol is not None:
                        alert_message += f"{alert.breached_parameter}({alert.breach_paramater_value}) breached by {alert.symbol}({alert.breach_value}) "
                    else:
                        alert_message += f"{alert.breached_parameter}({alert.breach_paramater_value}) breached. Value: {alert.breach_value}"
                    
                    if alert.action is not None:
                        alert_message += f"\nAction taken: {alert.action}"
                        print(alert.action)
                        
                    await tg_bot.send_alert_message(application, alert_message, alert.symbol)
                print("alert message sent")
            else:
                print("System is healthy")
        except Exception as e:
            print(f"An error occurred during periodic health check: {e}")

        await asyncio.sleep(config.health_check_frequency)


async def main():
    application = tg_bot.initializeBot(config.tg_bot_token)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()



    await run_periodic_health_check(application)




if __name__ == "__main__":
    asyncio.run(main())