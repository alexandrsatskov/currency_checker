import os
import sys
import asyncio
import logging
import argparse


from aiohttp import web
from aiomisc.log import basic_config
from aiohttp_apispec import docs, request_schema, validation_middleware, setup_aiohttp_apispec
from marshmallow import Schema
from marshmallow.fields import Float
from dotenv import load_dotenv


from api import CheckerAPI
from middleware import error_middleware
from utils import get_symbols

logger = logging.getLogger('user_info')

parser = argparse.ArgumentParser()
parser.add_argument('--period', required=True, type=float)
parser.add_argument('--debug', choices={'0', 'false', 'False', 'n', 'N', '1', 'true', 'True', 'y', 'Y'}, default='0')


if __name__ == '__main__':

    load_dotenv()

    parsed, unknown = parser.parse_known_args()
    period, debug = parsed.period, parsed.debug
    if debug.lower() in {'1', 'true', 'y'}:
        logger.disabled = True
    else:
        logging.getLogger('aiohttp.access').disabled = True

        # Рандомно вылетает ошибка, не знаю в чем проблема
        # Гугл особо ничего не дал, поэтому просто отключил лог
        # 2021-11-05 16:12:53 [T:MainThread] ERROR:aiohttp.server: Error handling request
        #   File "aiohttp\_http_parser.pyx", line 546, in aiohttp._http_parser.HttpParser.feed_data
        # aiohttp.http_exceptions.BadStatusLine: 400, message="Bad status line 'invalid HTTP method'"
        logging.getLogger('aiohttp.server').disabled = True

    # Чтобы логи не блокировали основной поток (и event loop) во время операций
    # записи в stderr или файл - логи можно буфферизовать и обрабатывать в
    # отдельном потоке (aiomisc.basic_config настроит буфферизацию автоматически)
    basic_config(level=logging.INFO, log_format='color', buffered=True)

    if not os.getenv('ACCESS_KEY'):
        logger.critical('Не передана переменная окружения "ACCESS_KEY"')
        sys.exit()

    SYMBOLS = asyncio.get_event_loop().run_until_complete(get_symbols())

    # Создаем новый парсер для unknown аргументов
    parser = argparse.ArgumentParser()
    for arg in unknown:
        # Добавляем новые аргументы командной строки
        if arg.startswith("--"):
            parser.add_argument(arg, type=float)

    # Получаем новые аргументы - валюты
    args = vars(parser.parse_args(unknown))
    currencies = {}
    invalid_currencies = []
    for currency, value in args.items():
        if currency.upper() not in SYMBOLS:
            invalid_currencies.append(currency)
        else:
            currencies[currency.lower()] = value

    if invalid_currencies:
        logger.warning('Invalid currencies=%s' % ",".join(invalid_currencies).lstrip(","))

    if len(currencies) <= 1:
        if len(currencies) == 1:
            logger.critical('Требуется минимум две валюты')
        if len(currencies) == 0:
            logger.critical('Не указана ни одна валюта')
        logger.info('Примеры параметров: --usd 3.23 --btc 0.03')
        logger.info('Приложение завершено')
        sys.exit()

    # Динамически генерируем marshmallow схему для валидации в API
    CurrenciesSchema = type('CurrenciesSchema', (Schema,), {k: Float() for k in currencies.keys()})

    # Вешаем декораторы здесь, потому что не нашел куда правильнее будет вставить динамично создающуюся схему
    CheckerAPI.get_currency = docs(summary='Количество валюты на текущий момент')(CheckerAPI.get_currency)
    CheckerAPI.get_amount = docs(summary='Отчет по всем валютам')(CheckerAPI.get_amount)
    CheckerAPI.post_amount = docs(summary='Переопределить количество валюты')(request_schema(CurrenciesSchema)(CheckerAPI.post_amount))
    CheckerAPI.post_modify = docs(summary='Изменить количество валюты')(request_schema(CurrenciesSchema)(CheckerAPI.post_modify))

    checker = CheckerAPI(currencies, period)
    app = web.Application(middlewares=[validation_middleware, error_middleware])
    app.add_routes([
        web.get(r'/{currency:[a-zA-Z]{3}}/get', checker.get_currency),
        web.get('/amount/get', checker.get_amount),
        web.post('/amount/set', checker.post_amount),
        web.post('/modify', checker.post_modify),
    ])
    checker.set_tasks()

    # Генерация документации
    setup_aiohttp_apispec(app, swagger_path='/')

    logger.info('Старт приложения')
    web.run_app(app)
    logger.info('Приложение завершено')
