import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AuthSettings:
    base_url: str
    google_client_id: str
    google_client_secret: str
    session_secret: str
    cookie_secure: bool = True
    session_days: int = 7
    candidates_collection: str = "candidates"
    cookie_name: str = "election_session"

    @classmethod
    def from_env(cls):
        base = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")
        parsed = urlsplit(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise RuntimeError("APP_BASE_URL harus berupa origin, misalnya https://vote.example.com")
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        secure = os.getenv("COOKIE_SECURE", "true").lower() == "true"
        if not local and (parsed.scheme != "https" or not secure):
            raise RuntimeError("Domain publik wajib HTTPS dan COOKIE_SECURE=true")
        secret = os.getenv("SESSION_SECRET", "")
        if len(secret) < 32:
            raise RuntimeError("Isi SESSION_SECRET dengan minimal 32 karakter acak")
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise RuntimeError("Isi GOOGLE_CLIENT_ID dan GOOGLE_CLIENT_SECRET di .env")
        return cls(base, client_id, client_secret, secret, secure,
                   candidates_collection=os.getenv("CANDIDATES_COLLECTION", "candidates"))
