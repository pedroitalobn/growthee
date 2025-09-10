import jwt
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Configurações JWT
JWT_SECRET = os.getenv("JWT_SECRET_KEY") or "your-secret-key-here"
JWT_ALGORITHM = "HS256"

def generate_token(user_id: str, email: str):
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

if __name__ == "__main__":
    # Usar o usuário admin para teste
    user_id = "cmfcsvva50000ieylo94lzbhf"
    email = "admin@admin.com"
    
    token = generate_token(user_id, email)
    print(f"Token JWT: {token}")