# -*- coding: utf-8 -*-
import importlib
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

main = importlib.import_module("redturtle.rssservice.proxycacheserver.main")


class ProxyCacheServerTest(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        main.ACTIVE_REFRESH_THREADS.clear()
        main.LAST_ACCESS_TIMES.clear()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        main.ACTIVE_REFRESH_THREADS.clear()
        main.LAST_ACCESS_TIMES.clear()

    def test_cache_path(self):
        url = "https://example.com/rss.xml"
        path = main.cache_path(url, self.test_dir)
        self.assertTrue(path.startswith(self.test_dir))
        self.assertTrue(path.endswith(".json"))

    def test_safe_atomic_write_and_load_json(self):
        file_path = os.path.join(self.test_dir, "test.json")
        data = {"url": "https://example.com/rss", "status_code": 200, "body": "OK"}
        main.safe_atomic_write_json(file_path, data)

        loaded = main.load_json(file_path)
        self.assertEqual(loaded, data)
        # Ensure no temporary file left
        files = os.listdir(self.test_dir)
        self.assertEqual(files, ["test.json"])

    def test_is_valid_url(self):
        self.assertTrue(main.is_valid_url("https://example.com/feed"))
        self.assertTrue(main.is_valid_url("http://news.google.com/rss"))
        self.assertFalse(main.is_valid_url("ftp://example.com"))
        self.assertFalse(main.is_valid_url("http://localhost:8080"))
        self.assertFalse(main.is_valid_url("http://127.0.0.1/admin"))
        self.assertFalse(main.is_valid_url("http://169.254.169.254/latest/meta-data/"))

    def test_ensure_refresh_thread_deduplication(self):
        url = "https://example.com/feed"
        with mock.patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = mock.MagicMock()
            mock_thread_cls.return_value = mock_thread_instance

            main.ensure_refresh_thread(url, self.test_dir, ttl=60)
            self.assertIn(url, main.ACTIVE_REFRESH_THREADS)
            self.assertEqual(mock_thread_cls.call_count, 1)

            # Second call for the same URL should be deduplicated
            main.ensure_refresh_thread(url, self.test_dir, ttl=60)
            self.assertEqual(mock_thread_cls.call_count, 1)

    @mock.patch("requests.get")
    def test_fetch_and_cache_success(self, mock_requests_get):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/rss+xml"}
        mock_response.text = "<rss><channel><title>Test Feed</title></channel></rss>"
        mock_requests_get.return_value = mock_response

        url = "https://example.com/rss"
        result = main.fetch_and_cache(url, self.test_dir)

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["body"], mock_response.text)

        # Check cached file
        cache_file = main.cache_path(url, self.test_dir)
        self.assertTrue(os.path.exists(cache_file))
        loaded = main.load_json(cache_file)
        self.assertEqual(loaded["status_code"], 200)

    @mock.patch("requests.get")
    def test_fetch_and_cache_connection_error_not_persisted(self, mock_requests_get):
        mock_requests_get.side_effect = Exception("Connection refused")

        url = "https://example.com/failing_rss"
        result = main.fetch_and_cache(url, self.test_dir)

        self.assertEqual(result["status_code"], 502)
        cache_file = main.cache_path(url, self.test_dir)
        self.assertFalse(os.path.exists(cache_file))
