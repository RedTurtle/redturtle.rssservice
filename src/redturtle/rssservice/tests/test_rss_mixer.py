# -*- coding: utf-8 -*-
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.restapi.testing import RelativeSession
from redturtle.rssservice.testing import (
    REDTURTLE_RSSSERVICE_API_FUNCTIONAL_TESTING,
)
from requests.exceptions import Timeout
from plone import api
from unittest import mock
from transaction import commit

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

        self.doc = api.content.create(
            container=self.portal,
            type="Document",
            title="Doc",
            blocks={
                "non-rss-block": {"@type": "not-rss"},
                "rss-block": {
                    "@type": "rssBlock",
                    "feeds": [
                        {"url": "http://foo.com/RSS", "source": "Foo site"},
                        {"url": "http://bar.com/RSS"},
                    ],
                },
            },
        )

        self.api_session = RelativeSession(self.portal_url)
        self.api_session.headers.update({"Accept": "application/json"})
        self.api_session.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

        commit()

    def tearDown(self):
        self.api_session.close()

    def test_block_id_parameter_is_required(self):
        response = self.api_session.get("/doc/@get_rss_from_block")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"], "Missing required parameter: block_id"
        )

    def test_works_only_for_rssblocks(self):
        response = self.api_session.get(
            "/doc/@get_rss_from_block?block_id=non-rss-block"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"],
            'Block with id "non-rss-block" is not a RSS block, but "not-rss".',
        )

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_result(self, mock_get):
        response = self.api_session.get("/doc/@get_rss_from_block?block_id=rss-block")
        res = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(res), 4)

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_results_are_sorted_by_date_descending(self, mock_get):
        response = self.api_session.get("/doc/@get_rss_from_block?block_id=rss-block")
        res = response.json()

        self.assertEqual(res[0]["title"], "Foo News 1")
        self.assertEqual(res[1]["title"], "Bar News 1")
        self.assertEqual(res[2]["title"], "Foo News 2")
        self.assertEqual(res[3]["title"], "Bar News 2")

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_results_from_foo_have_the_source(self, mock_get):
        response = self.api_session.get("/doc/@get_rss_from_block?block_id=rss-block")
        res = response.json()

        self.assertEqual(res[0]["source"], "Foo site")
        self.assertEqual(res[1]["source"], "")
        self.assertEqual(res[2]["source"], "Foo site")
        self.assertEqual(res[3]["source"], "")

        response = self.api_session.get("/doc/@get_rss_from_block?block_id=rss-block")
