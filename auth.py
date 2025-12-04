from fastapi import HTTPException, status, Header
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
from pydantic import BaseModel
import os

# Secret key for encoding and decoding JWT tokens (should be stored securely, not hardcoded)
SECRET_KEY = "your-secret-key"  # Change this to something secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expiration time in minutes

# Pydantic model for user data
class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

# Simulate a user database for demonstration purposes
fake_users_db = {
    "user1": {
        "username": "user1",
        "password": "hashed_password_1",  # In a real app, use hashed passwords
    },
    "admin": {
        "username": "admin",
        "password": "hashed_password_2",  # In a real app, use hashed passwords
    }
}

# Function to authenticate a user
def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user:
        return None
    if user["password"] != password:
        return None
    return User(**user)

# Function to create an access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to verify a token and extract its data
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return TokenData(username=username)
    except JWTError:
        raise credentials_exception

# Function to get the current user from a valid token
def get_current_user(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_token(token)


def decode_jwt_token(token: str):
    try:
        # Decode the token without verifying the signature (for demo purposes)
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated: Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1].strip()
    
    if not token:
        raise HTTPException(status_code=400, detail="Invalid token format.")
    
    decoded_payload = decode_jwt_token(token)
    user_id = decoded_payload.get("sub")  # Typically, user ID is stored under "sub" in JWT
    return user_id