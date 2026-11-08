import os


# Подключение к PostgreSQL через синхронный драйвер
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://lab:lab@db:5432/flights"
)


# Подключение через асинхронный драйвер
ASYNC_DATABASE_URL = DATABASE_URL.replace(
    "postgresql+psycopg://",
    "postgresql+asyncpg://"
)


# Адреса трёх авиапоставщиков
SUPPLIERS = [
    os.getenv("SUPPLIER_1", "http://supplier1:8101"),
    os.getenv("SUPPLIER_2", "http://supplier2:8102"),
    os.getenv("SUPPLIER_3", "http://supplier3:8103")
]

# Максимальное время ожидания одного поставщика
SUPPLIER_TIMEOUT = 2.0
# Количество повторов после ошибки
RETRIES = 1
# Пауза перед повторным запросом
RETRY_DELAY = 0.2