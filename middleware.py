import logging

from aiohttp.web_exceptions import HTTPNotFound, HTTPFound
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request


logger = logging.getLogger('user_info')


@middleware
async def error_middleware(request: Request, handler):
    try:
        return await handler(request)

    except HTTPNotFound:
        # Автоматический редирект на документацию
        raise HTTPFound('/')

    except Exception as err:
        # Все остальные исключения не могут быть отображены клиенту в виде
        # HTTP ответа и могут случайно раскрыть внутреннюю информацию.
        log.exception(err)
