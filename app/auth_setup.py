from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from app.auth_config import AuthSettings
from app.api.auth import router


def install_auth(app, settings: AuthSettings | None = None):
    settings = settings or AuthSettings.from_env()
    app.state.auth_settings = settings
    oauth = OAuth()
    oauth.register(name="google", client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"})
    app.state.oauth = oauth
    # Cookie singkat khusus state/nonce OAuth; sesi pengguna ada di MongoDB.
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret,
        session_cookie="election_oauth", max_age=600, same_site="lax",
        https_only=settings.cookie_secure)
    app.include_router(router)
