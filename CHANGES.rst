Changelog
=========

2.2.1 (unreleased)
------------------

- Handle case when feed url is an internal url with resolveuid.
  [cekk]
- Do not print exception on log, but use warning because it's handled.
  [cekk]

2.2.0 (2023-03-21)
------------------

- Allow configuring the User-Agent for the requests to get feeds,
  via the REQUESTS_USER_AGENT environment variable.
  [davisagli]


2.1.0 (2023-03-10)
------------------

- Customizable timeout.
  [cekk]
- Return 404 if block not found instead BadRequest.
  [cekk]
- Handle site root blocks in plone 6.
  [cekk]


2.0.0 (2022-04-07)
------------------

- Remove unused and unsafe endpoint.
  [cekk]
- Now @rss_mixer_data accept GET calls (see README for more infos).
  [cekk]


1.0.3 (2022-03-22)
------------------

- Allow to use cateogry in rss feed.
  [lucabel]


1.0.2 (2022-03-04)
------------------

- Allow dates with wrong date format (eg. a date range)
  [lucabel]


1.0.1 (2021-12-02)
------------------

- Fix python version in setup.py
  [cekk]

1.0.0 (2021-10-13)
------------------

- Add @rss_mixer_data endpoint.
  [cekk]


0.1.0 (2020-04-08)
------------------

- Initial release.
  [cekk]
