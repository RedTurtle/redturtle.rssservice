.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

=====================
Redturtle RSS Service
=====================

.. image:: https://travis-ci.com/collective/collective.volto.cookieconsent.svg?branch=master
    :target: https://travis-ci.com/collective/collective.volto.cookieconsent

This package add support to retrieve RSS feeds from external sources.

Usage
=====

RSS proxy
---------

There is a service "**@get_rss_feed**" that is used as proxy to call an
RSS feed from backend and not from frontend to avoid CORS problems.

The service will reply with an "application/rss+xml" response with the desired feed.

Each feed url has a 10 minutes cache for his result to avoid too much requests.

You can call the endpoint passing a *feed* parameter like this example::

    > curl -i http://localhost:8080/Plone/@get_rss_feed?feed=https://www.plone.org/RSS -H 'Accept: application/rss+xml'


RSS block
---------

There is a service "**@rss_mixer_data**" that accept a list of sources and limit, and return a list of sorted feeds by date.

This service only accept POST calls and accept following parameters:

- limit: the number of items to show (default 20)
- feeds: a list of objects like this: {"url": "url-of-the-feed", "source": "A custom label"}

For example::

    > curl -i -X POST http://localhost:8080/Plone/@rss_mixer_data -H 'Accept: application/json' -H 'Content-Type: application/json' --data-raw '{"limit":5, "feeds": [{"url": "url-of-the-feed", "source": "A custom label"}]}'


Will reply with something like this::

    [
        {
            "source": "Foo site",
            "contentSnippet": "some description 2",
            "title": "Foo News 2",
            "date": "Thu, 1 Apr 2020 10:44:01 +0200",
            "url": "http://test.com/foo-news-2"
        },
        {
            "source": "",
            "contentSnippet": "some description 2",
            "title": "Bar News 2",
            "date": "Thu, 1 Apr 2020 10:44:01 +0200",
            "url": "http://test.com/bar-news-2"
        },
        {
            "source": "Foo site",
            "contentSnippet": "some description",
            "title": "Foo News 1",
            "date": "Thu, 2 Apr 2020 10:44:01 +0200",
            "url": "http://test.com/foo-news-1"
        },
        {
            "source": "",
            "contentSnippet": "some description",
            "title": "Bar News 1",
            "date": "Thu, 2 Apr 2020 10:44:01 +0200",
            "url": "http://test.com/bar-news-1"
        }
    ]

This endpoint works with `volto-rss-block <https://github.com/RedTurtle/volto-rss-block/>`_ plugin.

Installation
============

Install redturtle.rssservice by adding it to your buildout::

    [buildout]

    ...

    eggs =
        redturtle.rssservice


and then running ``bin/buildout``


Contribute
==========

- Issue Tracker: https://github.com/RedTurtle/redturtle.rssservice/issues
- Source Code: https://github.com/RedTurtle/redturtle.rssservice


Support
=======

If you are having issues, please let us know.
We have a mailing list located at: sviluppo@redturtle.it


License
=======

The project is licensed under the GPLv2.
