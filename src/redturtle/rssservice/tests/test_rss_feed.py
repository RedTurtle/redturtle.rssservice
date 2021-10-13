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
from unittest import mock

import unittest

EXAMPLE_FEED = """
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<atom:link rel="self" type="application/rss+xml" href="http://test.com/RSS"></atom:link>
<title>RSS FOO</title>
  <link>http://test.com/RSS</link>
<language>en</language>
<item>
<title><![CDATA[Foo News]]></title>
<description><![CDATA[some description]]></description><link>http://test.com/foo</link><pubDate>Thu, 2 Apr 2020 10:44:01 +0200</pubDate>
<guid>http://test.com/foo</guid>
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

    if args[0] == "http://test.com/RSS":
        return MockResponse(text=EXAMPLE_FEED, status_code=200)
    if args[0] == "http://test.com/toomany/RSS":
        return MockResponse(text="Too Many Requests", status_code=429)
    if args[0] == "http://test.com/timeout/RSS":
        raise Timeout
    return MockResponse(text="Not Found", status_code=404)


class RSSSFeedTest(unittest.TestCase):

    layer = REDTURTLE_RSSSERVICE_API_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer["app"]
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()

        self.api_session = RelativeSession(self.portal_url)
        self.api_session.headers.update({"Accept": "application/rss+xml"})
        self.api_session.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def tearDown(self):
        self.api_session.close()

    def test_feed_parameter_is_required(self):
        response = self.api_session.get("/@get_rss_feed")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "Missing required parameter: feed")

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_not_found(self, mock_get):
        response = self.api_session.get(
            "/@get_rss_feed?feed=http://test.com/notfound/RSS"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, "Not Found")

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_error(self, mock_get):
        response = self.api_session.get(
            "/@get_rss_feed?feed=http://test.com/toomany/RSS"
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.text, "Too Many Requests")

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_result(self, mock_get):
        response = self.api_session.get("/@get_rss_feed?feed=http://test.com/RSS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, EXAMPLE_FEED)

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_feed_timeout(self, mock_get):
        response = self.api_session.get(
            "/@get_rss_feed?feed=http://test.com/timeout/RSS"
        )
        self.assertEqual(response.status_code, 408)
        self.assertEqual(
            response.text,
            "Unable to fetch RSS feed at this moment: timeout. Retry later.",
        )
