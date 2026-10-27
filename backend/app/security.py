import base64, hashlib, secrets
from datetime import timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import select
from .config import settings
from .db import get_db, now
from .models import User, Session, Audit
passwords = PasswordHash.recommended()

def cipher():
    key = settings.encryption_key
    if not key:
        if settings.production: raise RuntimeError('ENCRYPTION_KEY required in production')
        path = Path(settings.storage_dir) / '.encryption-key'
        if not path.exists():
            try:
                with path.open('xb') as f: f.write(Fernet.generate_key())
                path.chmod(0o600)
            except FileExistsError: pass
        key = path.read_text().strip()
    return Fernet(key.encode())

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
def create_session(db, user):
    token = secrets.token_urlsafe(32)
    db.add(Session(token=token_hash(token), user_id=user.id, expires_at=now()+timedelta(days=7)))
    db.commit()
    return token

def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get('careerorbit_session','')
    session = db.get(Session, token_hash(token))
    if not session or session.expires_at < now(): raise HTTPException(401,'Sign in required')
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin = request.headers.get('origin')
        if origin != settings.app_url: raise HTTPException(403,'Untrusted request origin')
        if request.headers.get('x-careerorbit-request') != '1': raise HTTPException(403,'CSRF header required')
    user = db.get(User, session.user_id)
    if not user: raise HTTPException(401,'Account not found')
    return user

def audit(db, user_id, action, **details):
    db.add(Audit(user_id=user_id, action=action, details=details))
