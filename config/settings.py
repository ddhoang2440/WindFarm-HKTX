from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb+srv://ddhoang2440_db_user:dZnUN0yDeWkF9EVM@windfarm.fxgf0y1.mongodb.net"
    DATABASE_NAME: str = "windfarm"
    API_TOKEN: str = "EnoDncjaHecKAaU_4ev-UA7_oRhMamg9mW1vEDqwfzI"
    ML_SERVICE_URL: str = "http://127.0.0.1:8001" # Server local của Long
    
    class Config:
        env_file = ".env" 
settings = Settings()