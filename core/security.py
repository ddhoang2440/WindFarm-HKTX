from fastapi import Depends, HTTPException
from config.settings import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Token")
    return credentials.credentials