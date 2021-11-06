import os
import sys
import json
import logging
from http import HTTPStatus

import aiohttp

logger = logging.getLogger('user_info')


async def fetch(session, url, params):
    async with session.get(url, params=params) as resp:
        if resp.status == HTTPStatus.OK:
            data = await resp.json()
            if data['success']:
                return data
            else:
                code, msg = data['error']
                logger.error('Не удалось получить данные: %s, %s' % (code, msg))
        else:
            logger.critical('API не отвечает status_code=%d' % resp.status)
    return None


async def get_symbols():
    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path, 'currencies.txt')
    if not (os.path.exists(path) and os.path.isfile(path)):
        logger.warning('Файла с валютами не существует %s' % path)

        async with aiohttp.ClientSession() as session:
            url = 'http://api.exchangeratesapi.io/v1/symbols'
            params = {'access_key': os.getenv('ACCESS_KEY')}
            data = await fetch(session, url, params=params)

        with open(path, mode='w') as f:
            if data is not None:
                f.write(json.dumps(data['symbols']))
                logger.info('Файл с валютами создан')
            else:
                logger.critical('Файл с валютами не создан')
                sys.exit()

    with open(path, mode='r') as f:
        # Получаем наименования всех валют
        return json.loads(f.read())
