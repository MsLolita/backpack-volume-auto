import random
import traceback
from asyncio import sleep
from typing import Optional
from math import floor

from backpack import Backpack

from better_proxy import Proxy
from tenacity import stop_after_attempt, retry, wait_random, retry_if_not_exception_type

from .exceptions import TradeException
from .utils import logger


def to_fixed(n: str | float, d: int = 0) -> str:
    d = int('1' + ('0' * d))
    return str(floor(float(n) * d) / d).replace(".0", "")


class BackpackTrade(Backpack):
    ASSETS_INFO = {
        "SOL": {
            'decimal': 2
        },
        "USDC": {
            'decimal': 2
        },
        "PYTH": {
            'decimal': 1
        },
        "JTO": {
            'decimal': 1
        },
        "HNT": {
            'decimal': 1
        },
        "MOBILE": {
            'decimal': 0
        },
        'BONK': {
            'decimal': 0,
        },
        "WIFI": {
            'decimal': 0
        },
        "USDT": {
            'decimal': 0
        },
        "JUP": {
            'decimal': 2
        }
    }

    def __init__(self, api_key: str, api_secret: str, proxy: Optional[str] = None, *args):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            proxy=proxy and Proxy.from_str(proxy.strip()).as_url
        )

        self.trade_delay, self.deal_delay, self.needed_volume, self.min_balance_to_left, self.trade_amount = args

        self.current_volume: float = 0

    async def start_trading(self, pairs: list[str]):
        try:
            while True:
                pair = random.choice(pairs)
                if await self.trade_worker(pair):
                    break
        except TradeException as e:
            logger.info(e)
        except Exception as e:
            logger.error(f"{e} / Check logs in logs/out.log")
            logger.debug(f"{e} {traceback.format_exc()}")

        logger.info(f"Finished! Traded volume ~ {self.current_volume:.2f}$")

    async def trade_worker(self, pair: str):
        await self.buy(pair)
        await self.sell(pair)
        await self.custom_delay(self.deal_delay)

        if self.needed_volume and self.current_volume > self.needed_volume:
            return True

    async def buy(self, symbol: str):
        side = 'buy'
        token = symbol.split('_')[1]
        price, balance = await self.get_trade_info(symbol, side, token)

        amount = str(float(balance) / float(price))

        await self.trade(symbol, amount, side, price)

    async def sell(self, symbol: str):
        side = 'sell'
        token = symbol.split('_')[0]
        price, amount = await self.get_trade_info(symbol, side, token)

        return await self.trade(symbol, amount, side, price)

    async def get_trade_info(self, symbol: str, side: str, token: str):
        price = await self.get_market_price(symbol, side, 3)
        response = await self.get_balances()
        balances = await response.json()
        amount = balances[token]['available']
        amount_usd = float(amount) * float(price) if side != 'buy' else float(amount)

        if self.trade_amount[1] > 0:
            if self.trade_amount[0] > float(amount):
                raise TradeException(f"Not enough funds to trade. Trade Amount Stopped. Current balance ~ {float(amount):.2f}$")
            elif self.trade_amount[1] > amount_usd:
                self.trade_amount[1] = amount_usd

            amount_usd = random.uniform(*self.trade_amount)

        self.current_volume += amount_usd

        if self.min_balance_to_left > 0 and self.min_balance_to_left >= amount_usd:
            raise TradeException(f"Not enough funds to trade. Min Balance Stopped. Current balance ~ {amount_usd}$")

        return price, amount

    @retry(stop=stop_after_attempt(3), wait=wait_random(2, 5), reraise=True,
           retry=retry_if_not_exception_type(TradeException))
    async def trade(self, symbol: str, amount: str, side: str, price: str):
        decimal = BackpackTrade.ASSETS_INFO.get(symbol.split('_')[0].upper(), {}).get('decimal', 0)
        fixed_amount = to_fixed(float(amount), decimal)

        if fixed_amount == "0":
            raise TradeException("Not enough funds to trade!")

        logger.bind(end="").debug(f"Side: {side} | Price: {price} | Amount: {fixed_amount}")

        response = await self.execute_order(symbol, side, order_type="limit", quantity=fixed_amount, price=price)

        logger.opt(raw=True).debug(f" | Response: {await response.text()} \n")

        if response.status != 200:
            logger.info(f"Failed to trade! Check logs for more info. Response: {await response.text()}")

        result = await response.json()

        if result.get("createdAt"):
            logger.info(f"{side.capitalize()} {fixed_amount} {symbol}. "
                        f"Traded volume: {self.current_volume:.2f}$")

            await self.custom_delay(delays=self.trade_delay)

            return True

        raise TradeException(f"Failed to trade! Check logs for more info. Response: {await response.text()}")

    async def get_market_price(self, symbol: str, side: str, depth: int = 1):
        response = await self.get_order_book_depth(symbol)
        orderbook = await response.json()

        return orderbook['asks'][depth][0] if side == 'buy' else orderbook['bids'][-depth][0]

    @staticmethod
    async def custom_delay(delays: tuple):
        if delays[1] > 0:
            sleep_time = random.uniform(*delays)
            logger.info(f"Sleep for {sleep_time:.2f} seconds")
            await sleep(sleep_time)
