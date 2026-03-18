import bcrypt


def generate_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    return password_hash

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    password_hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, password_hash_bytes)