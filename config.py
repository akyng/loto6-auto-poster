import os
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    API_KEY = os.getenv('X_API_KEY')
    API_KEY_SECRET = os.getenv('X_API_KEY_SECRET')
    ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')
    CLIENT_ID = os.getenv('X_CLIENT_ID')
    CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
    APP_URL = os.getenv('X_APP_URL', 'https://onelink.to/loto6oracle')

    @classmethod
    def validate(cls):
        missing = []
        for attr in ['API_KEY', 'API_KEY_SECRET', 'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET']:
            if not getattr(cls, attr):
                missing.append(f"X_{attr}")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return True
