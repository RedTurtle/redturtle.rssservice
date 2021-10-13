# -*- coding: utf-8 -*-
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.restapi.testing import RelativeSession
from redturtle.rssservice.rss_mixer import FEED_DATA
from redturtle.rssservice.testing import (
    REDTURTLE_RSSSERVICE_API_FUNCTIONAL_TESTING,
)
from requests.exceptions import Timeout
from transaction import commit
from unittest import mock

import unittest

EXAMPLE_FEED_FOO = """
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<atom:link rel="self" type="application/rss+xml" href="http://test.com/RSS"></atom:link>
<title>RSS FOO</title>
  <link>http://test.com/RSS</link>
<language>en</language>
<item>
<title><![CDATA[Foo News 1]]></title>
<description><![CDATA[some description]]></description>
<link>http://test.com/foo-news-1</link>
<pubDate>Thu, 2 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/foo-news-1</guid>
</item>
<item>
<title><![CDATA[Foo News 2]]></title>
<description><![CDATA[some description 2]]></description>
<link>http://test.com/foo-news-2</link>
<pubDate>Thu, 1 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/foo-news-2</guid>
</item>
</channel>
</rss>
"""

EXAMPLE_FEED_BAR = """
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<atom:link rel="self" type="application/rss+xml" href="http://test.com/RSS"></atom:link>
<title>RSS BAR</title>
  <link>http://test.com/RSS</link>
<language>en</language>
<item>
<title><![CDATA[Bar News 1]]></title>
<description><![CDATA[some description]]></description>
<link>http://test.com/bar-news-1</link>
<pubDate>Thu, 2 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/bar-news-1</guid>
</item>
<item>
<title><![CDATA[Bar News 2]]></title>
<description><![CDATA[some description 2]]></description>
<link>http://test.com/bar-news-2</link>
<pubDate>Thu, 1 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/bar-news-2</guid>
</item>
</channel>
</rss>
"""

EXAMPLE_FEED_FOO_UPDATED = """
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<atom:link rel="self" type="application/rss+xml" href="http://test.com/RSS"></atom:link>
<title>RSS FOO</title>
  <link>http://test.com/RSS</link>
<language>en</language>
<item>
<title><![CDATA[Foo News 1 UPDATED]]></title>
<description><![CDATA[some description]]></description>
<link>http://test.com/foo-news-1</link>
<pubDate>Thu, 2 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/foo-news-1</guid>
</item>
<item>
<title><![CDATA[Foo News 2 UPDATED]]></title>
<description><![CDATA[some description 2]]></description>
<link>http://test.com/foo-news-2</link>
<pubDate>Thu, 1 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/foo-news-2</guid>
</item>
</channel>
</rss>
"""


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, text, status_code, reason=""):
            self.text = text
            self.content = text
            self.status_code = status_code
            self.reason = reason

        def text(self):
            return self.text

        def content(self):
            return self.content

    if args[0] == "http://foo.com/RSS":
        return MockResponse(text=EXAMPLE_FEED_FOO, status_code=200)
    if args[0] == "http://bar.com/RSS":
        return MockResponse(text=EXAMPLE_FEED_BAR, status_code=200)
    if args[0] == "http://test.com/timeout/RSS":
        raise Timeout
    return MockResponse(text="Not Found", status_code=404)


class RSSSMixerTest(unittest.TestCase):

    layer = REDTURTLE_RSSSERVICE_API_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer["app"]
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        self.api_session = RelativeSession(self.portal_url)
        self.api_session.headers.update({"Accept": "application/json"})
        self.api_session.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

        commit()

    def tearDown(self):
        # invalidate cache
        for feed in FEED_DATA.values():
            feed._last_update_time_in_minutes = 0
        self.api_session.close()

    def get_feed_data(self, query):
        response = self.api_session.post(
            "/@rss_mixer_data?block_id=rss-block", json=query
        )
        return response.json()

    def test_feeds_parameter_is_required(self):
        response = self.api_session.post("/@rss_mixer_data", json={"foo": "bar"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"], "Missing required parameter: feeds"
        )

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_single_result(self, mock_get):
        query = {"feeds": [{"url": "http://foo.com/RSS"}]}
        res = self.get_feed_data(query=query)
        self.assertEqual(len(res), 2)

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_mixed_result(self, mock_get):
        query = {
            "feeds": [
                {"url": "http://foo.com/RSS"},
                {"url": "http://bar.com/RSS"},
            ]
        }
        res = self.get_feed_data(query=query)
        self.assertEqual(len(res), 4)

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_results_are_sorted_by_date_descending(self, mock_get):
        query = {
            "feeds": [
                {"url": "http://foo.com/RSS"},
                {"url": "http://bar.com/RSS"},
            ]
        }
        res = self.get_feed_data(query=query)

        self.assertEqual(res[0]["title"], "Foo News 1")
        self.assertEqual(res[1]["title"], "Bar News 1")
        self.assertEqual(res[2]["title"], "Foo News 2")
        self.assertEqual(res[3]["title"], "Bar News 2")

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_return_source_info_in_feeds(self, mock_get):
        query = {
            "feeds": [
                {"url": "http://foo.com/RSS", "source": "Foo site"},
                {"url": "http://bar.com/RSS"},
            ],
        }

        res = self.get_feed_data(query=query)

        self.assertEqual(res[0]["source"], "Foo site")
        self.assertEqual(res[1]["source"], "")
        self.assertEqual(res[2]["source"], "Foo site")
        self.assertEqual(res[3]["source"], "")
