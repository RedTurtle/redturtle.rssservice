.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

=====================
Redturtle RSS Service
=====================

.. image:: https://travis-ci.com/collective/collective.volto.cookieconsent.svg?branch=master
    :target: https://travis-ci.com/collective/collective.volto.cookieconsent

This package contains a service: "@get_rss_feed" that is used as proxy to call an
RSS feed from backend and not from frontend to avoid CORS problems.

The service will reply with an "application/rss+xml" response with the desired feed.

Each feed url has a 10 minutes cache for his result to avoid too much requests.

Usage
-----

You can call the endpoint passing a *feed* parameter like this example::

    > curl -i http://localhost:8080/Plone/@get_rss_feed?feed=https://www.plone.org/RSS -H 'Accept: application/rss+xml'


Installation
------------

Install redturtle.rssservice by adding it to your buildout::

    [buildout]

    ...

    eggs =
        redturtle.rssservice


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/RedTurtle/redturtle.rssservice/issues
- Source Code: https://github.com/RedTurtle/redturtle.rssservice


Support
-------

If you are having issues, please let us know.
We have a mailing list located at: sviluppo@redturtle.it


License
-------

The project is licensed under the GPLv2.
