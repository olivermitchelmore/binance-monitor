import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from binanceApi import binanceApi
from config_handler import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

white_listed_ids = config.white_listed_ids


def whitelisted(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id not in white_listed_ids:
            return
        await handler(update, context)
    return wrapper
user_chat_ids = set()


def format_health_message(health):
    total_exposure = health["totalExposure"]
    exposures_per_symbol = health["exposures"]

    formatted_exposures = "Exposures:\n"
    for key, exposure in exposures_per_symbol.items():
        formatted_exposures += f"{key}: {round(exposure, 2)}\n"

    open_orders_per_symbol = health["openOrdersPerSymbol"]

    formatted_open_orders = "Open Orders:\n"
    for key, open_order_count in open_orders_per_symbol.items():
        formatted_open_orders += f"{key}: {open_order_count}\n"
    
    total_open_orders = health["totalOpenOrders"]

    usdcusdt_funding = health.get("eightHourUsdcUsdtFunding", 0)
    fprediction_per_symbol = health["eightHourFundingPredictionPerSymbol"] 
    cum_funding_prediction = health["eightHourCumFunding"]
    formatted_funding_prediction = "Funding per symbol:\n"
    for key, funding in fprediction_per_symbol.items():
        if key != "USDCUSDT" and key not in config.ignore_funding_symbols:
            formatted_funding_prediction += f"{key}: {round(funding, 2)}\n"

    for symbol in config.ignore_funding_symbols:
        cum_funding_prediction -= fprediction_per_symbol.get(symbol, 0)

    for symbol in config.ignore_symbols:
        total_open_orders -= open_orders_per_symbol.get(symbol, 0)
        total_exposure -= exposures_per_symbol.get(symbol, 0)

    return (f"{formatted_exposures}\n\n{formatted_open_orders}\n\n{formatted_funding_prediction}\n\n"
            f"Cum Funding:\n8 Hours: {round(cum_funding_prediction, 2)}\n"
            f"Daily: {round(cum_funding_prediction*3, 2)}\n"
            f"Yearly: {round((cum_funding_prediction*3)*365, 2)}\n\n"
            f"Total open orders: {total_open_orders}\n"
            f"Total exposure: {total_exposure}\n\n"
            f"USDCUSDT funding:\n8 hour: {round(usdcusdt_funding, 2)}\ndaily: {round(usdcusdt_funding*3, 2)}\nyearly: {round((usdcusdt_funding * 3) * 365, 2)}")

async def send_health_message(application, health_data):
    message = format_health_message(health_data)
    for chat_id in white_listed_ids:
        await application.bot.send_message(chat_id=chat_id, text=message)

async def send_alert_message(application, alert_message, symbol=None):
    keyboard = []
    if symbol:
        keyboard.append([
            InlineKeyboardButton(f"Ignore {symbol}", callback_data=f"ignore_{symbol}")
        ])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    for chat_id in white_listed_ids:
        await application.bot.send_message(chat_id=chat_id, text=alert_message, reply_markup=reply_markup)


@whitelisted
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("ignore_"):
        symbol = data.split("_")[1]
        config.update_ignore_list(symbol, True)
        await query.edit_message_text(text=f"Added {symbol} to ignore list.\nOriginal message:\n{query.message.text}")


@whitelisted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

@whitelisted
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="""commands:\n/health: get health update\n
    /igadd {{symbol}}: exclude symbol from exposure&open order checks\nigrm {{symbol}}: remove reinclude symbol in exposure&open order checks
    \n/igfadd {{symbol}}: exclude symbol from funding estimates\n/igfrm {{symbol}}: reinclude symbol in funding estimates""")


@whitelisted
async def ig_add_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    symbol = context.args[0]
    config.update_ignore_list(symbol, True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Added {symbol} to ignore list")

@whitelisted
async def ig_remove_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    symbol = context.args[0]
    config.update_ignore_list(symbol, False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Removed {symbol} from ignore list")


@whitelisted
async def ig_funding_add_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    symbol = context.args[0]
    config.update_ignore_funding_list(symbol, True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Added {symbol} to funding ignore list")

@whitelisted
async def display_alert_ig_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Ignore list:\n{config.ignore_symbols}")






@whitelisted
async def ig_funding_remove_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_chat_ids.add(update.effective_chat.id)
    symbol = context.args[0]
    config.update_ignore_funding_list(symbol, False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Removed {symbol} from funding ignore list")


@whitelisted
async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Sending health update to user")
    user_chat_ids.add(update.effective_chat.id)
    health_data = await binanceApi.health_check()
    message = format_health_message(health_data)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    

def initializeBot(token):
    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    health_handler = CommandHandler('health', health)
    ig_symbol_add_handler = CommandHandler('igadd', ig_add_symbol)
    ig_symbol_remove_handler = CommandHandler('igrm', ig_remove_symbol)
    ig_funding_add_handler = CommandHandler('igfadd', ig_funding_add_symbol)
    ig_funding_remove_handler = CommandHandler('igfrm', ig_funding_remove_symbol)
    ig_display_symbols_handler = CommandHandler('iglist', display_alert_ig_list)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(health_handler)
    application.add_handler(ig_symbol_add_handler)
    application.add_handler(ig_symbol_remove_handler)
    application.add_handler(ig_funding_add_handler)
    application.add_handler(ig_funding_remove_handler)
    application.add_handler(ig_display_symbols_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    return application
