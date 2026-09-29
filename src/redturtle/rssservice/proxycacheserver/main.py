"""
This code implements a caching proxy server that stores and serves web content.

Key Components:
* Creates unique filenames for cached content using SHA256 hashing
* Stores both the content and metadata (URL information) in separate files
* Background refresh content periodically

The Proxy Server:

* Listens for incoming requests (protected against SSRF and concurrent requests)
* Checks if requested content is in cache
* If found, serves from cache
* If not found, fetches it, saves it, then serves it

Background Refresh:

* Automatically updates cached content periodically
* Runs in separate threads to not block the main server (deduplicated per URL)
* Time between updates is configurable (TTL - Time To Live)

Command Line Interface: Uses Click library to accept parameters like:

Host address (default: 127.0.0.1)
Port number (default: 8080)
Cache directory location (default: ./var/cache)
TTL for cache refresh (default: 3600 seconds)

Usage Example:

```
rssmixer-proxy --host 127.0.0.1 --port 8080 --cache-dir ./var/cache --ttl 3600
```

XXX: this is not actually a real HTTP/HTTPS proxy because needs to act as man-in-the-middle

Usage:

```python
import requests

RSSMIXER_PROXY = "http://127.0.0.1:8080"
url = "https://abcnews.go.com/abcnews/usheadlines"
res = requests.get(f"{RSSMIXER_PROXY}/{url}")
```

This is particularly useful for:

* Reducing load on original servers
* Improving response times
* Working with content even when the original source is temporarily unavailable
* Saving bandwidth by not repeatedly downloading the same content
"""

import click
import hashlib
import http.server
import json
import logging
import os
import re
import requests
import socketserver
import threading
import time
from urllib.parse import urlparse

LOCK = threading.Lock()
LAST_ACCESS_TIMES = {}
ACTIVE_REFRESH_THREADS = set()
MAX_TTL_IN_CACHE = 7 * 24 * 3600  # 1 week

logger = logging.getLogger("rssmixer-proxy")
logger.setLevel(logging.INFO)
if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def cache_path(url, cache_dir):
    hash_url = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{hash_url}.json")


def safe_atomic_write_json(file_path, data):
    tmp_path = f"{file_path}.tmp.{threading.get_ident()}_{time.time_ns()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, file_path)
    except Exception as e:
        logger.error("Error writing atomically to %s: %s", file_path, e)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def load_json(cache_file):
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Error reading cache file %s: %s", cache_file, e)
    return {}


def is_valid_url(url):
    """Validate URL format and prevent basic SSRF targets."""
    if not re.match(r"^https?:\/\/", url):
        return False
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False
    forbidden_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}
    if hostname.lower() in forbidden_hosts:
        return False
    return True


def fetch_and_cache(url, cache_dir, client_headers=None, timeout=(3, 10)):
    cache_file = cache_path(url, cache_dir)
    headers = {}

    if client_headers is None:
        data = load_json(cache_file)
        headers = data.get("request_headers", {})
    else:
        headers = dict(client_headers)

    headers.setdefault("User-Agent", "RSSMixerProxy/1.0")
    headers.pop("Host", None)

    if not is_valid_url(url):
        logger.error("Invalid or restricted URL path: %s", url)
        return {
            "url": url,
            "request_headers": headers,
            "response_headers": {},
            "status_code": 400,
            "body": f"Invalid or restricted URL: {url}",
        }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        cache_content = {
            "url": url,
            "request_headers": headers,
            "response_headers": dict(response.headers),
            "status_code": response.status_code,
            "body": response.text,
        }

        if response.status_code == 200:
            safe_atomic_write_json(cache_file, cache_content)
            logger.info("Cached %s: %s in %s", response.status_code, url, cache_dir)
        else:
            logger.error("Failed to fetch %s: status %s", url, response.status_code)
            if not os.path.exists(cache_file):
                safe_atomic_write_json(cache_file, cache_content)
                logger.info(
                    "Cached error %s: %s in %s", response.status_code, url, cache_dir
                )
    except Exception as e:
        logger.error("Error fetching %s: %s", url, e)
        cache_content = {
            "url": url,
            "request_headers": headers,
            "response_headers": {},
            "status_code": 502,
            "body": str(e),
        }
        # Do not persist transient connection errors permanently to disk
    return cache_content


