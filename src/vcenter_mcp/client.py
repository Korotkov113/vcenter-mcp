"""Async vCenter REST API client using httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class VCenterError(Exception):
    """Raised when vCenter API returns an error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"vCenter API error {status_code}: {message}")


class VCenterClient:
    """Async client for the vCenter 8 REST API (VI/JSON)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = f"https://{settings.vcenter_host}:{settings.vcenter_port}/api"
        self._session_token: str | None = None
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Create an httpx client and obtain a vCenter session token."""
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._settings.vcenter_ssl_verify,
            timeout=30.0,
        )
        response = await self._http.post(
            "/session",
            auth=(self._settings.vcenter_username, self._settings.vcenter_password),
        )
        self._raise_for_status(response)
        # The token is returned as a plain JSON string (with quotes)
        self._session_token = response.json()
        logger.info("Authenticated to vCenter %s", self._settings.vcenter_host)

    async def close(self) -> None:
        """Delete the session and close the HTTP client."""
        if self._http and self._session_token:
            try:
                await self._http.delete(
                    "/session",
                    headers={"vmware-api-session-id": self._session_token},
                )
            except Exception:
                pass
        if self._http:
            await self._http.aclose()
        self._http = None
        self._session_token = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if not self._session_token:
            raise RuntimeError("Not authenticated — call authenticate() first")
        return {"vmware-api-session-id": self._session_token}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
    ) -> Any:
        assert self._http is not None, "Client not initialised"
        response = await self._http.request(
            method,
            path,
            headers=self._auth_headers(),
            params=params,
            json=json,
        )
        # Auto-reauthenticate once on 401
        if response.status_code == 401:
            logger.warning("Session expired — re-authenticating")
            await self.authenticate()
            response = await self._http.request(
                method,
                path,
                headers=self._auth_headers(),
                params=params,
                json=json,
            )
        self._raise_for_status(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any = None, params: dict | None = None) -> Any:
        return await self._request("POST", path, json=json, params=params)

    async def patch(self, path: str, json: Any = None) -> Any:
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str, params: dict | None = None) -> Any:
        return await self._request("DELETE", path, params=params)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                detail = response.json()
                msg = detail.get("messages", [{}])[0].get("default_message", response.text)
            except Exception:
                msg = response.text
            raise VCenterError(response.status_code, msg)
