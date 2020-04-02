from plone.restapi.services import Service, _no_content_marker
from redturtle.rssservice import _
from zope.i18n import translate

import requests


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
        response = requests.get(feed)
        if response.status_code != 200:
            self.request.response.setStatus(response.status_code)
            message = response.text or response.reason
            return dict(
                error=dict(type="InternalServerError", message=message)
            )
        return {'data': response.text}
