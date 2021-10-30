# Overview

Convert tv7 http URLs to m3u and xmltv format, allowing timeshifting.

Compatible with tivimate and kodi.  Additional contributions welcome.

Edit `config.yml`, and set `guide_url` and `catchup_redirect_url` to values
appropriate for your environment.

M3U URL to use is http://your.server/api/channels?app=<appname>

Note: appname currently can be one of `tivimate`, `kodi` or `testing`

EPG Url to use is http://your.server/api/guide?app=<appname>

Note: You can set this in your app manually, or in the config (`guide_url`).
In this case, the generated M3U will contain a link to the guide (`x-tvg-url`)


# Testing

File generation:
* Set up a python virtualenv, and run `pip install -r requirements.txt`
* Generate sample m3u and epg files using `python3 tv7.py <path to config>`

Web service:
* Start the server: `python3 app.py config-testing.yml`
* The following URLS are exposed:
  * /api/status
  * /api/channels?app=<app>
  * /api/guide?app=<app>
  * /api/catchup?channel=<channel_uuid>&start=<unix_timestamp>&duration=<seconds>


