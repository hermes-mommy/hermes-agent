"""P13 X Auto Poster — Official X API v2 client (OAuth 2.0 Bearer + auto-refresh)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import httpx
import structlog

from .config import XPosterSettings
from .exceptions import (
    XApiAuthError,
    XApiError,
    XApiPostError,
    XApiRateLimitError,
)

_logger = structlog.get_logger(__name__)

_API_BASE = "https://api.x.com"
_UPLOAD_BASE = "https://upload.twitter.com"
_TOKEN_URL = "https://api.x.com/2/oauth2/token"
_UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB
_REFRESH_BUFFER_SECONDS = 300  # Refresh 5 min before expiry


class XApiClient:
    """Async Official X API v2 client with OAuth 2.0 Bearer Token + auto-refresh."""

    def __init__(self, settings: XPosterSettings) -> None:
        self._settings = settings
        self._access_token: str = settings.x_access_token
        self._refresh_token: str = settings.x_refresh_token
        self._token_expires_at: float = 0.0  # epoch seconds; 0 = unknown/force refresh
        self._authenticated = False
        self._log = _logger.bind()

    async def __aenter__(self) -> XApiClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Validate token and refresh if needed."""
        if self._authenticated and not self._token_needs_refresh():
            return

        if not self._access_token:
            raise XApiAuthError("No X API access token configured")

        # Try refresh if we have refresh_token + client_id and token is expired/unknown
        if self._token_needs_refresh() and self._refresh_token and self._settings.x_client_id:
            try:
                await self._refresh_access_token()
            except XApiAuthError as exc:
                self._log.warning(
                    "x_poster.x_api.refresh_failed_using_existing_token",
                    error=str(exc),
                )
                # Non-fatal: continue with existing token if available

        self._authenticated = True
        self._log.info("x_poster.x_api.connected")

    async def disconnect(self) -> None:
        self._authenticated = False
        self._log.info("x_poster.x_api.disconnected")

    def _token_needs_refresh(self) -> bool:
        if self._token_expires_at == 0.0:
            return True  # Unknown expiry, try refresh
        return time.time() >= (self._token_expires_at - _REFRESH_BUFFER_SECONDS)

    async def _refresh_access_token(self) -> None:
        """Refresh the OAuth 2.0 access token using the refresh token."""
        if not self._refresh_token or not self._settings.x_client_id:
            self._log.warning("x_poster.x_api.refresh_skipped_missing_credentials")
            return

        self._log.info("x_poster.x_api.refreshing_token")

        payload: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._settings.x_client_id,
        }
        if self._settings.x_client_secret:
            payload["client_secret"] = self._settings.x_client_secret

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            raise XApiAuthError(
                f"Token refresh failed: {response.status_code} {response.text}"
            )

        data = response.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        expires_in = int(data.get("expires_in", 7200))
        self._token_expires_at = time.time() + expires_in

        self._log.info(
            "x_poster.x_api.token_refreshed",
            expires_in=expires_in,
        )

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid token, refreshing if needed."""
        if self._token_needs_refresh() and self._refresh_token and self._settings.x_client_id:
            try:
                await self._refresh_access_token()
            except XApiAuthError as exc:
                self._log.warning(
                    "x_poster.x_api.refresh_failed_continuing_with_existing_token",
                    error=str(exc),
                )

    async def post_media(self, media_paths: list[str], caption: str | None = None) -> dict[str, Any]:
        """Upload multiple media files (up to 4), mark sensitive, and create a single tweet."""
        if not media_paths:
            raise XApiPostError("No media paths provided")

        paths = [Path(p) for p in media_paths]
        for path in paths:
            if not path.exists() or not path.is_file():
                raise XApiPostError("Media file does not exist", {"media_path": str(path)})

        self._log.info(
            "x_poster.x_api.post_starting",
            media_count=len(paths),
            media_paths=[str(p) for p in paths],
        )

        try:
            media_ids = []
            for path in paths:
                media_id = await self._upload_media(path)
                await self._mark_sensitive(media_id)
                media_ids.append(media_id)

            tweet_id = await self._create_tweet(caption or "", media_ids)
            tweet_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else ""

            if self._settings.x_post_delay_seconds:
                await asyncio.sleep(self._settings.x_post_delay_seconds)

            self._log.info(
                "x_poster.x_api.post_completed",
                tweet_id=tweet_id,
                tweet_url=tweet_url,
                media_count=len(media_ids),
            )
            return {"ok": True, "tweet_id": tweet_id, "tweet_url": tweet_url}
        except XApiError:
            raise
        except Exception as exc:
            raise XApiPostError(f"Failed to create X post: {exc}") from exc

    async def get_user_tweets(self, user_id: str, max_results: int = 100) -> list[dict[str, Any]]:
        """Fetch recent tweets from a user account via OAuth 1.0a GET /2/users/:id/tweets."""
        if not self._settings.x_oauth1_access_token:
            self._log.warning("x_poster.x_api.get_user_tweets_no_credentials")
            return []

        tweets: list[dict[str, Any]] = []
        pagination_token: str | None = None

        try:
            while len(tweets) < max_results:
                params: dict[str, str] = {
                    "tweet.fields": "public_metrics,created_at",
                    "max_results": str(min(100, max_results - len(tweets))),
                    "exclude": "retweets",
                }
                if pagination_token:
                    params["pagination_token"] = pagination_token

                response = await self._oauth1_request(
                    "GET",
                    f"{_API_BASE}/2/users/{user_id}/tweets",
                    params=params,
                )

                if response.status_code != 200:
                    self._log.warning(
                        "x_poster.x_api.get_user_tweets_failed",
                        status=response.status_code,
                        body=response.text[:200],
                    )
                    break

                data = response.json()
                raw_tweets = data.get("data", [])
                if not raw_tweets:
                    break

                for t in raw_tweets:
                    metrics = t.get("public_metrics", {})
                    tweets.append({
                        "tweet_id": t.get("id", ""),
                        "text": t.get("text", ""),
                        "created_at": t.get("created_at", ""),
                        "impressions": int(metrics.get("impression_count", 0)),
                        "likes": int(metrics.get("like_count", 0)),
                        "replies": int(metrics.get("reply_count", 0)),
                        "retweets": int(metrics.get("retweet_count", 0)),
                        "quotes": int(metrics.get("quote_count", 0)),
                        "bookmarks": int(metrics.get("bookmark_count", 0)),
                    })

                meta = data.get("meta", {})
                pagination_token = meta.get("next_token")
                if not pagination_token:
                    break

                await asyncio.sleep(1)

            self._log.info(
                "x_poster.x_api.user_tweets_fetched",
                user_id=user_id,
                count=len(tweets),
            )
        except Exception as exc:
            self._log.warning(
                "x_poster.x_api.get_user_tweets_error",
                user_id=user_id,
                error=str(exc),
            )

        return tweets

    async def get_tweet_engagement(self, tweet_id: str) -> dict[str, Any]:
        """Fetch public_metrics for a tweet via OAuth 1.0a GET /2/tweets/:id."""
        if not self._settings.x_oauth1_access_token:
            return {"ok": False, "error": "No OAuth1 credentials"}

        try:
            response = await self._oauth1_request(
                "GET",
                f"{_API_BASE}/2/tweets/{tweet_id}",
                params={"tweet.fields": "public_metrics"},
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                metrics = data.get("public_metrics", {})
                self._log.info(
                    "x_poster.x_api.engagement_fetched",
                    tweet_id=tweet_id,
                    impressions=metrics.get("impression_count", 0),
                    likes=metrics.get("like_count", 0),
                )
                return {
                    "ok": True,
                    "tweet_id": tweet_id,
                    "impressions": int(metrics.get("impression_count", 0)),
                    "likes": int(metrics.get("like_count", 0)),
                    "replies": int(metrics.get("reply_count", 0)),
                    "retweets": int(metrics.get("retweet_count", 0)),
                    "quotes": int(metrics.get("quote_count", 0)),
                    "bookmarks": int(metrics.get("bookmark_count", 0)),
                }
            self._log.warning(
                "x_poster.x_api.engagement_fetch_failed",
                tweet_id=tweet_id,
                status=response.status_code,
            )
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        except Exception as exc:
            self._log.warning(
                "x_poster.x_api.engagement_fetch_error",
                tweet_id=tweet_id,
                error=str(exc),
            )
            return {"ok": False, "error": str(exc)}

    async def check_health(self) -> dict[str, bool]:
        """Verify API credentials by calling /2/users/me with OAuth 1.0a."""
        if not self._settings.x_oauth1_access_token:
            return {"authenticated": False}

        try:
            response = await self._oauth1_request(
                "GET",
                f"{_API_BASE}/2/users/me",
                params={"user.fields": "id,name"},
            )
            if response.status_code == 200:
                self._authenticated = True
                data = response.json().get("data", {})
                self._log.info(
                    "x_poster.x_api.health_ok",
                    user_id=data.get("id"),
                    username=data.get("username"),
                )
                return {"authenticated": True}
            self._authenticated = False
            return {"authenticated": False}
        except Exception as exc:
            self._log.warning("x_poster.x_api.health_check_failed", error=str(exc))
            self._authenticated = False
            return {"authenticated": False}

    async def get_me(self) -> dict[str, str]:
        """Return authenticated user's ID and username via /2/users/me."""
        if not self._settings.x_oauth1_access_token:
            return {"id": "", "username": ""}
        try:
            response = await self._oauth1_request(
                "GET",
                f"{_API_BASE}/2/users/me",
                params={"user.fields": "id,name,username"},
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "id": str(data.get("id", "")),
                    "username": str(data.get("username", "")),
                }
        except Exception as exc:
            self._log.warning("x_poster.x_api.get_me_failed", error=str(exc))
        return {"id": "", "username": ""}

    # --- Media upload (OAuth 1.0a v1.1 chunked fallback) ---

    async def _upload_media(self, path: Path) -> str:
        """Upload media through v1.1 media/upload using OAuth 1.0a user context.

        X API OAuth2 in this app UI exposes tweet.write but not media.write, so the v2 media
        endpoint returns 403. The supported fallback is legacy v1.1 media upload with OAuth1,
        then creating the tweet through v2 with the returned media_id.
        """
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        media_category = self._media_category(media_type)
        total_bytes = path.stat().st_size

        self._ensure_oauth1_media_credentials()
        self._log.info("x_poster.x_api.media_upload_init", media_type=media_type, total_bytes=total_bytes)

        media_id = await self._media_init(media_type, media_category, total_bytes)

        segment_index = 0
        with path.open("rb") as f:
            while True:
                chunk = f.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                await self._media_append(media_id, chunk, segment_index)
                segment_index += 1

        finalize_data = await self._media_finalize(media_id)
        await self._media_wait_processing(media_id, finalize_data)

        self._log.info("x_poster.x_api.media_uploaded", media_id=media_id)
        return media_id

    def _ensure_oauth1_media_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "x_api_key": self._settings.x_api_key,
                "x_api_secret": self._settings.x_api_secret,
                "x_oauth1_access_token": self._settings.x_oauth1_access_token,
                "x_oauth1_access_token_secret": self._settings.x_oauth1_access_token_secret,
            }.items()
            if not value
        ]
        if missing:
            raise XApiAuthError(
                "OAuth 1.0a media credentials are required for media upload: " + ", ".join(missing)
            )

    async def _media_init(self, media_type: str, media_category: str, total_bytes: int) -> str:
        payload = {
            "command": "INIT",
            "media_type": media_type,
            "media_category": media_category,
            "total_bytes": str(total_bytes),
        }
        response = await self._oauth1_request(
            "POST",
            f"{_UPLOAD_BASE}/1.1/media/upload.json",
            data=payload,
        )
        if response.is_error:
            raise XApiPostError(f"Media init failed: {response.status_code} {response.text}")
        data = response.json()
        media_id = data.get("media_id_string") or data.get("media_id")
        if not media_id:
            raise XApiPostError("Media init returned no media_id", {"response": data})
        return str(media_id)

    async def _media_append(self, media_id: str, chunk: bytes, segment_index: int) -> None:
        response = await self._oauth1_request(
            "POST",
            f"{_UPLOAD_BASE}/1.1/media/upload.json",
            params={
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": str(segment_index),
            },
            files={"media": ("chunk", chunk, "application/octet-stream")},
        )

        if response.status_code == 429:
            raise XApiRateLimitError("Media append rate limited")
        if response.is_error:
            raise XApiPostError(
                f"Media append failed: {response.status_code} {response.text}",
                {"segment_index": segment_index},
            )

    async def _media_finalize(self, media_id: str) -> dict[str, Any]:
        response = await self._oauth1_request(
            "POST",
            f"{_UPLOAD_BASE}/1.1/media/upload.json",
            data={"command": "FINALIZE", "media_id": media_id},
        )
        if response.is_error:
            raise XApiPostError(f"Media finalize failed: {response.status_code} {response.text}")
        return response.json()

    async def _media_wait_processing(self, media_id: str, finalize_data: dict[str, Any]) -> None:
        processing = finalize_data.get("processing_info")
        if not processing:
            return

        for _ in range(60):
            state = processing.get("state", "")
            if state == "succeeded":
                return
            if state == "failed":
                raise XApiPostError("Media processing failed", {"processing_info": processing})

            delay = int(processing.get("check_after_secs", 5))
            await asyncio.sleep(delay)

            response = await self._oauth1_request(
                "GET",
                f"{_UPLOAD_BASE}/1.1/media/upload.json",
                params={"command": "STATUS", "media_id": media_id},
            )
            if response.is_error:
                raise XApiPostError(f"Media status check failed: {response.status_code} {response.text}")
            processing = response.json().get("processing_info", {})

        raise XApiPostError("Media processing timed out after 60 checks")

    # --- NSFW metadata ---

    async def _mark_sensitive(self, media_id: str) -> None:
        payload: dict[str, Any] = {
            "media_id": media_id,
            "sensitive_media_warning": {
                "adult_content": "true",
            },
        }
        try:
            response = await self._oauth1_request(
                "POST",
                f"{_UPLOAD_BASE}/1.1/media/metadata/create.json",
                json_payload=payload,
            )
            if response.is_error:
                raise XApiPostError(f"Media metadata failed: {response.status_code} {response.text}")
            self._log.info("x_poster.x_api.sensitive_marked", media_id=media_id)
        except Exception as exc:
            self._log.warning("x_poster.x_api.sensitive_mark_failed", media_id=media_id, error=str(exc))

    # --- Tweet creation ---

    async def _create_tweet(self, text: str, media_ids: list[str]) -> str:
        payload: dict[str, Any] = {}
        if text:
            payload["text"] = text
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        response = await self._oauth1_request("POST", f"{_API_BASE}/2/tweets", json_payload=payload)
        if response.is_error:
            raise XApiPostError(f"Tweet creation failed: {response.status_code} {response.text}")
        data = response.json().get("data", {})
        tweet_id = data.get("id", "")
        if not tweet_id:
            raise XApiPostError("Tweet creation returned no id", {"response": response})
        self._log.info("x_poster.x_api.tweet_created", tweet_id=tweet_id)
        return str(tweet_id)

    # --- HTTP helpers (Bearer Token auth) ---

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:
            # Token may have expired, try refresh once
            if self._refresh_token and self._settings.x_client_id and not kwargs.pop("_refreshed", False):
                self._log.info("x_poster.x_api.401_retrying_refresh")
                try:
                    await self._refresh_access_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    kwargs["_refreshed"] = True
                    async with httpx.AsyncClient(timeout=30.0) as client2:
                        response = await client2.request(method, url, headers=headers, **kwargs)
                    return response
                except XApiAuthError as exc:
                    self._log.warning("x_poster.x_api.refresh_failed_401", error=str(exc))
            self._authenticated = False
            raise XApiAuthError("Auth failed: 401")

        if response.status_code == 429:
            retry_after = int(response.headers.get("retry-after", "15"))
            self._log.warning("x_poster.x_api.rate_limited", retry_after=retry_after)
            raise XApiRateLimitError(f"Rate limited, retry after {retry_after}s")

        if response.status_code == 403:
            self._authenticated = False
            raise XApiAuthError(f"Auth forbidden: {response.status_code} {response.text}")

        return response

    async def _request_json(self, method: str, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"))
        response = await self._request(
            method,
            url,
            content=body,
            headers={"Content-Type": "application/json"},
        )
        if response.is_error:
            raise XApiPostError(
                f"X API error {response.status_code}: {response.text}",
                {"url": url},
            )
        return response.json()

    async def _request_multipart(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> httpx.Response:
        headers = self._auth_headers()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.request(method, url, headers=headers, data=data, files=files)
        return response

    # --- OAuth 1.0a helpers (legacy media upload) ---

    async def _oauth1_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> httpx.Response:
        request_url = self._with_query(url, params or {})
        signature_params: dict[str, str] = {}
        if params:
            signature_params.update(params)
        if data and not files:
            signature_params.update(data)

        headers = {"Authorization": self._oauth1_authorization_header(method, url, signature_params)}
        if json_payload is not None:
            headers["Content-Type"] = "application/json"
            content = json.dumps(json_payload, separators=(",", ":"))
            async with httpx.AsyncClient(timeout=120.0) as client:
                return await client.request(method, request_url, headers=headers, content=content)

        async with httpx.AsyncClient(timeout=120.0) as client:
            return await client.request(method, request_url, headers=headers, data=data, files=files)

    def _oauth1_authorization_header(
        self,
        method: str,
        url: str,
        extra_params: dict[str, str],
    ) -> str:
        oauth_params = {
            "oauth_consumer_key": self._settings.x_api_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self._settings.x_oauth1_access_token,
            "oauth_version": "1.0",
        }
        signature_params = {**extra_params, **oauth_params}
        oauth_params["oauth_signature"] = self._oauth1_signature(method, url, signature_params)
        header_parts = [
            f'{quote(key, safe="")}="{quote(value, safe="")}"'
            for key, value in sorted(oauth_params.items())
        ]
        return "OAuth " + ", ".join(header_parts)

    def _oauth1_signature(self, method: str, url: str, params: dict[str, str]) -> str:
        split = urlsplit(url)
        normalized_url = urlunsplit((split.scheme, split.netloc, split.path, "", ""))
        query_pairs = dict(pair.split("=", 1) for pair in split.query.split("&") if pair and "=" in pair)
        all_params = {**query_pairs, **params}
        encoded_params = [(quote(str(k), safe=""), quote(str(v), safe="")) for k, v in all_params.items()]
        parameter_string = "&".join(f"{k}={v}" for k, v in sorted(encoded_params))
        base_string = "&".join(
            [
                method.upper(),
                quote(normalized_url, safe=""),
                quote(parameter_string, safe=""),
            ]
        )
        signing_key = "&".join(
            [
                quote(self._settings.x_api_secret, safe=""),
                quote(self._settings.x_oauth1_access_token_secret, safe=""),
            ]
        )
        digest = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        return base64.b64encode(digest).decode()

    @staticmethod
    def _with_query(url: str, params: dict[str, str]) -> str:
        if not params:
            return url
        separator = "&" if "?" in url else "?"
        return url + separator + urlencode(params)

    # --- Utilities ---

    @staticmethod
    def _media_category(media_type: str) -> str:
        if media_type == "image/gif":
            return "tweet_gif"
        if media_type.startswith("image/"):
            return "tweet_image"
        if media_type.startswith("video/"):
            return "tweet_video"
        return "tweet_image"


__all__ = ["XApiClient"]
