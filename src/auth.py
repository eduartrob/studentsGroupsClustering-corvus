import os
import jwt
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User

security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_corvus_dev_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
DEV_BYPASS = os.getenv("DEV_BYPASS", "true").lower() == "true"

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    user_id = None
    
    # 1. Bypass para pruebas locales: si el token es un UUID válido, lo tomamos como userId directo
    if DEV_BYPASS:
        try:
            uuid.UUID(token)
            user_id = token
        except ValueError:
            pass
            
    # 2. Si no es UUID o bypass está apagado, decodificar el token JWT estándar
    if not user_id:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub") or payload.get("id") or payload.get("userId")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="El token no contiene un identificador de usuario válido en 'sub', 'id' o 'userId'.",
                )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El token ha expirado.",
            )
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token de autorización inválido: {str(e)}",
            )
            
    # 3. Buscar el usuario en la base de datos
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario con ID '{user_id}' no existe en la base de datos.",
        )
    return user
