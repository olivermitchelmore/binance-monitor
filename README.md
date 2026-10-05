# Binance Monitor

A Telegram bot that watches a Binance USDS-margined futures account and sends an alert when a risk limit is breached.

> This project was written in September 2025 and published in October 2026 as an archive. It is not maintained and the pinned libraries are out of date.

## What it does

- Checks the account on a timer (`healthCheckFrequency`, in seconds).
- Nets each asset's USDT and USDC positions into one exposure and prints any leg that has no hedge.
- Alerts when exposure per asset, total exposure, open orders per symbol or total open orders pass their limits.
- Cancels a symbol's open orders when its order limit is breached.
- Estimates funding payments per symbol over 8 hours, a day and a year.

## Telegram commands

| Command | Action |
|---|---|
| `/health` | Send the current exposures, open orders and funding estimates |
| `/igadd SYMBOL`, `/igrm SYMBOL` | Add or remove a symbol from the alert ignore list |
| `/igfadd SYMBOL`, `/igfrm SYMBOL` | Add or remove a symbol from the funding ignore list |
| `/iglist` | Show the alert ignore list |

Alerts go to the chat IDs in `whitelistedChatIds`, and commands from any other chat are ignored.

## Run

```sh
pip install -r requirements.txt
cp binanceApi/config.example.json binanceApi/config.json   # then fill in your keys
python main.py
```

The bot cancels orders on the account it is given. Use an API key with the permissions you intend.

## Licence

GPL-3.0. See `LICENSE`.
