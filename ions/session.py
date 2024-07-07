from datetime import datetime, timedelta
from logging import getLogger

import requests

from . import exceptions as exc

__version__ = 0.1

__url_cache__ = {}
__logs__ = getLogger(__package__)


class IonsSession(requests.Session):
    __attrs__ = requests.Session.__attrs__ + [
        "base_url",
        "default_connect_timeout",
        "default_read_timeout",
    ]

    auth = None

    def __init__(
        self,
        username,
        password,
        default_connect_timeout=4,
        default_read_timeout=10,
    ):
        super().__init__()
        self.default_connect_timeout = default_connect_timeout
        self.default_read_timeout = default_read_timeout
        self.base_url = "https://integra.ons.org.br/api"
        self.headers.update(
            {
                "Accept": "application/json",
                "Accept-Charset": "utf-8",
                "Content-Type": "application/json",
                "User-Agent": f"ions/{__version__}",
            }
        )
        self._login(username, password)

    @property
    def timeout(self):
        return (self.default_connect_timeout, self.default_read_timeout)

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        response = super().request(*args, **kwargs)
        return response

    def _login(self, username, password):
        url = self.build_url("autenticar")
        request_body = {"usuario": username, "senha": password}
        response = self.post(url, json=request_body)
        if response.status_code != 200:
            response.raise_for_status()
        json = response.json()
        self.bearer_auth(json)

    def bearer_auth(self, json):
        if not json:
            return
        token = json.get("access_token", "")
        expire_in = int(json.get("expires_in", 60 * 60))
        self.auth = BearerTokenAuth(token, expire_in)

    def build_url(self, *args, **kwargs):
        parts = [kwargs.get("base_url") or self.base_url]
        parts.extend(args)
        parts = [str(p) for p in parts]
        key = tuple(parts)
        __logs__.info("Building a url from %s", key)
        if key not in __url_cache__:
            __logs__.info("Missed the cache building the url")
            __url_cache__[key] = "/".join(parts)
        return __url_cache__[key]


class BearerTokenAuth(requests.auth.AuthBase):
    def __init__(self, token, expire_in):
        self.token = token
        expire_in = timedelta(seconds=expire_in)
        self.expires_at = datetime.now() + expire_in

    def __repr__(self):
        """Return a helpful view of the token."""
        return f"token {self.token[:4]} expiring at {self.expires_at}"

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return self.token == getattr(other, "token", None)

    @property
    def expired(self):
        return datetime.now() > self.expires_at

    def __call__(self, request):
        if self.expired:
            raise exc.TokenExpired(f"Token expired at {self.expires_at}")
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request
