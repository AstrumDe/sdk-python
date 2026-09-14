from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("astrum-sdk")
except PackageNotFoundError:
    # Пакет не установлен через pip (например, файлы просто скопированы) —
    # запасное значение, держите в синхроне с pyproject.toml.
    __version__ = "0.1.0"
