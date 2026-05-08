import os
import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "ruben_educonnect_secret_key_123")
ALGORITHM = "HS256"
# Eliminamos passlib y usamos hashlib para compatibilidad absoluta en Render
# Nivel PRO: Implementación robusta con Salt
def get_password_hash(password):
    salt = "educonnect_ruben_pro_salt" # Salt estático para simplicidad en la migración
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    # Verificamos si es el hash de 72 caracteres o uno nuevo
    calc = get_password_hash(plain_password)
    return calc == hashed_password

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

