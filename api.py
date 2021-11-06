from aiohttp.web import Request, Response

from checker import Checker


class CheckerAPI(Checker):
    async def get_currency(self, request: Request):
        """API. Отдает текущее количество запрашиваемой валюты"""
        currency = request.match_info['currency']
        if currency in self.currencies:
            return Response(text=f"{currency}: {self.currencies[currency]}", content_type='text/plain')
        return Response(text=f"Валюта {currency=} не найдена!", content_type='text/plain', status=400)

    async def get_amount(self, request: Request):
        """API. Формирует и отдает отчет"""
        if self.exchange_rates is None:
            return Response(text='Данные еще не получены', content_type='text/plain', status=503)

        result = []
        for category in (self.currencies, self.exchange_rates, await self.generate_sum()):
            for k, v in category.items():
                result.append(f'{k}: {v}\n')
            result.append('\n')
        result.pop()
        return Response(text=''.join(result), content_type='text/plain')

    async def post_amount(self, request: Request):
        """API. Устанавливает новое количество валют"""
        for currency, value in request['data'].items():
            if currency in self.currencies:
                self.currencies[currency] = value
        return Response(status=204)

    async def post_modify(self, request: Request):
        """API. Добавляет к текущим количествам валют переданные пользователем значения"""
        for currency, value in request['data'].items():
            if currency in self.currencies:
                self.currencies[currency] += value
        return Response(status=204)
