# -*- coding: utf-8 -*-
from zope.interface import Interface


class IRSSMixerFeed(Interface):
    def __init__(url, source, timeout):
        """Initialize the feed with the given url. will not automatically load
        if timeout defines the time between updates in minutes.
        """

    def loaded():
        """Return if this feed is in a loaded state."""

    def title():
        """Return the title of the feed."""

    def items():
        """Return the items of the feed."""

    def feed_link():
        """Return the url of this feed in feed:// format."""

    def site_url():
        """Return the URL of the site."""

    def last_update_time_in_minutes():
        """Return the time this feed was last updated in minutes since epoch."""

    def last_update_time():
        """Return the time the feed was last updated as DateTime object."""

    def needs_update():
        """return if this feed needs to be updated."""

    def update():
        """Update this feed. will automatically check failure state etc.
        returns True or False whether it succeeded or not.
        """

    def update_failed():
        """Return if the last update failed or not."""

    def ok():
        """Is this feed ok to display?"""