def refresh_cache(url, cache_dir, ttl):
    logger.info("Refresh cache for %s every %s seconds", url, ttl)
    try:
        while True:
            time.sleep(ttl)
            with LOCK:
                last_access = LAST_ACCESS_TIMES.get(url, time.time())
                if last_access + MAX_TTL_IN_CACHE < time.time():
                    cache_file = cache_path(url, cache_dir)
                    if os.path.exists(cache_file):
                        try:
                            os.remove(cache_file)
                        except OSError:
                            pass
                    LAST_ACCESS_TIMES.pop(url, None)
                    logger.warning("Remove %s from cached files due to inactivity", url)
                    return

            logger.info("Refresh cache for %s", url)
            fetch_and_cache(url, cache_dir)
    finally:
        with LOCK:
            ACTIVE_REFRESH_THREADS.discard(url)


def ensure_refresh_thread(url, cache_dir, ttl):
    """Ensure at most one background refresh thread runs per URL."""
    with LOCK:
        if url not in ACTIVE_REFRESH_THREADS:
            ACTIVE_REFRESH_THREADS.add(url)
            threading.Thread(
                target=refresh_cache, args=(url, cache_dir, ttl), daemon=True
            ).start()


def load_urls_from_cache(cache_dir):
    urls = []
    if not os.path.exists(cache_dir):
        return urls
    for file in os.listdir(cache_dir):
        if file.endswith(".json"):
            hash_file = os.path.join(cache_dir, file)
            data = load_json(hash_file)
            url = data.get("url", "")
            if url:
                logger.info("Load: %s from cache %s", url, hash_file)
                urls.append(url)
    return urls


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class CachingProxyHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, cache_dir=None, ttl=None, **kwargs):
        self.cache_dir = cache_dir
        self.ttl = ttl
        super().__init__(*args, **kwargs)

    def do_GET(self):
        url = self.path.lstrip("/").replace("\n", "").replace("\r", "")
        with LOCK:
            LAST_ACCESS_TIMES[url] = time.time()

        cache_file = cache_path(url, self.cache_dir)
        cache_content = load_json(cache_file)

        if cache_content:
            logger.info("Serving from cache: %s", url)
        else:
            logger.info("Fetching and caching: %s", url)
            client_headers = dict(self.headers)
            cache_content = fetch_and_cache(url, self.cache_dir, client_headers)
            ensure_refresh_thread(url, self.cache_dir, self.ttl)

        body_str = cache_content.get("body", "")
        body_bytes = body_str.encode("utf-8")
        status_code = cache_content.get("status_code", 500)

        self.send_response(status_code)
        response_headers = cache_content.get("response_headers", {})
        for header, value in response_headers.items():
            header_lower = header.lower()
            if header_lower in ("set-cookie", "content-length"):
                continue
            if header_lower in (
                "content-type",
                "cache-control",
                "etag",
                "last-modified",
            ):
                self.send_header(header, value)

        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, format, *args):
        logger.debug(
            "%s - - [%s] %s",
            self.address_string(),
            self.log_date_time_string(),
            format % args,
        )


def start_server(host, port, cache_dir, ttl):
    def handler(*args, **kwargs):
        return CachingProxyHandler(*args, cache_dir=cache_dir, ttl=ttl, **kwargs)

    with ThreadingHTTPServer((host, port), handler) as httpd:
        try:
            logger.info("Serving on http://%s:%s", host, port)
            httpd.serve_forever()
        finally:
            logger.info("Closing connection")
            httpd.shutdown()


@click.command()
@click.option("--host", default="127.0.0.1", help="Ip address to run the server on.")
@click.option("--port", default=8080, help="Port to run the server on.")
@click.option(
    "--cache-dir", default="./var/cache", help="Directory to store cached files."
)
@click.option("--ttl", default=3600, help="TTL for cache refresh in seconds.")
def main(host, port, cache_dir, ttl):
    os.makedirs(cache_dir, exist_ok=True)
    cached_urls = load_urls_from_cache(cache_dir)
    try:
        for url in cached_urls:
            ensure_refresh_thread(url, cache_dir, ttl)

        start_server(host, port, cache_dir, ttl)
    except KeyboardInterrupt:
        logger.info("Server stopped.")
    finally:
        logger.info("Closing connection")


if __name__ == "__main__":
    main()
