"""SAP OData HTTP client with authentication, CSRF handling, and retry logic."""

import asyncio
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


class SAPClientError(Exception):
    """Raised when an SAP OData call fails."""

    def __init__(self, message: str, status_code: int | None = None, sap_error: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.sap_error = sap_error


class SAPClient:
    """Async HTTP client for SAP OData services.

    Features:
    - Basic authentication
    - SAP-specific headers (sap-client, X-CSRF-Token)
    - Automatic CSRF token fetch for mutating requests
    - Retry logic with exponential backoff (3 attempts)
    """

    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0  # seconds

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        sap_client: str | None = None,
    ):
        self.base_url = (base_url or settings.SAP_BASE_URL).rstrip("/")
        self._username = username or settings.SAP_USERNAME
        self._password = password or settings.SAP_PASSWORD
        self._sap_client = sap_client or settings.SAP_CLIENT
        self._csrf_token: str | None = None
        self._cookies: httpx.Cookies = httpx.Cookies()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                auth=httpx.BasicAuth(self._username, self._password),
                headers={
                    "sap-client": self._sap_client,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                cookies=self._cookies,
                timeout=httpx.Timeout(60.0),
                verify=False,  # SAP dev systems often use self-signed certs
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # CSRF token
    # ------------------------------------------------------------------

    async def _fetch_csrf_token(self) -> str:
        """Fetch a CSRF token from SAP (required before POST/PATCH/DELETE)."""
        client = await self._get_client()
        response = await client.get(
            self.base_url,
            headers={"X-CSRF-Token": "Fetch"},
        )
        token = response.headers.get("x-csrf-token", "")
        if not token:
            logger.warning("SAP did not return a CSRF token.")
        self._csrf_token = token
        self._cookies.update(response.cookies)
        return token

    # ------------------------------------------------------------------
    # Core request with retry
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Execute an HTTP request with retry + backoff."""
        client = await self._get_client()

        # For mutating methods, ensure we have a CSRF token
        if method.upper() in ("POST", "PATCH", "PUT", "DELETE"):
            if not self._csrf_token:
                await self._fetch_csrf_token()

        merged_headers: dict[str, str] = {}
        if self._csrf_token:
            merged_headers["X-CSRF-Token"] = self._csrf_token
        if headers:
            merged_headers.update(headers)

        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=merged_headers,
                )

                # Handle CSRF token expiry — SAP returns 403 with token-required
                if response.status_code == 403 and attempt < self.MAX_RETRIES:
                    logger.info("CSRF token expired, re-fetching (attempt %d).", attempt)
                    await self._fetch_csrf_token()
                    merged_headers["X-CSRF-Token"] = self._csrf_token or ""
                    continue

                if response.status_code >= 400:
                    sap_error = self._parse_odata_error(response)
                    raise SAPClientError(
                        f"SAP OData error {response.status_code}: {sap_error.get('message', 'Unknown')}",
                        status_code=response.status_code,
                        sap_error=sap_error,
                    )

                # Return parsed JSON (or empty dict for 204 No Content)
                if response.status_code == 204:
                    return {}
                return response.json()

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES:
                    wait = self.BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "SAP request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt,
                        self.MAX_RETRIES,
                        wait,
                        exc,
                    )
                    await asyncio.sleep(wait)

        raise SAPClientError(f"SAP request failed after {self.MAX_RETRIES} attempts") from last_exc

    @staticmethod
    def _parse_odata_error(response: httpx.Response) -> dict:
        """Extract the error body from a SAP OData error response."""
        try:
            body = response.json()
            error = body.get("error", {})
            return {
                "code": error.get("code", ""),
                "message": error.get("message", {}).get("value", response.text[:200]),
            }
        except Exception:
            return {"code": "", "message": response.text[:200]}

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    async def get(self, path: str, *, params: dict[str, str] | None = None) -> Any:
        """GET request to an OData entity set / entity."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        return await self._request("GET", url, params=params)

    async def post(self, path: str, *, json: dict) -> Any:
        """POST (create) an OData entity."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        return await self._request("POST", url, json=json)

    async def patch(self, path: str, *, json: dict) -> Any:
        """PATCH (update) an OData entity."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        return await self._request("PATCH", url, json=json)

    async def delete(self, path: str) -> Any:
        """DELETE an OData entity."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        return await self._request("DELETE", url)
