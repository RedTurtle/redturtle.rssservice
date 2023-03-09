.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

.. image:: https://img.shields.io/pypi/v/redturtle.rssservice.svg
    :target: https://pypi.org/project/redturtle.rssservice/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/redturtle.rssservice.svg?style=plastic
    :target: https://pypi.org/project/redturtle.rssservice/
    :alt: Supported - Python Versions

.. image:: https://img.shields.io/pypi/dm/redturtle.rssservice.svg
    :target: https://pypi.org/project/redturtle.rssservice/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/pypi/l/redturtle.rssservice.svg
    :target: https://pypi.org/project/redturtle.rssservice/
    :alt: License

.. image:: https://github.com/RedTurtle/redturtle.rssservice/actions/workflows/test.yml/badge.svg
    :target: https://github.com/RedTurtle/redturtle.rssservice/actions
    :alt: Tests

.. image:: https://coveralls.io/repos/github/RedTurtle/redturtle.rssservice/badge.svg?branch=master
    :target: https://coveralls.io/github/RedTurtle/redturtle.rssservice?branch=master
    :alt: Coverage

=====================
Redturtle RSS Service
=====================

This package add support to retrieve RSS feeds from external sources.

Usage
=====


RSS block
---------

There is a service "**@rss_mixer_data**" that accept a block id, and return a list of sorted feeds by date.

This service only accept GET calls and accept following parameters:

- block: the id of the rssBlock with the feeds

The endpoint should be called on the context that has the rssBlock that you want to show.


For example::

    > curl -i -X GET http://localhost:8080/Plone/example-page/@rss_mixer_data?block=123456789 -H 'Accept: application/json' -H 'Content-Type: application/json'


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

Retrieve timeout
----------------

There is a 5s default timeout for retrieve RSS feeds.

You can override it with an environment variable: **RSS_SERVICE_TIMEOUT**

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
