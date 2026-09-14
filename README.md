# astrum-sdk (Python)

Официальный клиент для Astrum API — создание и статус сделок Пейин/Пейаут,
шифрование заявок (Fernet) и разбор колбеков сделаны за вас.

## Установка

**Использовать SDK в своём проекте** — ставится по прямой ссылке на файл из
[GitHub Releases](https://github.com/AstrumDe/sdk-python/releases) этого
репозитория, отдельный хостинг не нужен:

```bash
pip install "https://github.com/AstrumDe/sdk-python/releases/download/v0.1.0/astrum_sdk-0.1.0-py3-none-any.whl"
```

(ссылку на конкретную версию берёте со страницы релиза).

**Разработка самого SDK** (правите код в этом репозитории):

```bash
git clone https://github.com/AstrumDe/sdk-python.git
cd sdk-python
pip install -e .   # editable install: правки в коде видны сразу, без переустановки
```

## Быстрый старт

```python
from astrum_sdk import AstrumClient, AstrumAPIError

client = AstrumClient(api_key="...", private_key="...", base_url="...")
# все три значения выдаёт площадка при регистрации мерчанта

try:
    deal = client.create_payin(
        foreign_id="order-1",
        amount=70.0,
        method_type_id=46,
        client_id="user-1",
    )
except AstrumAPIError as e:
    print(e, e.status_code, e.response)
```

## Методы и эндпоинты

| Метод SDK | HTTP | Эндпоинт | Описание |
|---|---|---|---|
| `create_payin` | POST | `/source/deal` | Создать сделку (Пейин) |
| `create_payin_vnd_qr` | POST | `/source/deal/vnd-qr` | Создать сделку (Пейин, вьетнамский QR) |
| `create_payin_qr` | POST | `/source/deal/qr` | Создать сделку (Пейин, QR) |
| `confirm_payin` | PUT | `/source/deal` | Подтвердить оплату сделки (Пейин) |
| `cancel_payin` | PUT | `/source/deal/cancel` | Отменить сделку (Пейин) |
| `get_payin_info` | GET | `/source/deal/info` | Статус сделки (Пейин) |
| `get_payin_deals` | GET | `/source/deal/api` | CSV-выгрузка сделок (Пейин) с фильтрами |
| `get_balance` | GET | `/source/balance/api` | Баланс |
| `get_balance_currency` | GET | `/source/balance/api/currency` | Баланс и валюта баланса |
| `get_movements` | GET | `/source/movements/api` | CSV-выгрузка ДДС |
| `get_methods` | GET | `/source/methods` | Список типов и методов оплаты |
| `get_source_info` | GET | `/source/info/api` | Информация об источнике (мерчанте) |
| `get_course` | GET | `/source/course` | Курс |
| `create_payout_v1` | POST | `/source/applications/new` | Создать сделку (Пейаут, старая snake_case-версия) |
| `create_payout` | POST | `/source/v2/applications/new` | Создать сделку (Пейаут, v2 camelCase — рекомендуется) |
| `get_payout_info` | GET | `/source/v2/applications/info` | Статус сделки (Пейаут) |

`create_payin*` и `create_payout*` шифруют тело заявки Fernet-ключом
(`private_key`) перед отправкой — остальные методы отправляют/получают
обычный JSON, аутентификация — заголовком `Authorization: <api_key>`.

## Пример: Пейаут

```python
payout = client.create_payout(
    foreign_id="payout-1",
    amount=10,
    requisite="1111222233334444",
    method_type_id=5,
    client_initials="Test Name",
)
```

## Ошибки

Все ошибки — это один класс `astrum_sdk.AstrumAPIError` (наследует `Exception`,
поля `status_code` и `response`). Кидается в трёх случаях:

1. **HTTP-статус не 2xx.**
2. **`success: false` в теле ответа при HTTP 200** — сервер не различает
   бизнес-отказ (нет реквизита, превышен лимит, неверный ключ и т.п.)
   статус-кодом, поэтому SDK кидает исключение и здесь, чтобы отказ не
   проскочил незамеченным без явной проверки поля.
3. **Ответ не JSON**, когда его ожидали (сломанный/пустой ответ сервера).

Причину смотрите в `str(error)` (уже содержит понятное сообщение) или
`error.response` — весь исходный JSON-ответ сервера (либо сырой текст, если
сервер вернул не JSON, например HTML-страницу ошибки от прокси).

Для типовых HTTP-статусов `str(error)` сразу объясняет причину и что делать
(маппинг — `astrum_sdk.STATUS_HINTS`):

| Код | Значение | Что означает / что делать |
|---|---|---|
| 401 | Unauthorized | API-ключ, вероятно, отключён или неверен — обратиться в чат поддержки |
| 403 | Forbidden | Эндпоинт доступен только с авторизованных IP — сообщить в поддержку IP-адреса, с которых идут запросы |
| 404 | Not Found | Неверный путь/URL запроса |
| 500 | Internal Server Error | Внутренняя ошибка сервера — если повторяется, обратиться в поддержку |
| 502 | Bad Gateway | Бэкенд, вероятно, перезагружается для обновления — повторить запрос позже |
| 503 | Service Unavailable | Сервис временно недоступен (перегрузка/техработы) — повторить запрос позже |
| 504 | Gateway Timeout | Сервер не успел ответить за отведённое время — повторить запрос позже |

```python
try:
    client.create_payin(...)
except AstrumAPIError as e:
    logger.error("Astrum API error: %s (status=%s)", e, e.status_code)
```

## Колбеки (webhooks)

Площадка отправляет обычный (не подписанный и не зашифрованный) JSON POST на
`callbackUrl` (Пейин) / `callbackUrlPayout` (Пейаут). Разбор дат — через
`parse_payin_webhook` / `parse_payout_webhook`:

```python
from astrum_sdk import parse_payin_webhook

@app.post("/astrum/callback")
async def callback(request: Request):
    deal = parse_payin_webhook(await request.body())
    ...
```

Смотрите `examples/` для полного примера.
