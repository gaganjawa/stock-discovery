"""Bounded login throttling for one API process; never trust forwarded IPs."""
from collections import deque
import threading
import time
from fastapi.responses import JSONResponse


class LoginLimiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.global_attempts = deque()
        self.peers = {}

    def allow(self, peer):
        with self.lock:
            now = self.clock()
            cutoff = now - 60
            while self.global_attempts and self.global_attempts[0] <= cutoff:
                self.global_attempts.popleft()
            for key in list(self.peers):
                values = self.peers[key]
                while values and values[0] <= cutoff:
                    values.popleft()
                if not values:
                    del self.peers[key]
            if len(self.global_attempts) >= 20:
                return False
            self.global_attempts.append(now)
            values = self.peers.setdefault(peer, deque())
            if len(values) >= 5:
                return False
            values.append(now)
            return True


async def throttle(request, call_next):
    if request.method == "POST" and request.url.path == "/api/v1/session":
        peer = request.client.host if request.client else "unknown"
        if not request.app.state.login_limiter.allow(peer):
            return JSONResponse({"detail": "Too many login attempts"}, status_code=429,
                                headers={"Retry-After": "60"})
    return await call_next(request)
