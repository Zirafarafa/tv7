# Overview

Convert tv7 http URLs to m3u and xmltv format, allowing timeshifting.

Compatible with tivimate and kodi.  Additional contributions welcome.

# Usage

Edit `config.yml`, and set `guide_url` and `catchup_redirect_url` to values
appropriate for your environment.

M3U URL to use is http://your.server/api/channels?app=<appname>

Note: appname currently can be one of `tivimate`, `kodi` or `testing`

EPG Url to use is http://your.server/api/guide?app=<appname>

Note: You can set this in your app manually, or in the config (`guide_url`).
In this case, the generated M3U will contain a link to the guide (`x-tvg-url`)


# Testing

First set up a python virtualenv, and run `pip install -r requirements.txt`

## Unit Tests

Run `pytest`

## Manual

File generation:
* Generate sample m3u and epg files using `python3 tv7.py <path to config>`

Web service:
* Start the server: `python3 app.py config-testing.yml`
* The following URLS are exposed:
  * /api/status
  * /api/channels?app=<app>
  * /api/guide?app=<app>
  * /api/catchup?channel=<channel_uuid>&start=<unix_timestamp>&duration=<seconds>

# Additional Info

## TV7 Web api

* curl https://api.tv.init7.net/api/tvchannel/ | jq .
* curl https://api.tv.init7.net/api/epg/?channel=781e3ee4-06fb-4cda-a367-469bd8e3cb5a | jq .
* curl 'https://api.tv.init7.net/api/replay/?epg_pk=9af29ebf-3d26-4993-802f-7383c5080d58' -o /tmp/file.m3u

## M3U format
* https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#supported-m3u-and-xmltv-elements
* https://siptv.eu/howto/playlist.html
* https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#catchup-format-specifiers
