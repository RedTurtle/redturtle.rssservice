"""
This code implements a caching proxy server that stores and serves web content.

Key Components:
* Creates unique filenames for cached content using MD5 hashing
* Stores both the content and metadata (URL information) in separate files
* Background refresh content periodically

The Proxy Server:

* Listens for incoming requests (be awere to protect connection or leave the server listen only on localhost)
* Checks if requested content is in cache
* If found, serves from cache
* If not found, fetches it, saves it, then serves it

Background Refresh:

* Automatically updates cached content periodically
* Runs in separate threads to not block the main server
* Time between updates is configurable (TTL - Time To Live)

Command Line Interface : Uses Click library to accept parameters like:

Host address (default: 127.0.0.1)
Port number (default: 8080)
Cache directory location (default: ./var/cache)
TTL for cache refresh (default: 3600 seconds)

Usage Example :

```
rssmixer-proxy --host 127.0.0.1 --port 8080 --cache-dir ./var/cache --ttl 3600
```

XXX: this is not actually a real HTTP/HTTPS proxy because needs to act as man-in-the-middle

Usage:

```
import requests

RSSMIXER_PROXY = "http://127.0.0.1:8080"
url = "https://abcnews.go.com/abcnews/usheadlines"
res = requests.get(f{RSS_MIXER_PROXY}/{url}")
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


# this is not thtread-safe, but we don't care about it !
LAST_ACCESS_TIMES = {}
MAX_TTL_IN_CACHE = 7 * 24 * 3600  # 1 week

logger = logging.getLogger("rssmixer-proxy")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


# Function to calculate cache file path based on URL
def cache_path(url, cache_dir):
    hash_url = hashlib.md5(url.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{hash_url}.json")


def load_json(cache_file):
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return {}


def fetch_and_cache(url, cache_dir, client_headers=None, timeout=(1, 10)):
    cache_file = cache_path(url, cache_dir)
    try:
        # Send the request to the server
        if client_headers is None:
            data = load_json(cache_file)
            headers = data.get("request_headers", {})
        else:
            headers = client_headers
        if "User-Agent" not in headers:
            headers["User-Agent"] = "RSSMixerProxy/1.0"
        if "Host" in headers:
            del headers["Host"]
        # Validate the URL
        if not re.match(r"^https?:\/\/", url):
            raise ValueError(f"Invalid URL path: {url}")
        response = requests.get(url, headers=headers, timeout=timeout)
        # Store the response in the cache
        if response.status_code == 200:
            cache_content = {
                "url": url,
                "request_headers": headers,
                "response_headers": dict(response.headers),
                "status_code": response.status_code,
                "body": response.text,
            }
            # TODO: update file only if changed ?
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_content, f, indent=2)
            logger.info("Cached %s: %s in %s", response.status_code, url, cache_dir)
        else:
            logger.error("Failed to fetch $s: %s", url, response.status_code)
            cache_content = {
                "url": url,
                "request_headers": headers,
                "response_headers": dict(response.headers),
                "status_code": response.status_code,
                "body": response.text,
            }
            if not os.path.exists(cache_file):
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_content, f, indent=2)
                logger.info(
                    "Cached error %s: %s in %s", response.status_code, url, cache_dir
                )
    except Exception as e:
        logger.error("Error fetching %s: %s", url, e)
        cache_content = {
            "url": url,
            "request_headers": headers,
            "response_headers": {},
            "status_code": 500,
            "body": str(e),
        }
        if not os.path.exists(cache_file):
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_content, f, indent=2)
            logger.info("Cached error: %s in %s", url, cache_dir)
    return cache_content


# Background thread to refresh cache
def refresh_cache(url, cache_dir, ttl):
    logger.info(f"Refresh cache for {url} every {ttl} seconds")
    while True:
        time.sleep(ttl)
        if url not in LAST_ACCESS_TIMES:
            LAST_ACCESS_TIMES[url] = time.time()
        else:
            if LAST_ACCESS_TIMES[url] + MAX_TTL_IN_CACHE < time.time():
                cache_file = cache_path(url, cache_dir)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                logger.warning("Remove %s from cached files", url)
                return
        logger.info("Refresh cache for %s", url)
        fetch_and_cache(url, cache_dir)


# Load URLs to cache from existing .url files
def load_urls_from_cache(cache_dir):
    urls = []
    for file in os.listdir(cache_dir):
        if file.endswith(".json"):
            hash_file = os.path.join(cache_dir, file)
            try:
                # Extract original URL from the cached file
                data = json.load(open(hash_file, "r", encoding="utf-8"))
                url = data.get("url", "")
                if url:
                    logger.info("Load: %s from cache %s", url, hash_file)
                    urls.append(url)
            except Exception as e:
                logger.info("Error reading cached file %s: %s", file, e)
    return urls


# HTTP proxy handler
class CachingProxyHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, cache_dir=None, ttl=None, **kwargs):
        self.cache_dir = cache_dir
        self.ttl = ttl
        super().__init__(*args, **kwargs)

    def do_GET(self):

        url = self.path.lstrip("/").replace("\n").replace("\r")
        LAST_ACCESS_TIMES[url] = time.time()
        cache_file = cache_path(url, self.cache_dir)

        # Check if the page is already cached
        if os.path.exists(cache_file):
            logger.info("Serving from cache: %s", url)
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_content = json.load(f)
        else:
            logger.info("Fetching and caching: %s", url)
            client_headers = dict(self.headers)
            cache_content = fetch_and_cache(url, self.cache_dir, client_headers)
            threading.Thread(
                target=refresh_cache, args=(url, self.cache_dir, self.ttl), daemon=True
            ).start()

        # Send response
        self.send_response(cache_content["status_code"])
        for header, value in cache_content["response_headers"].items():
            if header.lower() in ("set-cookie", "content-length"):
                continue
            if header.lower() in ("content-type", "cache-control"):
                self.send_header(header, value)
                continue
            # logger.info("skip header", header, value)
        self.send_header("Content-Length", len(cache_content["body"].encode("utf-8")))
        self.end_headers()
        self.wfile.write(cache_content["body"].encode("utf-8"))


# Start the server
def start_server(host, port, cache_dir, ttl):
    def handler(*args, **kwargs):
        return CachingProxyHandler(*args, cache_dir=cache_dir, ttl=ttl, **kwargs)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, port), handler) as httpd:
        try:
            logger.info("Serving on http://%s:%s", host, port)
            httpd.serve_forever()
        finally:
            logger.info("Closing connection")
            httpd.shutdown()
            # con.shutdown(socket.SHUT_RDWR)
            # httpd.close()


@click.command()
@click.option("--host", default="127.0.0.1", help="Ip address to run the server on.")
@click.option("--port", default=8080, help="Port to run the server on.")
@click.option(
    "--cache-dir", default="./var/cache", help="Directory to store cached files."
)
@click.option("--ttl", default=3600, help="")
def main(host, port, cache_dir, ttl):
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)

    # Load URLs from cache directory and start refresh threads
    cached_urls = load_urls_from_cache(cache_dir)
    try:
        for url in cached_urls:
            threading.Thread(
                target=refresh_cache, args=(url, cache_dir, ttl), daemon=True
            ).start()

        # Start the proxy server
        start_server(host, port, cache_dir, ttl)
    except KeyboardInterrupt:
        logger.info("Server stopped.")
    finally:
        logger.info("Closing connection")


if __name__ == "__main__":
    main()
