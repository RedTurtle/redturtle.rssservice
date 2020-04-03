# -*- coding: utf-8 -*-
from plone.memoize import ram
from plone.restapi.services import Service
from redturtle.rssservice import _
from requests.exceptions import RequestException
from requests.exceptions import Timeout
from time import time
from zope.i18n import translate

import logging
import requests


logger = logging.getLogger(__name__)


def _feed_cachekey(method, self, feed):
    """
    method for ramcache that store time and feed url.
    Cache time is 10 minutes
    """
    timestamp = time() // (60 * 10 * 1)
    return '{timestamp}:{feed}'.format(timestamp=timestamp, feed=feed)


class GetRSSFeedService(Service):
    """
    Proxy route
    """

    content_type = "application/rss+xml"

    error_message = "Unable to get rss"

    def render(self):

        self.check_permission()
        content = self.reply()
        if content.get('error', {}):
            self.request.response.setHeader("Content-Type", self.content_type)
            return content['error'].get('message')
        self.request.response.setHeader("Content-Type", self.content_type)
        return content.get('data', '')

    def reply(self):
        feed = self.request.form.get('feed', '')
        if not feed:
            self.request.response.setStatus(400)
            return dict(
                error=dict(
                    type="BadRequest",
                    message=translate(
                        _(
                            'missing_feed_parameter',
                            default='Missing required parameter: feed',
                        ),
                        context=self.request,
                    ),
                )
            )

        rss_feed = self.fetch_feed(feed=feed)
        if 'error' in rss_feed:
            self.request.response.setStatus(rss_feed['error'].get('code', 500))
        return rss_feed

    @ram.cache(_feed_cachekey)
    def fetch_feed(self, feed):
        try:
            response = requests.get(feed, timeout=10)
        except Timeout as e:
            logger.exception(e)
            return dict(
                error=dict(
                    code='408',
                    type='Timeout',
                    message=translate(
                        _(
                            'request_timeout',
                            default='Unable to fetch RSS feed at this moment: timeout. Retry later.',  # noqa
                        ),
                        context=self.request,
                    ),
                )
            )
        except RequestException as e:
            logger.exception(e)
            return dict(
                error=dict(
                    code='500',
                    type='InternalServerError',
                    message=translate(
                        _(
                            'request_error',
                            default='Unable to fetch RSS feed. Retry later.',
                        ),
                        context=self.request,
                    ),
                )
            )
        if response.status_code != 200:
            message = response.text or response.reason
            return dict(
                error=dict(
                    code=response.status_code,
                    type="InternalServerError",
                    message=message,
                )
            )
        return {'data': response.content}
