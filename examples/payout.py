"""Пример создания сделки (Пейаут) через astrum_sdk."""

from astrum_sdk import AstrumClient

client = AstrumClient(
    api_key="YOUR_API_KEY",
    private_key="YOUR_PRIVATE_KEY",
    base_url="YOUR_API_BASE_URL",  # адрес выдаёт площадка при регистрации
)

result = client.create_payout(
    foreign_id="testpayout",
    amount=10,
    requisite="1111222233334444",
    method_type_id=5,
    client_initials="Test Name",
)
print(result)
