import secrets

def generate_signup_token() -> str:
    # 256-bit token, URL-safe hex
    return secrets.token_hex(32)
