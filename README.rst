.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

====================
redturtle.rssservice
====================

This package contains a simple service: "@get_rss_feed".
It's used as proxy to call rss feed from backend and not
from frontend to avoid CORS

The service will return the string with the rss feed

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

- Issue Tracker: https://github.com/collective/redturtle.rssservice/issues
- Source Code: https://github.com/collective/redturtle.rssservice
- Documentation: https://docs.plone.org/foo/bar


Support
-------

If you are having issues, please let us know.
We have a mailing list located at: sviluppo@redturtle.it


License
-------

The project is licensed under the GPLv2.
