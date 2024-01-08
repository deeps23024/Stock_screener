from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from telegram.ext import CallbackContext
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import logging

# Load environment variables from a .env file
load_dotenv()

# Use environment variables for sensitive information
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize the list of users who subscribed to alerts
subscribed_users = set()

# List of stock tickers
stock_tickers = ["ABB.NS", "AARTIIND.NS", "ADANIPORTS.NS", "ALKEM.NS", "APOLLOTYRE.NS", "ASTRAL.NS", "AXISBANK.NS", "BAJAJFINSV.NS", "BAJAJ-AUTO.NS", "BALKRISIND.NS", "BANKBARODA.NS", "BEL.NS", "BPCL.NS", "BSOFT.NS", "BAJFINANCE.NS", "BALRAMCHIN.NS", "BATAINDIA.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BOSCHLTD.NS", "BANDHANBNK.NS", "BERGEPAINT.NS", "BIOCON.NS", "BRITANNIA.NS", "COALINDIA.NS", "CONCOR.NS", "CUMMINSIND.NS", "CANBK.NS", "CIPLA.NS", "COFORGE.NS", "COROMANDEL.NS", "CHAMBLFERT.NS", "CUB.NS", "COLPAL.NS", "CROMPTON.NS", "DLF.NS", "DEEPAKNI.NS", "DIXON.NS", "DALBHARAT.NS", "DIVISLAB.NS", "DRREDDY.NS", "DABUR.NS", "DELTACORP.NS", "LALPATHLAB.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GODREJCP.NS", "GRASIM.NS", "GMRINFRA.NS", "GODREJPROP.NS", "GUJGASLTD.NS", "GLENMARK.NS", "GRANULES.NS", "GNFC.NS", "HCLTECH.NS", "HDFCLIFE.NS", "HINDALCO.NS", "HINDPETRO.NS", "HDFCAMC.NS", "HAVELLS.NS", "HAL.NS", "HINDUNILVR.NS", "HDFCBANK.NS", "HEROMOTOCO.NS", "HINDCOPPER.NS", "ICICIBANK.NS", "IDFCFIRSTB.NS", "INDIACEM.NS", "INDHOTEL.NS", "IGL.NS", "NAUKRI.NS", "IPCALAB.NS", "ICICIGI.NS", "IDFC.NS", "INDIAMART.NS", "IOC.NS", "INDUSTOWER.NS", "INFY.NS", "ICICIPRULI.NS", "ITC.NS", "IEX.NS", "IRCTC.NS", "INDUSINDBK.NS", "INDIGO.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JINDALSTEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "L&TFH.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS", "LAURUSLABS.NS", "LUPIN.NS", "MRF.NS", "MGL.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MFSL.NS", "METROPOLIS", "MPHASIS.NS", "MCX.NS", "MUTHOOTFIN.NS", "NMDC.NS", "NTPC.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "OBEROIRLTY.NS", "ONGC.NS", "OFSS.NS", "PIIND.NS", "PVRINOX.NS", "PAGEIND.NS", "PERSISTENT.NS", "PETRONET.NS", "PIDILITIND.NS", "PEL.NS", "POLYCAB.NS", "PFC.NS", "POWERGRID.NS", "PNB.NS", "RBLBANK.NS", "RECLTD.NS", "RELIANCE.NS", "SBICARD.NS", "SBILIFE.NS", "SRF.LTD", "MOTHERSON.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SBIN.NS", "SAIL.NS", "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", "TVSMOTOR.NS", "TATACHEM.NS", "TATACOMM.NS", "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TECHM.NS", "RAMCOCEM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", "UPL.NS", "ULTRACEMCO.NS", "UBL.NS", "MCDOWELL-N.NS", "VEDL.NS", "IDEA.NS", "VOLTAS.NS", "WIPRO.NS", "ZEEL.NS", "ZYDUSLIFE.NS"]

# Dictionary to track whether an alert has been sent for each ticker
alert_sent = {ticker: False for ticker in stock_tickers}

# Dictionary to store the opening range prices for each stock
opening_range_prices = {}

# Function to get stock data from Yahoo Finance using BeautifulSoup with headers
def get_stock_data(ticker):
    try:
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
        }

        url = f"https://finance.yahoo.com/quote/{ticker}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            opening_range_element = soup.find('div', attrs={'data-test': 'OPENING_RANGE'})

            if opening_range_element:
                opening_range_price = float(opening_range_element.text.replace(",", ""))
                current_price_element = soup.select_one('[data-test="qsp-price"]')

                if current_price_element:
                    current_price = float(current_price_element.get('value').replace(",", ""))

                    return {"ticker": ticker, "opening_range_price": opening_range_price, "current_price": current_price}

    except Exception as e:
        logging.error(f"Error fetching stock data for {ticker}: {str(e)}")

    return {"ticker": ticker, "opening_range_price": None, "current_price": None}


# Function to send a price alert to a user group
def send_group_price_alert(context: CallbackContext, chat_ids, ticker, current_price):
    message = f"Price Alert for {ticker}: Current Price {current_price}"
    for chat_id in chat_ids:
        context.bot.send_message(chat_id=chat_id, text=message)
    logging.info(f"Alert sent to group {chat_ids}")

# Function to check and send price alerts via Telegram for all subscribed users
def check_price_alerts(context: CallbackContext):
    current_time = datetime.now().time()

    # Check if the current time is within the specified range (9:15 to 9:20)
    if time(9, 15) <= current_time <= time(9, 20):
        subscribed_user_ids = list(subscribed_users)

        for ticker in alert_sent.keys():
            # Check if an alert has already been sent for the current ticker
            if not alert_sent.get(ticker, False):
                price_data = get_stock_data(ticker)

                if price_data['opening_range_price'] is not None and price_data['current_price'] is not None:
                    opening_range_price = price_data['opening_range_price']
                    current_price = price_data['current_price']

                    # Compare opening range price with current price
                    if current_price > opening_range_price:
                        message = f"Price Alert for {ticker}: Current Price {current_price} is greater than Opening Range Price {opening_range_price}"
                    elif current_price < opening_range_price:
                        message = f"Price Alert for {ticker}: Current Price {current_price} is less than Opening Range Price {opening_range_price}"
                    else:
                        # Prices are equal, no alert
                        continue

                    send_group_price_alert(context, subscribed_user_ids, ticker, message)
                    alert_sent[ticker] = True


# Set up scheduler with the default jobstore
scheduler = BackgroundScheduler()

# Schedule the check_price_alert function every 4 minutes for each stock ticker within the specified time range
for ticker in stock_tickers:
    scheduler.add_job(check_price_alerts, trigger=IntervalTrigger(minutes=4),
                      args=[None])

# Start the scheduler
scheduler.start()

# Keep the script running
try:
    while True:
        pass
except (KeyboardInterrupt, SystemExit):
    # Shut down the scheduler gracefully before exiting
    scheduler.shutdown()
