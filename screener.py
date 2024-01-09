import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

# Load environment variables from a .env file
load_dotenv()

# Use environment variables for sensitive information
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")

# Initialize the scheduler
scheduler = BackgroundScheduler()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Group-specific opening range prices
group_opening_range_prices = {}

# List of stock tickers
tickers_to_track = ["ABB.NS", "AARTIIND.NS", "ADANIPORTS.NS", "ALKEM.NS", "APOLLOTYRE.NS", "ASTRAL.NS", "AXISBANK.NS", "BAJAJFINSV.NS", "BAJAJ-AUTO.NS", "BALKRISIND.NS", "BANKBARODA.NS", "BEL.NS", "BPCL.NS", "BSOFT.NS", "BAJFINANCE.NS", "BALRAMCHIN.NS", "BATAINDIA.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BOSCHLTD.NS", "BANDHANBNK.NS", "BERGEPAINT.NS", "BIOCON.NS", "BRITANNIA.NS", "COALINDIA.NS", "CONCOR.NS", "CUMMINSIND.NS", "CANBK.NS", "CIPLA.NS", "COFORGE.NS", "COROMANDEL.NS", "CHAMBLFERT.NS", "CUB.NS", "COLPAL.NS", "CROMPTON.NS", "DLF.NS", "DEEPAKNI.NS", "DIXON.NS", "DALBHARAT.NS", "DIVISLAB.NS", "DRREDDY.NS", "DABUR.NS", "DELTACORP.NS", "LALPATHLAB.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GODREJCP.NS", "GRASIM.NS", "GMRINFRA.NS", "GODREJPROP.NS", "GUJGASLTD.NS", "GLENMARK.NS", "GRANULES.NS", "GNFC.NS", "HCLTECH.NS", "HDFCLIFE.NS", "HINDALCO.NS", "HINDPETRO.NS", "HDFCAMC.NS", "HAVELLS.NS", "HAL.NS", "HINDUNILVR.NS", "HDFCBANK.NS", "HEROMOTOCO.NS", "HINDCOPPER.NS", "ICICIBANK.NS", "IDFCFIRSTB.NS", "INDIACEM.NS", "INDHOTEL.NS", "IGL.NS", "NAUKRI.NS", "IPCALAB.NS", "ICICIGI.NS", "IDFC.NS", "INDIAMART.NS", "IOC.NS", "INDUSTOWER.NS", "INFY.NS", "ICICIPRULI.NS", "ITC.NS", "IEX.NS", "IRCTC.NS", "INDUSINDBK.NS", "INDIGO.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JINDALSTEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "L&TFH.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS", "LAURUSLABS.NS", "LUPIN.NS", "MRF.NS", "MGL.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MFSL.NS", "METROPOLIS", "MPHASIS.NS", "MCX.NS", "MUTHOOTFIN.NS", "NMDC.NS", "NTPC.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "OBEROIRLTY.NS", "ONGC.NS", "OFSS.NS", "PIIND.NS", "PVRINOX.NS", "PAGEIND.NS", "PERSISTENT.NS", "PETRONET.NS", "PIDILITIND.NS", "PEL.NS", "POLYCAB.NS", "PFC.NS", "POWERGRID.NS", "PNB.NS", "RBLBANK.NS", "RECLTD.NS", "RELIANCE.NS", "SBICARD.NS", "SBILIFE.NS", "SRF.LTD", "MOTHERSON.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SBIN.NS", "SAIL.NS", "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", "TVSMOTOR.NS", "TATACHEM.NS", "TATACOMM.NS", "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TECHM.NS", "RAMCOCEM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", "UPL.NS", "ULTRACEMCO.NS", "UBL.NS", "MCDOWELL-N.NS", "VEDL.NS", "IDEA.NS", "VOLTAS.NS", "WIPRO.NS", "ZEEL.NS", "ZYDUSLIFE.NS"]

# Dictionary to track whether an alert has been sent for each ticker
alert_sent = {}

# Function to get stock data from Yahoo Finance using BeautifulSoup with headers
def get_stock_data(ticker):
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}

        url = f"https://finance.yahoo.com/quote/{ticker}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            current_price_element = soup.select_one('[data-test="qsp-price"]')

            if current_price_element:
                current_price = float(current_price_element.get('value').replace(",", ""))
                return {"ticker": ticker, "current_price": current_price}

    except Exception as e:
        logging.error(f"Error fetching stock data for {ticker}: {str(e)}")

    return {"ticker": ticker, "current_price": None}

# Function to send a price alert to the group
def send_group_price_alert(ticker, current_price, alert_type):
    message = f"Price Alert for {ticker}: Current Price {current_price} has crossed {alert_type} price between 9:15 to 9:20"
    
    telegram_api_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {
        "chat_id": group_chat_id,
        "text": message,
    }

    response = requests.post(telegram_api_url, data=data)

    if response.status_code == 200:
        logging.info(f"Alert sent to group {group_chat_id}")
    else:
        logging.error(f"Failed to send alert. Telegram API response: {response.status_code}, {response.text}")

# Function to handle group messages and check if the current price crosses limits
def group_message():
    for ticker in tickers_to_track:
        price_data = get_stock_data(ticker)

        if price_data['current_price'] is not None:
            current_price = price_data['current_price']

            if ticker not in group_opening_range_prices:
                group_opening_range_prices[ticker] = {"highest": current_price, "lowest": current_price}
            else:
                highest_price = group_opening_range_prices[ticker]["highest"]
                lowest_price = group_opening_range_prices[ticker]["lowest"]

                if current_price > highest_price:
                    group_opening_range_prices[ticker]["highest"] = current_price
                    send_group_price_alert(ticker, current_price, "highest")
                    alert_sent[ticker] = True
                elif current_price < lowest_price:
                    group_opening_range_prices[ticker]["lowest"] = current_price
                    send_group_price_alert(ticker, current_price, "lowest")
                    alert_sent[ticker] = True

# Schedule the script to start at 9:00 AM every weekday
scheduler.add_job(
    group_message,
    trigger=CronTrigger(hour=9, minute=0, second=0, day_of_week="mon-fri"),
    id='start_job'
)

# Schedule the script to stop at 3:30 PM every weekday
scheduler.add_job(
    scheduler.shutdown,  # Assuming the shutdown method stops the scheduler
    trigger=CronTrigger(hour=15, minute=30, second=0, day_of_week="mon-fri"),
    id='stop_job',
)

# Schedule the script to refresh every day (including Saturday and Sunday) at midnight
scheduler.add_job(
    lambda: scheduler.reschedule_job('start_job', trigger='cron', hour=0, minute=0, second=0, day_of_week="*"),
    trigger=CronTrigger(hour=0, minute=0, second=0),
    id='refresh_job',
)

# Start the scheduler
scheduler.start()
