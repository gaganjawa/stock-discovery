"""Single-owner sessions. Fail closed without a strong configured access key."""
import hashlib
import hmac
import os
import secrets
import time
from fastapi import HTTPException,Request


def secret():
    value=os.getenv('AUTH_TOKEN','')
    if len(value)<32: raise HTTPException(503,'Owner access key is not configured')
    return value


def session():
    payload=str(int(time.time())+8*3600)+'.'+secrets.token_hex(16)
    sig=hmac.new(secret().encode(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+sig


def require_auth(request: Request):
    key=secret()
    auth=request.headers.get('Authorization','')
    if auth.startswith('Bearer ') and hmac.compare_digest(auth[7:].encode(),key.encode()): return
    cookie=request.cookies.get('stk_session','')
    try:
        expiry,nonce,sig=cookie.split('.')
        expected=hmac.new(key.encode(),(expiry+'.'+nonce).encode(),hashlib.sha256).hexdigest()
        valid=int(expiry)>time.time() and hmac.compare_digest(sig,expected)
    except (ValueError,TypeError): valid=False
    if not valid: raise HTTPException(401,'Sign in required')
    if request.method not in ('GET','HEAD'):
        origin=request.headers.get('origin')
        expected_origin=os.getenv('APP_ORIGIN',str(request.base_url).rstrip('/'))
        if origin!=expected_origin: raise HTTPException(403,'Request origin rejected')
