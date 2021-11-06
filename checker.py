import os
import logging
from typing import Dict
from dataclasses import dataclass

import asyncio
import aiohttp

from abc_checker import CheckerABC
from utils import fetch


logger = logging.getLogger('user_info')


@dataclass
class Amount:
    currencies: Dict[str, float]
    exchange_rates: Dict[str, float]
    sum: Dict[str, float]


class Checker(CheckerABC):
    def __init__(self, currencies: Dict[str, float], period: int):
        self.period = period
        self.currencies = currencies
        self.exchange_rates = None

        currencies_names = list(currencies.keys())
        if 'eur' in currencies:
            # Должен находится вначале, для правильного подсчета
            currencies_names.remove('eur')
            currencies_names.insert(0, 'eur')
        self._prev_amount = Amount(
            currencies={k: 0 for k in currencies},
            exchange_rates={
                # Получаем элементы вида: { 'EURRUB': 0, ... }
                currencies_names[i] + currencies_names[j]: 0
                for i in range(len(currencies_names))
                for j in range(i + 1, len(currencies_names))
            },
            sum={k: 0 for k in currencies},
        )

    async def get_exchange_rate(self):
        url = 'http://api.exchangeratesapi.io/v1/latest'
        params = {
            'access_key': os.getenv('ACCESS_KEY'),
            'base': 'EUR',
            'symbols': ','.join(filter(lambda x: x != 'EUR', (c.upper() for c in self.currencies))),
        }
        async with aiohttp.ClientSession() as session:
            while True:
                data = await fetch(session, url, params=params)

                if data is not None:
                    add_this_currency_to_result = False

                    if 'eur' in self.currencies:
                        # Мы можем получать данные только через EUR, поэтому нам
                        # приходится использовать его для формирования других курсов валют
                        # Но если пользователь не передал EUR в качестве параметра
                        # скрипта, то нам не нужны дынные эти данные
                        add_this_currency_to_result = True

                    self.exchange_rates = await self.generate_exchange_rates(
                        currency='eur',
                        its_exchange_rate=data['rates'],
                        add_this_currency_to_result=add_this_currency_to_result
                    )
                    logger.info('Новые данные получены')
                await asyncio.sleep(self.period * 60)

    @staticmethod
    async def generate_exchange_rates(currency: str, its_exchange_rate: dict, add_this_currency_to_result: bool):
        eur_exchange_rate = [
            (currency + name.lower(), 1 / value)
            for name, value in its_exchange_rate.items()
        ]

        result = {}
        for i in range(len(eur_exchange_rate)):
            name1, value1 = eur_exchange_rate[i]
            name1 = name1[3:]

            for j in range(i + 1, len(eur_exchange_rate)):
                name2, value2 = eur_exchange_rate[j]
                name2 = name2[3:]

                name = name1 + name2
                value = value2 / value1

                result[name] = value

        if add_this_currency_to_result:
            result, temp = dict(eur_exchange_rate), result
            result.update(temp)
        return result

    async def generate_sum(self):
        result = self.currencies.copy()
        exchange_rates = list(self.exchange_rates.items())
        for i in range(len(exchange_rates)):
            name, value = exchange_rates[i]
            name1, name2 = name[:3], name[3:]

            result[name1] += (value * self.currencies[name2])
            result[name2] += ((1 / value) * self.currencies[name1])
        return result

    async def amount_diff_checker(self):
        while True:
            await asyncio.sleep(1)  # For debug
            # await asyncio.sleep(1 * 60)

            if (diff := await self.get_amount_diff()) is not None:
                logger.info(''.join(diff))

    async def get_amount_diff(self):
        result = [f'\n{"Amount":^54s}\n', f'{"="*54}\n']
        there_is_diff = False

        if self.exchange_rates is None:
            # Если данные о курсах валют еще не получены
            return None

        amount_sum = await self.generate_sum()
        # Сравниваем предыдущий предстоящий "вывод"
        categories = (
            (self._prev_amount.currencies, self.currencies),
            (self._prev_amount.exchange_rates, self.exchange_rates),
            (self._prev_amount.sum, amount_sum),
        )
        for category in categories:
            prev, curr = category

            for key in curr.keys():
                value1 = prev[key]
                value2 = curr[key]

                if (diff := value1 - value2) == 0:
                    res = f'{key:6s}:\t{str(value2):20s}\n'
                elif diff < 0:
                    res = f'{key:6s}:\t{str(value2):20s}\t+{str(value2 - value1):20s}\n'
                    there_is_diff = True
                else:
                    res = f'{key:6s}:\t{str(value2):20s}\t-{str(value1 - value2):20s}\n'
                    there_is_diff = True
                result.append(res)
            result.append('\n')
        if there_is_diff:
            self._prev_amount.currencies = self.currencies.copy()
            self._prev_amount.exchange_rates = self.exchange_rates.copy()
            self._prev_amount.sum = amount_sum
            return result
        return None

    def set_tasks(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.get_exchange_rate())
        loop.create_task(self.amount_diff_checker())
