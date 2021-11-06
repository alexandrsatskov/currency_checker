from abc import ABC, abstractmethod


class CheckerABC(ABC):

    @abstractmethod
    async def get_exchange_rate(self):
        """
        Раз в N минут получает данные о курсе валюты EUR

        **Вынуждены использовать EUR, из-за реализации бесплатного тарифа API
        """

    @staticmethod
    @abstractmethod
    async def generate_exchange_rates(currency: str, its_exchange_rate: dict, add_this_currency_to_result: bool):
        """
        Формирует данные курсов валют, основываясь на курсе EUR

        Например: 'EUR': {'RUB': 0.12, 'USD': 0.80}

        Получим:
            [('EURRUB', 0.12), ('EURUSD', 0.80), ('RUBUSD', ~70)]
        """

    @abstractmethod
    async def generate_sum(self):
        """Считаем итоговую сумму по всем валютам на основе текущего курса"""

    @abstractmethod
    async def amount_diff_checker(self):
        """
            Раз в минуту проверяет есть ли
            изменения с прошлого вывода,
            если да - делает новый вывод в консоль
        """

    @abstractmethod
    async def get_amount_diff(self):
        """Формирует данные для нового вывода в консоль, если были изменены"""

    @abstractmethod
    def set_tasks(self):
        """
        Создает задачи из корутин:
            1. Брать данные раз в N минут
            2. Вывод в консоль раз в минуту

        И скармливает их event loop'у
        """
