import asyncio
import json
import random
import traceback
from asyncio import sleep
from typing import Optional
from math import floor
from tenacity import stop_after_attempt, retry, wait_random, retry_if_not_exception_type, retry_if_exception_type

from backpack import Backpack
from better_proxy import Proxy

from inputs.config import DEPTH
from .exceptions import TradeException, FokOrderException
from .utils import logger


def to_fixed(n: str | float, d: int = 0) -> str:
    d = int('1' + ('0' * d))
    result = str(floor(float(n) * d) / d)
    if result.endswith(".0"):
        result = result[:-2]
    return result


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
        "WIF": {
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
        self.amount_usd = 0

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
        await self.custom_delay(delays=self.trade_delay)
        await self.buy(pair)

        await self.custom_delay(delays=self.trade_delay)
        await self.sell(pair)

        await self.custom_delay(self.deal_delay)

        if self.needed_volume and self.current_volume > self.needed_volume:
            return True

    @retry(stop=stop_after_attempt(10), wait=wait_random(5, 7), reraise=True,
           retry=retry_if_exception_type(FokOrderException))
    async def buy(self, symbol: str):
        side = 'buy'
        token = symbol.split('_')[1]
        price, balance = await self.get_trade_info(symbol, side, token)

        amount = str(float(balance) / float(price))

        await self.trade(symbol, amount, side, price)

    @retry(stop=stop_after_attempt(10), wait=wait_random(5, 7), reraise=True,
           retry=retry_if_exception_type(FokOrderException))
    async def sell(self, symbol: str):
        side = 'sell'
        token = symbol.split('_')[0]
        price, amount = await self.get_trade_info(symbol, side, token)

        return await self.trade(symbol, amount, side, price)

    @retry(stop=stop_after_attempt(7), wait=wait_random(2, 5), before_sleep=lambda e: logger.info(e),
           retry=retry_if_not_exception_type(TradeException), reraise=True)
    async def get_trade_info(self, symbol: str, side: str, token: str):
        logger.info(f"Trying to trade {side} {symbol}...")
        price = await self.get_market_price(symbol, side, DEPTH)
        # logger.info(f"Market price: {price} | Side: {side} | Token: {token}")
        response = await self.get_balances()
        # logger.info(f"Balances: {await response.text()} | Side: {side} | Token: {token}")
        balances = json.loads(await response.read())

        amount = balances[token]['available']

        amount_usd = float(amount) * float(price) if side != 'buy' else float(amount)

        if self.trade_amount[0] < 5 and self.trade_amount[1] > 0:
            self.trade_amount[0] = 5
            self.trade_amount[1] = 5

        if side == "buy":
            if self.min_balance_to_left > 0 and self.min_balance_to_left >= amount_usd:
                raise TradeException(
                    f"Stopped by min balance parameter {self.min_balance_to_left}. Current balance ~ {amount_usd}$")

        if self.trade_amount[1] > 0:
            if self.trade_amount[0] * 0.8 > amount_usd:
                raise TradeException(
                    f"Not enough funds to trade. Trade Stopped. Current balance ~ {amount_usd:.2f}$")
            elif self.trade_amount[1] > amount_usd:
                self.trade_amount[1] = amount_usd

            if side == "buy":
                amount_usd = random.uniform(*self.trade_amount)
                amount = amount_usd
            elif side == "sell":
                amount = amount_usd / float(price)

        self.amount_usd = amount_usd

        return price, amount

    @retry(stop=stop_after_attempt(9), wait=wait_random(2, 5), reraise=True,
           retry=retry_if_not_exception_type((TradeException, FokOrderException)))
    async def trade(self, symbol: str, amount: str, side: str, price: str):
        decimal = BackpackTrade.ASSETS_INFO.get(symbol.split('_')[0].upper(), {}).get('decimal', 0)
        fixed_amount = to_fixed(float(amount), decimal)
        # print(amount, fixed_amount)
        if fixed_amount == "0":
            raise TradeException("Not enough funds to trade!")

        logger.bind(end="").debug(f"Side: {side} | Price: {price} | Amount: {fixed_amount}")

        response = await self.execute_order(symbol, side, order_type="limit", quantity=fixed_amount, price=price,
                                            time_in_force="FOK")

        resp_text = await response.text()

        logger.opt(raw=True).debug(f" | Response: {resp_text} \n")

        if resp_text == "Fill or kill order would not complete fill immediately":
            logger.info(f"Order can't be executed. Re-creating order")
            raise FokOrderException(resp_text)

        if response.status != 200:
            logger.info(f"Failed to trade! Check logs for more info. Response: {await response.text()}")

        result = json.loads(await response.read())

        if result.get("createdAt"):
            self.current_volume += self.amount_usd

            logger.info(f"{side.capitalize()} {fixed_amount} {symbol}. "
                        f"Traded volume: {self.current_volume:.2f}$")

            return True

        raise TradeException(f"Failed to trade! Check logs for more info. Response: {await response.text()}")

    @retry(stop=stop_after_attempt(7), wait=wait_random(2, 5), reraise=True)
    async def get_market_price(self, symbol: str, side: str, depth: int = 1):
        response = await self.get_order_book_depth(symbol)
        orderbook = json.loads(await response.read())

        return orderbook['asks'][depth][0] if side == 'buy' else orderbook['bids'][-depth][0]

    @staticmethod
    async def custom_delay(delays: tuple):
        if delays[1] > 0:
            sleep_time = random.uniform(*delays)
            logger.info(f"Sleep for {sleep_time:.2f} seconds")
            await sleep(sleep_time)
