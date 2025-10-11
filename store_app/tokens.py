import secrets
from django.utils import timezone
from datetime import timedelta

def new_email_token(hours_valid=1):
    return secrets.token_hex(32), timezone.now() + timedelta(hours=hours_valid)
