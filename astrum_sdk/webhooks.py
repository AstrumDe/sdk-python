import datetime
import json
from typing import Any

_DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def _parse_dt(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return value


def _load(raw_body: str | bytes | dict) -> dict[str, Any]:
    if isinstance(raw_body, dict):
        return raw_body
    return json.loads(raw_body)


def parse_payin_webhook(raw_body: str | bytes | dict) -> dict[str, Any]:
    """Разобрать тело колбека по сделке Пейин (POST на callbackUrl мерчанта).

    Колбек НЕ подписывается и не шифруется — площадка отправляет обычный
    JSON. Функция парсит даты (createdAt/closedAt/updatedAt) в datetime.
    """
    data = _load(raw_body)
    for field in ("createdAt", "closedAt", "updatedAt"):
        if field in data:
            data[field] = _parse_dt(data[field])
    return data


def parse_payout_webhook(raw_body: str | bytes | dict) -> dict[str, Any]:
    """Разобрать тело колбека по сделке Пейаут (POST на callbackUrlPayout мерчанта).

    Поля приходят в snake_case (foreign_id, inner_id, created_at, closed_at, ...).
    """
    data = _load(raw_body)
    for field in ("created_at", "closed_at"):
        if field in data:
            data[field] = _parse_dt(data[field])
    return data
