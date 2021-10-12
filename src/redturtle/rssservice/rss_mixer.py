# -*- coding: utf-8 -*-
from plone.restapi.serializer.converters import json_compatible
from DateTime import DateTime
from plone.restapi.services import Service
from redturtle.rssservice import _
from redturtle.rssservice.interfaces import IRSSMixerFeed
from requests.exceptions import RequestException
from requests.exceptions import Timeout
from time import time
from zExceptions import BadRequest
from zope.i18n import translate
from zope.interface import implementer
from plone.restapi.deserializer import json_body

import feedparser
import requests
import logging


logger = logging.getLogger(__name__)

# Accept these bozo_exceptions encountered by feedparser when parsing
# the feed:
ACCEPTED_FEEDPARSER_EXCEPTIONS = (feedparser.CharacterEncodingOverride,)

# store the feeds here (which means in RAM)
FEED_DATA = {}  # url: ({date, title, url, itemlist})


class POSTRSSMixerService(Service):
    """ """

    def reply(self):
        query = json_body(self.request)

        limit = query.get("limit", 20)
        feeds = query.get("feeds", [])
        if not feeds:
            raise BadRequest(
                translate(
                    _(
                        "missing_feeds_parameter",
                        default="Missing required parameter: feeds",
                    ),
                    context=self.request,
                )
            )
        return self._getFeeds(feeds=feeds, limit=limit)

    def _getFeeds(self, feeds, limit=20):
        """Return all feeds"""
        data = []
        for feed_data in feeds:
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
            else:
                # check if we need to update the source
                if feed.source != source:
                    feed.source = source
            feed.update()
            data.append(feed)
        return self._sortedFeeds(feeds=data, limit=limit)

    def _sortedFeeds(self, feeds, limit):
        """Sort feed items by date"""

        itemsWithDate = []
        itemsWithoutDate = []
        for feed in feeds:
            for item in feed.items:
                if "date" in item:
                    itemsWithDate.append(item)
                else:
                    itemsWithoutDate.append(item)
        sortedItems = sorted(itemsWithDate, key=lambda d: d["date"], reverse=True)
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
        if not url:
            self._loaded = True
            self._failed = True  # no url set means failed
            # no url set, although that actually should not really happen
            return False
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
            itemdict = {
                "title": item.title,
                "url": item.get("link", ""),
                "contentSnippet": item.get("description", ""),
                "source": getattr(self, "source", ""),
            }

            date = self.get_item_date(item=item)
            if date:
                itemdict["date"] = date

            image = self.get_item_image(item=item)
            if image:
                # format needed in blocks to keep compatibility
                itemdict["enclosure"] = image

            self._items.append(itemdict)
        self._loaded = True
        self._failed = False
        return True

    def get_item_date(self, item):
        if getattr(item, "updated", None):
            return json_compatible(DateTime(item.updated))
        elif getattr(item, "published", None):
            return json_compatible(DateTime(item.published))
        return ""

    def get_item_image(self, item):
        image = ""
        if item.get("media_thumbnail", []):
            image = item["media_thumbnail"][0].get("url", "")
        elif item.get("media_content", []):
            images = [
                x.get("url", "")
                for x in item.media_content
                if x.get("medium", "") == "image"
            ]
            if images:
                image = images[0]
        elif item.get("links", []):
            images = [
                x.get("url", "")
                for x in item.links
                if x.get("rel", "") == "enclosure" and "image" in x.get("type", "")
            ]
            if images:
                image = images[0]
        if not image:
            return {}
        return {"url": image}

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
