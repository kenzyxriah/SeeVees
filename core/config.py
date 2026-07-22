from decouple import config

ENVIRONMENT: str = config("ENVIRONMENT")
REDIS_HOST: str = config("REDIS_HOST")
REDIS_PORT: str = config("REDIS_PORT")
SECRET_KEY: str = config("SECRET_KEY")
BASE_URL: str = config("BASE_URL", default="http://seevees.api")


POSTGRES_USER: str = config("POSTGRES_USER")
POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD")
POSTGRES_HOST: str = config("POSTGRES_HOST")
POSTGRES_PORT: str = config("POSTGRES_PORT")
POSTGRES_DB: str = config("POSTGRES_DB")

REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
POSTGRES_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
