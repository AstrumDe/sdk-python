"""Пример создания и подтверждения сделки (Пейин) через astrum_sdk."""

from astrum_sdk import AstrumClient

client = AstrumClient(
    api_key="YOUR_API_KEY",
    private_key="YOUR_PRIVATE_KEY",
    base_url="YOUR_API_BASE_URL",  # адрес выдаёт площадка при регистрации
)

result = client.create_payin(
    foreign_id="testpayin2_trans",
    amount=70.0,
    method_type_id=46,
    client_id="testuser1",
)
print(result)
