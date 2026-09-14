import datetime
import json
from typing import Any

import requests
from cryptography.fernet import Fernet

from .exceptions import AstrumAPIError
from .status_hints import STATUS_HINTS
from .version_check import check_for_updates as _check_for_updates


class AstrumClient:
    """Клиент для Astrum API (создание и статус сделок пейин/пейаут).

    api_key, private_key и base_url выдаются администрацией площадки при
    регистрации мерчанта.
    """

    def __init__(
        self,
        api_key: str,
        private_key: str,
        base_url: str,
        timeout: float = 15.0,
        check_for_updates: bool = True,
    ):
        self._api_key = api_key
        self._fernet = Fernet(private_key)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        if check_for_updates:
            _check_for_updates()

    def _encrypt(self, data: dict[str, Any]) -> str:
        return self._fernet.encrypt(json.dumps(data).encode("utf-8")).decode("utf-8")

    def _headers(self) -> dict[str, str]:
        return {
            "accept": "application/json",
            "content-type": "application/json;charset=utf-8",
            "Authorization": self._api_key,
        }

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = requests.request(
            method,
            f"{self._base_url}{path}",
            headers=self._headers(),
            timeout=self._timeout,
            **kwargs,
        )
        if not response.ok:
            # 401/403/404/500/502/503/504 не всегда возвращают наш JSON с полем
            # msg (404 — стандартный FastAPI {"detail": "Not Found"}, 502/503/504
            # часто отдаёт proxy/nginx, а не приложение, и может вернуть HTML).
            # Поэтому для известных статусов используем готовую подсказку,
            # а исходное тело всегда кладём в error.response для отладки.
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
            hint = STATUS_HINTS.get(response.status_code)
            if hint:
                message = hint
            elif isinstance(body, dict) and body.get("msg"):
                message = body["msg"]
            else:
                message = f"Ошибка запроса (HTTP {response.status_code})"
            raise AstrumAPIError(message, response.status_code, body)

        try:
            body = response.json()
        except ValueError as e:
            raise AstrumAPIError(f"Невалидный JSON в ответе: {response.text}", response.status_code) from e
        # Сервер отвечает 200 OK даже на бизнес-отказы (нет реквизита, превышен
        # лимит и т.п.) — success:false в теле. Кидаем исключение и здесь, чтобы
        # отказ не проскочил незамеченным без явной проверки result["success"].
        if isinstance(body, dict) and body.get("success") is False:
            raise AstrumAPIError(body.get("msg") or "Заявка отклонена", response.status_code, body)
        return body

    # ---- Пейин ----

    def _payin_payload(
        self,
        foreign_id: str,
        amount: float,
        method_type_id: int,
        method_name_id: int | None,
        client_id: str | None,
        initials: str | None,
    ) -> dict[str, Any]:
        return {
            "foreignId": foreign_id,
            "amount": amount,
            "methodTypeId": method_type_id,
            "methodNameId": method_name_id,
            "clientId": client_id,
            "initials": initials,
        }

    def create_payin(
        self,
        foreign_id: str,
        amount: float,
        method_type_id: int,
        method_name_id: int | None = None,
        client_id: str | None = None,
        initials: str | None = None,
    ) -> dict[str, Any]:
        """Создать сделку (Пейин). Тело шифруется Fernet перед отправкой."""
        payload = self._payin_payload(foreign_id, amount, method_type_id, method_name_id, client_id, initials)
        return self._request(
            "POST", "/source/deal",
            json={"encrypted_application": self._encrypt(payload)},
        )

    def create_payin_vnd_qr(
        self,
        foreign_id: str,
        amount: float,
        method_type_id: int,
        method_name_id: int | None = None,
        client_id: str | None = None,
        initials: str | None = None,
    ) -> dict[str, Any]:
        """Создать сделку (Пейин, вьетнамский QR)."""
        payload = self._payin_payload(foreign_id, amount, method_type_id, method_name_id, client_id, initials)
        return self._request(
            "POST", "/source/deal/vnd-qr",
            json={"encrypted_application": self._encrypt(payload)},
        )

    def create_payin_qr(
        self,
        foreign_id: str,
        amount: float,
        method_type_id: int,
        method_name_id: int | None = None,
        client_id: str | None = None,
        initials: str | None = None,
    ) -> dict[str, Any]:
        """Создать сделку (Пейин, QR)."""
        payload = self._payin_payload(foreign_id, amount, method_type_id, method_name_id, client_id, initials)
        return self._request(
            "POST", "/source/deal/qr",
            json={"encrypted_application": self._encrypt(payload)},
        )

    def confirm_payin(self, foreign_id: str, receipt_url: str | None = None, initials: str | None = None) -> dict[str, Any]:
        """Подтвердить оплату сделки (Пейин). Тело НЕ шифруется."""
        body = {"foreignId": foreign_id, "receiptUrl": receipt_url, "initials": initials}
        return self._request("PUT", "/source/deal", json=body)

    def cancel_payin(self, foreign_id: str) -> dict[str, Any]:
        """Отменить сделку (Пейин)."""
        return self._request("PUT", "/source/deal/cancel", json={"foreignId": foreign_id})

    def get_payin_info(self, foreign_id: str) -> dict[str, Any]:
        """Получить информацию о сделке (Пейин)."""
        return self._request("GET", "/source/deal/info", params={"foreignId": foreign_id})

    def get_payin_deals(
        self,
        inner_id: str | None = None,
        foreign_id: str | None = None,
        requisite: str | None = None,
        show_pending: bool = True,
        show_success: bool = True,
        show_cancelled: bool = True,
        date_from: datetime.datetime | None = None,
        date_to: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Получить ссылку на CSV-выгрузку сделок (Пейин) с фильтрами."""
        # bool отправляем как "true"/"false" явно — requests сериализует python-bool
        # как "True"/"False", а сервер ожидает lowercase.
        params: dict[str, Any] = {
            "showPending": str(show_pending).lower(),
            "showSuccess": str(show_success).lower(),
            "showCancelled": str(show_cancelled).lower(),
        }
        if inner_id is not None:
            params["innerId"] = inner_id
        if foreign_id is not None:
            params["foreignId"] = foreign_id
        if requisite is not None:
            params["requisite"] = requisite
        if date_from is not None:
            params["dateFrom"] = date_from.isoformat()
        if date_to is not None:
            params["dateTo"] = date_to.isoformat()
        return self._request("GET", "/source/deal/api", params=params)

    # ---- Финансы и справочники ----

    def get_balance(self) -> dict[str, Any]:
        """Получить баланс."""
        return self._request("GET", "/source/balance/api")

    def get_balance_currency(self) -> dict[str, Any]:
        """Получить баланс и валюту баланса."""
        return self._request("GET", "/source/balance/api/currency")

    def get_movements(self, date_from: datetime.datetime | None = None, date_to: datetime.datetime | None = None) -> dict[str, Any]:
        """Получить ссылку на CSV-выгрузку ДДС."""
        params: dict[str, Any] = {}
        if date_from is not None:
            params["dateFrom"] = date_from.isoformat()
        if date_to is not None:
            params["dateTo"] = date_to.isoformat()
        return self._request("GET", "/source/movements/api", params=params)

    def get_methods(self) -> dict[str, Any]:
        """Получить список всех типов и методов оплаты."""
        return self._request("GET", "/source/methods")

    def get_source_info(self) -> dict[str, Any]:
        """Получить информацию об источнике (мерчанте)."""
        return self._request("GET", "/source/info/api")

    def get_course(self) -> dict[str, Any]:
        """Получить курс."""
        return self._request("GET", "/source/course")

    # ---- Пейаут (v1, snake_case) ----

    def create_payout_v1(
        self,
        foreign_id: str,
        amount: float,
        requisite: str,
        method_type_id: int,
        client_initials: str,
        method_name_id: int | None = 0,
        express: bool = False,
    ) -> dict[str, Any]:
        """Создать сделку (Пейаут, старая версия с snake_case-полями).

        Для новых интеграций используйте create_payout (v2, camelCase).
        """
        payload = {
            "foreign_id": foreign_id,
            "amount": amount,
            "requisite": requisite,
            "method_type_id": method_type_id,
            "method_name_id": method_name_id,
            "client_initials": client_initials,
            "express": express,
        }
        return self._request(
            "POST", "/source/applications/new",
            json={"encrypted_application": self._encrypt(payload)},
        )

    # ---- Пейаут (v2, camelCase) ----

    def create_payout(
        self,
        foreign_id: str,
        amount: float,
        requisite: str,
        method_type_id: int,
        client_initials: str,
        method_name_id: int | None = 0,
        express: bool = False,
    ) -> dict[str, Any]:
        """Создать сделку (Пейаут). Тело шифруется Fernet перед отправкой."""
        payload = {
            "foreignId": foreign_id,
            "amount": amount,
            "requisite": requisite,
            "methodTypeId": method_type_id,
            "methodNameId": method_name_id,
            "clientInitials": client_initials,
            "express": express,
        }
        return self._request(
            "POST", "/source/v2/applications/new",
            json={"encrypted_application": self._encrypt(payload)},
        )

    def get_payout_info(self, foreign_id: str) -> dict[str, Any]:
        """Получить информацию о сделке (Пейаут)."""
        return self._request("GET", "/source/v2/applications/info", params={"foreignId": foreign_id})
