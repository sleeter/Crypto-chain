import pybit.exceptions
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
import pandas as pd
import re
from pybit.unified_trading import HTTP
import time

apikey = '4USmcb9AKP3nJaeicGRve7mmVC2Pz70AidFTYH0DtogEbpID7rfPyARSgIwCLrnV'
secretkey = 'A2PcFLa6F304rQkkfVec2LhbGlEGLvrJVC0cs4dC2MqdNk5znfsWj494AuwueZ48'
client = Client(apikey, secretkey)

BYBIT_API_KEY = "pE2UcZ9IRVYUyvIh4l"
BYBIT_API_SECRET = "AREao0WtlFEjm04Tahjfv4TruyUDmMu1lDw3"
session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
)
def BinByBit():
    tickBinance = client.get_ticker()
    tickersBinanceUSDT = []
    tickersByBitUSDT = []
    tickers = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'LTCUSDT', 'QTUMUSDT', 'ADAUSDT', 'XRPUSDT', 'EOSUSDT', 'XLMUSDT', 'TRXUSDT', 'ETCUSDT', 'ICXUSDT', 'USDCUSDT', 'LINKUSDT', 'WAVESUSDT', 'HOTUSDT', 'ZILUSDT', 'ZRXUSDT', 'BATUSDT', 'ZECUSDT', 'DASHUSDT', 'OMGUSDT', 'THETAUSDT', 'ENJUSDT', 'MATICUSDT', 'ATOMUSDT', 'ONEUSDT', 'FTMUSDT', 'ALGOUSDT', 'DOGEUSDT', 'ANKRUSDT', 'CHZUSDT', 'BUSDUSDT', 'XTZUSDT', 'RENUSDT', 'RVNUSDT', 'HBARUSDT', 'STXUSDT', 'BCHUSDT', 'FTTUSDT', 'BNTUSDT', 'SOLUSDT', 'LRCUSDT', 'COMPUSDT', 'SCUSDT', 'ZENUSDT', 'SNXUSDT', 'DGBUSDT', 'MKRUSDT', 'DAIUSDT', 'DCRUSDT', 'MANAUSDT', 'YFIUSDT', 'JSTUSDT', 'SRMUSDT', 'CRVUSDT', 'SANDUSDT', 'DOTUSDT', 'LUNAUSDT', 'PAXGUSDT', 'SUSHIUSDT', 'KSMUSDT', 'EGLDUSDT', 'UMAUSDT', 'BELUSDT', 'UNIUSDT', 'SUNUSDT', 'AVAXUSDT', 'HNTUSDT', 'AAVEUSDT', 'NEARUSDT', 'FILUSDT', 'INJUSDT', 'AXSUSDT', 'ROSEUSDT', 'AVAUSDT', 'XEMUSDT', 'GRTUSDT', 'JUVUSDT', 'PSGUSDT', '1INCHUSDT', 'CELOUSDT', 'TWTUSDT', 'CAKEUSDT', 'ACMUSDT', 'PERPUSDT', 'BTGUSDT', 'BARUSDT', 'SLPUSDT', 'SHIBUSDT', 'ICPUSDT', 'ARUSDT', 'MASKUSDT', 'KLAYUSDT', 'C98USDT', 'QNTUSDT', 'FLOWUSDT', 'WAXPUSDT', 'TRIBEUSDT', 'XECUSDT', 'DYDXUSDT', 'GALAUSDT', 'FIDAUSDT', 'AGLDUSDT', 'MOVRUSDT', 'CITYUSDT', 'ENSUSDT', 'JASMYUSDT', 'RNDRUSDT', 'BICOUSDT', 'FXSUSDT', 'PEOPLEUSDT', 'SPELLUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'ACAUSDT', 'WOOUSDT', 'TUSDT', 'GMTUSDT', 'KDAUSDT', 'APEUSDT', 'NEXOUSDT', 'GALUSDT', 'LDOUSDT', 'OPUSDT', 'STGUSDT', 'LUNCUSDT', 'GMXUSDT', 'APTUSDT', 'HFTUSDT', 'HOOKUSDT', 'MAGICUSDT', 'RPLUSDT', 'AGIXUSDT', 'GNSUSDT', 'SSVUSDT', 'USTCUSDT', 'IDUSDT', 'ARBUSDT', 'RDNTUSDT', 'WBTCUSDT', 'SUIUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'PENDLEUSDT', 'ARKMUSDT', 'WLDUSDT']
    # bag ticker 'RUNEUSDT', 'MINAUSDT'
    ResponseMessage = ''
    BinanceMessage = '<b>BINANCE TO BYBIT</b>\n'
    ByBitMessage = '<b>BYBIT TO BINANCE</b>\n'
    deposit = 3400
    countBinance = 1
    countByBit = 1
    for ticker in tickBinance:
        symb = ticker['symbol']
        if symb in tickers:
            tickerByBitUSDT = session.get_tickers(
                category = "spot",
                symbol = symb,
            )
            tmpByBit = tickerByBitUSDT['result']['list'][0]

            # print('Binance to ByBit', symb, ticker['bidPrice'], tmpByBit['ask1Price'])
            # print('ByBit to Binance', symb, tmpByBit['bid1Price'], ticker['askPrice'])


            BinancePriceToBuy = float(ticker['bidPrice'])
            ByBitPriceToBuy = float(tmpByBit['bid1Price'])

            BinancePriceToSell = float(ticker['askPrice'])
            ByBitPriceToSell = float(tmpByBit['ask1Price'])
            try:
                #BinanceToByBit = (deposit/float(BinancePriceToBuy))*float(ByBitPriceToSell) - deposit
                spreadBinanceToByBit = float('{:.3f}'.format((float(ByBitPriceToSell)-float(BinancePriceToBuy))*100/float(BinancePriceToBuy)))
                #ByBitToBinance = (deposit/float(ByBitPriceToBuy))*float(BinancePriceToSell) - deposit
                spreadByBitToBinance = float('{:.3f}'.format((float(BinancePriceToSell)-float(ByBitPriceToBuy))*100/float(ByBitPriceToBuy)))
            except ZeroDivisionError:
                continue
            # if BinanceToByBit > 10.0 and float(ticker['bidQty'])*BinancePriceToBuy > 1000 and float(ticker['bidPrice']) > 0.1:
            #     ResponseMessage += f'<b>{count}. Buy {symb} on Binance and sell it on ByBit</b>\n\tPrice to buy on Binance = {BinancePriceToBuy}, price to sell on ByBit = {ByBitPriceToSell}\n\tDeposit = {deposit}$, spread = {BinanceToByBit}$, spread = {BinanceToByBit2}%'
            #     ResponseMessage += '\n'
            #     count+=1
            # if ByBitToBinance > 10.0 and float(tmpByBit['bid1Size'])*ByBitPriceToBuy > 1000 and float(tmpByBit['bid1Price']) > 0.1:
            #     ResponseMessage += f'<b>{count}. Buy {symb} on ByBit and sell it on Binance</b>\n\tPrice to buy on ByBit = {ByBitPriceToBuy}, price to sell on Binance = {BinancePriceToSell}\n\tDeposit = {deposit}$, spread = {ByBitToBinance}$, spread = {ByBitToBinance2}%'
            #     ResponseMessage += '\n'
            #     count+=1 float('{:.3f}'.format(x))
            turnover24hBinance = float('{:.3f}'.format(float(ticker['quoteVolume'])))
            turnover24hByBit = float('{:.3f}'.format(float(tmpByBit['turnover24h'])))
            if spreadBinanceToByBit > 0.4 and float(ticker['bidQty'])*BinancePriceToBuy > 1000 and BinancePriceToBuy > 0.1:
                BinanceMessage += f'<b>{countBinance}. Buy {symb} on Binance and sell it on ByBit</b>\n\tPrice to buy on Binance = {BinancePriceToBuy}, price to sell on ByBit = {ByBitPriceToSell}\n\tSpread = {spreadBinanceToByBit}%\n\tTurnover 24h on Binance = {turnover24hBinance}$'
                BinanceMessage += '\n'
                countBinance+=1
            if spreadByBitToBinance > 0.4 and float(tmpByBit['bid1Size'])*ByBitPriceToBuy > 1000 and ByBitPriceToBuy > 0.1:
                ByBitMessage += f'<b>{countByBit}. Buy {symb} on ByBit and sell it on Binance</b>\n\tPrice to buy on ByBit = {ByBitPriceToBuy}, price to sell on Binance = {BinancePriceToSell}\n\tSpread = {spreadByBitToBinance}%\n\tTurnover 24h on ByBit = {turnover24hByBit}$'
                ByBitMessage += '\n'
                countByBit+=1
    ResponseMessage += BinanceMessage + '\n' + ByBitMessage + '\n'
    return ResponseMessage
while True:
    Response = BinByBit()
    Response += f'<b>Chain relevant to {time.ctime()}</b>'
    with open('Links.txt', 'w') as links:
        links.write(Response)
