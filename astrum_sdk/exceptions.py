class AstrumAPIError(Exception):
    """Ошибка на стороне Astrum API (HTTP-код за пределами 2xx, либо success=False в ответе).

    response — распарсенное тело ответа (dict), либо сырой текст, если сервер
    вернул не JSON (типично для 404/502/503/504 от proxy, а не от приложения).
    """

    def __init__(self, message: str, status_code: int | None = None, response: dict | str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
