from plone.restapi.services import Service, _no_content_marker
import requests


class GetRSSFeedService(Service):

    content_type = "application/rss+xml"

    error_message = "Unable to get rss"

    def render(self):

        self.check_permission()
        content = self.reply()
        if content is not _no_content_marker:
            self.request.response.setHeader("Content-Type", self.content_type)
            return content

    def reply(self):

        form = self.request.form
        if not form.get("feed", None):
            self.request.response.setStatus(500)
            return dict(
                error=dict(
                    type="InternalServerError",
                    message=self.error_message
                )
            )
        response = requests.get(form.get("feed"))
        if response.status_code != 200:
            self.request.response.setStatus(500)
            return dict(
                error=dict(
                    type="InternalServerError",
                    message=self.error_message
                )
            )
        return response._content
