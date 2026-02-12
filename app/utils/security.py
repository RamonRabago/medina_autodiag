from passlib.context import CryptContext

# bcrypt primero: nuevos hashes se crean con bcrypt. argon2: para verificar usuarios antiguos (local).
pwd_context = CryptContext(
    schemes=["bcrypt", "argon2"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)
