# -*- coding: utf-8 -*-
from plone.restapi.services import Service
from time import time
from plone.restapi.search.utils import unflatten_dotted_dict
from zope.i18n import translate
from redturtle.rssservice import _
from zope.interface import implementer
from redturtle.rssservice.interfaces import IRSSMixerFeed
from requests.exceptions import RequestException
from requests.exceptions import Timeout
from DateTime import DateTime
from zExceptions import BadRequest
from plone.restapi.serializer.converters import json_compatible

import feedparser
import requests
import logging


logger = logging.getLogger(__name__)

# Accept these bozo_exceptions encountered by feedparser when parsing
# the feed:
ACCEPTED_FEEDPARSER_EXCEPTIONS = (feedparser.CharacterEncodingOverride,)

# store the feeds here (which means in RAM)
FEED_DATA = {}  # url: ({date, title, url, itemlist})


class GetRSSMixerService(Service):
    """
    Proxy route
    """

    def reply(self):
        query = self.request.form.copy()
        query = unflatten_dotted_dict(query)

        if "block_id" not in query:
            raise BadRequest(
                translate(
                    _(
                        "missing_block_id_parameter",
                        default="Missing required parameter: block_id",
                    ),
                    context=self.request,
                )
            )

        return self._getFeeds(block_id=query["block_id"], limit=query.get("limit", 20))

    def _getFeeds(self, block_id, limit=20):
        """Return all feeds"""
        feeds = []  # a list of feed objects
        blocks = getattr(self.context, "blocks", {})
        rss_block = blocks.get(block_id, None)
        if not rss_block:
            return []
        if rss_block.get("@type", "") != "rssBlock":
            raise BadRequest(
                translate(
                    _(
                        "block_id_wrong_type",
                        default='Block with id "{}" is not a RSS block, but "{}".'.format(
                            block_id, rss_block["@type"]
                        ),
                    ),
                    context=self.request,
                )
            )
        for feed_data in rss_block.get("feeds", []):
            url = feed_data.get("url", "")
            source = feed_data.get("source", "")

            feed = FEED_DATA.get(url, None)
            if feed is None:
                # create it
                feed = FEED_DATA[url] = RSSMixerFeed(
                    url=url,
                    source=source,
                    timeout=100,
                )
            # if it's new, populate it, else try to see if it need to be updated
            feed.update()
            feeds.append(feed)
        return self._sortedFeeds(feeds=feeds, limit=limit)

    def _sortedFeeds(self, feeds, limit):
        """Sort feed items by date"""

        itemsWithDate = []
        itemsWithoutDate = []
        for feed in feeds:
            for item in feed.items:
                if "updated" in item:
                    itemsWithDate.append(item)
                else:
                    itemsWithoutDate.append(item)
        sortedItems = sorted(itemsWithDate, key=lambda d: d["updated"], reverse=True)
        total = sortedItems + itemsWithoutDate

        # fix date format
        return total[:limit]


@implementer(IRSSMixerFeed)
class RSSMixerFeed(object):
    """An RSS feed."""

    FAILURE_DELAY = 10

    def __init__(self, url, source, timeout):
        self.url = url
        self.timeout = timeout
        self.source = source
        self._items = []
        self._title = ""
        self._siteurl = ""
        self._loaded = False  # is the feed loaded
        self._failed = False  # does it fail at the last update?
        self._last_update_time_in_minutes = 0  # when was the feed updated?
        self._last_update_time = None  # time as DateTime or Nonw

    @property
    def last_update_time_in_minutes(self):
        """Return the time the last update was done in minutes."""
        return self._last_update_time_in_minutes

    @property
    def last_update_time(self):
        """Return the time the last update was done in minutes."""
        return self._last_update_time

    @property
    def update_failed(self):
        return self._failed

    @property
    def ok(self):
        return not self._failed and self._loaded

    @property
    def loaded(self):
        """Return whether this feed is loaded or not."""
        return self._loaded

    @property
    def needs_update(self):
        """Check if this feed needs updating."""
        now = time() / 6
        return (self.last_update_time_in_minutes + self.timeout) < now

    def update(self):
        """Update this feed."""
        now = time() / 60  # time in minutes
        # check for failure and retry
        if self.update_failed:
            if (self.last_update_time_in_minutes + self.FAILURE_DELAY) < now:
                return self._retrieveFeed()
            else:
                return False

        # check for regular update
        if self.needs_update:
            return self._retrieveFeed()

        return self.ok

    def _getFeedFromUrl(self, url):
        """
        Use urllib to retrieve an rss feed.
        In this way, we can manage timeouts.
        """
        try:
            response = requests.get(url, timeout=5)
        except (Timeout, RequestException) as e:
            logger.exception(e)
            return None
        if response.status_code != 200:
            message = response.text or response.reason
            logger.error(
                "Unable to retrieve feed from {url}: {message}".format(
                    url=url, message=message
                )
            )
            return None
        return feedparser.parse(response.content)

    def _retrieveFeed(self):
        """Do the actual work and try to retrieve the feed."""
        url = self.url
        if url != "":
            self._last_update_time_in_minutes = time() / 60
            self._last_update_time = DateTime()
            parsed_feed = self._getFeedFromUrl(url)
            if not parsed_feed:
                self._loaded = True  # we tried at least but have a failed load
                self._failed = True
                return False
            if parsed_feed.bozo == 1 and not isinstance(
                parsed_feed.get("bozo_exception"),
                ACCEPTED_FEEDPARSER_EXCEPTIONS,
            ):
                self._loaded = True  # we tried at least but have a failed load
                self._failed = True
                return False
            self._title = parsed_feed.feed.title
            self._siteurl = parsed_feed.feed.link
            self._items = []

            for item in parsed_feed["items"]:
                try:
                    link = item.links[0]["href"]
                    itemdict = {
                        "title": item.title,
                        "url": link,
                        "summary": item.get("description", ""),
                        "source": self.source,
                    }
                    if getattr(item, "updated", None):
                        itemdict["updated"] = item.updated
                except AttributeError:
                    continue
                self._items.append(itemdict)
            self._loaded = True
            self._failed = False
            return True

        self._loaded = True
        self._failed = True  # no url set means failed
        # no url set, although that actually should not really happen
        return False

    @property
    def items(self):
        return self._items

    # convenience methods for displaying

    @property
    def feed_link(self):
        """Return rss url of feed for tile."""
        return self.url.replace("http://", "feed://")

    @property
    def title(self):
        """Return title of feed for tile."""
        return self._title

    @property
    def siteurl(self):
        """Return the link to the site the RSS feed points to."""
        return self._siteurl
