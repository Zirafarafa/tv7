"""Generate m3u and epg from tv7 api."""
import time
import collections
import logging
import datetime
import sys
import re

import tzlocal
import pytz
from requests_cache import CachedSession

import yaml

from lxml import etree as ET

import dateutil.parser

class TV7:
  def __init__(self, config=None):
    self.channels = None
    self.all_channels = None

    self.guide = {}

    self.config = config

    self.guide_url = self.config.get('guide_url', 'http://localhost')
    self.guide_append_app = self.config.get('guide_append_app', False)
    self.update_interval = self.config.get('update_interval', 3600)
    self.catchup_days = self.config.get('catchup_days', 7)
    self.include_channels = self.config.get('include_channels', None)
    self.catchup_redirect_url = self.config.get('catchup_redirect_url', None)
    self.cache_path = self.config.get('cache_path', 'tv7_cache')
    self.udpxy_address = self.config.get('udpxy_address', None)
    self.use_epg_for_channels = self.config.get('use_epg_for_channels', False)

    self._last_update = 0

    self.catchup_url='https://api.tv.init7.net/api/replay/'
    self.channel_url='https://api.tv.init7.net/api/tvchannel/'
    self.epg_url='https://api.tv.init7.net/api/epg/'

    self.session = CachedSession(cache_control=True, cache_name=self.cache_path, expire_after=14400)

  def api_get(self, url):
    d = []

    current_url = url
    while current_url:
      r = self.session.get(current_url)
      j = r.json()
      d.extend(j['results'])
      current_url = j['next']

    return d

  def read_channels(self):
    self.all_channels = self.api_get(self.channel_url)
    if not self.include_channels:
      self.channels = self.all_channels
    else:
      c = []
      channel_by_name = {chan['canonical_name']: chan for chan in self.all_channels}
      for channel_name in self.include_channels:
        if channel_name in channel_by_name:
          c.append(channel_by_name[channel_name])
      self.channels = c

  def read_epg_for_channel(self, channel_id):
    url = f'{self.epg_url}?channel={channel_id}'
    return self.api_get(url)

  def update_using_epg(self):
    all_epg = self.api_get(self.epg_url)
    logging.info('Got full EPG')

    channels = {}
    for item in all_epg:
      c = item['channel']
      channel_id = c['pk']

      if channel_id not in channels:
        channel_name = c['canonical_name']
        if not self.include_channels or channel_name in self.include_channels:
          channels[channel_id] = c

    self.channels = channels.values()

    guide = collections.defaultdict(list)
    for item in all_epg:
      channel_id = item['channel']['pk']
      if channel_id not in channels:
        continue

      guide[channel_id].append(item)






  def update(self, force=False):
    if not force and time.time() - self._last_update < self.update_interval:
      return

    if self.use_epg_for_channels:
      logging.info(">> Using EPG for channel data")
      self.update_using_epg()
      return

    logging.info(">> Getting all channels")
    self.read_channels()

    logging.info(">> Getting all EPGs")
    for c in self.channels:
      epg_list = self.read_epg_for_channel(c['pk'])
      self.guide[c['pk']] = epg_list

    self._last_update = time.time()

  def get_catchup_url(self, channel, start, duration):
    # Desired format
    # https://tv7api2.tv.init7.net/api/replay/?channel={channel_pk}&start={start}&stop={stop}

    url = self.catchup_url

    stop = start + duration
    start_str = self._format_date(start, informat='unix', outformat='iso8601')
    stop_str = self._format_date(stop, informat='unix', outformat='iso8601')

    url += f'?channel={channel}&start={start_str}&stop={stop_str}'

    return url


  def _xml_add_channel_element(self, chan, chan_id, xml, xml_id, **kwargs):
    if chan_id in chan and chan[chan_id]:
      ET.SubElement(xml, xml_id, **kwargs).text = str(chan[chan_id])

  def _format_date(self, d, informat, outformat):
    # In format: 2021-05-17T23:05:00Z
    # Out format: 20080715003000 -0600
    ts = None
    if informat == 'iso8601':
      ts = dateutil.parser.isoparse(d)

    if informat == 'unix':
      ts = datetime.datetime.utcfromtimestamp(d)

    if outformat == 'xmltv':
      return ts.strftime('%Y%m%d%H%M%S')

    if outformat == 'iso8601':
      return ts.isoformat()+'Z'

  def _xml_add_channel(self, tv, chan, app):
    chan_id = chan['canonical_name']
    pk = chan['pk']

    c = ET.SubElement(tv, 'channel', id=chan_id)
    ET.SubElement(c, 'icon', src=chan['logo'])
    ET.SubElement(c, 'display-name').text = chan['name']
    ET.SubElement(c, 'display-name').text = chan['canonical_name']

    for prog in self.guide[pk]:
      programme_attrs = {
        'start': self._format_date(prog['timeslot']['lower'], informat='iso8601', outformat='xmltv'),
        'stop': self._format_date(prog['timeslot']['upper'], informat='iso8601', outformat='xmltv'),
        'channel': chan_id,
      }
      if app == 'kodi':
        programme_attrs['catchup-id'] = prog['pk']

      p = ET.SubElement(tv,'programme', programme_attrs)

      self._xml_add_channel_element(prog, 'title', p, 'title')
      self._xml_add_channel_element(prog, 'desc', p, 'desc')
      for cat in prog['categories']:
        ET.SubElement(p, 'category').text = cat

      self._xml_add_channel_element(prog, 'sub_title', p, 'sub-title')
      self._xml_add_channel_element(prog, 'date', p, 'date')

      if 'episode_num_system' in prog and prog['episode_num_system'] == 'xmltv_ns':
        self._xml_add_channel_element(prog, 'date', p, 'date', system='xmltv_ns')

      for icon in prog['icons']:
        ET.SubElement(p, 'icon', src=icon)

  def get_epg(self, app):

    # http://wiki.xmltv.org/index.php/XMLTVFormat

    tv = ET.Element('tv')
    tv.attrib['source-info-url'] = self.channel_url
    tv.attrib['source-info-name'] = 'Blah'

    for c in self.channels:
      self._xml_add_channel(tv, c, app)

    data = ET.tostring(tv, pretty_print=True, xml_declaration=True, encoding="UTF-8", doctype='<!DOCTYPE tv SYSTEM "xmltv.dtd">')
    return data

  def get_m3u(self, app):
    # https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#catchup-format-specifiers
    lines = []

    app_params = ''
    if self.guide_append_app:
      app_params=f'?app={app}'

    lines.append(f'#EXTM3U tvg-shift="0" x-tvg-url="{self.guide_url}{app_params}" catchup-correction="0"')

    # Sample
    # #EXTINF:0 tvg-logo="https://api.tv.init7.net/media/logos/orf1_hd.png" tvg-name="ORF1.at" group-title="de", ORF1 HD
    # udp://@239.77.0.109:5000


    # https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#supported-m3u-and-xmltv-elements
    # http://niklabs.com/catchup-settings/
    for c in self.channels:
      line = f'#EXTINF:-1 type="video"'
      line += f' tvg-id="{c["canonical_name"]}"'
      line += f' tvg-name="{c["canonical_name"]}"'
      line += f' group-title="{c["language"]}"'
      line += f' tvg-logo="{c["logo"]}"'
      if c['has_replay']:
        line += f' catchup="default"'
        line += f' catchup-days="{self.catchup_days}"'

        if app == 'kodi':
          line += f' catchup-source="{self.catchup_url}?epg_pk={{catchup-id}}"'

        if app == 'tivimate':
          line += f' catchup-source="{self.catchup_redirect_url}?channel={c["pk"]}&start=${{start}}&duration=${{duration}}"'

        if app == 'pvrlive':
          app = 'debug'
        if app == 'tvirl':
          app = 'debug'
        if app == 'debug':
          line += ' catchup-source="' + self.catchup_redirect_url + '?channel={pk}'.format_map(c)
          line += '&start=${start}' # archive start time in Unix Timestamp Format
          line += '&end=${end}' # archive start time in Unix Timestamp Format
          line += '&stop=${stop}' # archive start time in Unix Timestamp Format
          line += '&dur=${duration}' # archive start time in Unix Timestamp Format
          line += '&startYmd=${start:Y-m-d}' # archive start time in Unix Timestamp Format
          line += '&timestamp=${timestamp}' # current time in Unix Timestamp Format
          line += '&offset=${offset}' # offset from current time in seconds
          line += '&b=${(b)yyyy}' # start in local time (… can be: yyyy, MM, dd, HH, mm, ss, UTF – Unix Timestamp Format)
          line += '&bu=${(bu)yyyy}' # start in UTC
          line += '&e=${(e)yyyy}' # stop in local time
          line += '&eu=${(eu)yyyy}' # stop in UTC
          line += '&n=${(n)yyyy}' # current time in local time
          line += '&nu=${(nu)yyyy}' # current time in UTC
          line += '&bu3=${(bu+3)yyy}' # start time in UTC with +3 hours time zone shift
          line += '&d=${(d)yyyy}' # duration (… can be: M – all minutes, S – all seconds, h – hours, m – minutes, s – seconds)
          line += '&utc={utc}' # The start time of the programme in UTC format.
          line += '&lutc={lutc}' # Current time in UTC format.
          line += '&now=${now}' # Same as {lutc}.
          line += '&utcend={utcend}' # The start time of the programme in UTC format + {duration}.
          line += '&end=${end}' # Same as {utcend}.
          line += '&Y={Y}' # The 4-digit year (YYYY) of the start date\time.
          line += '&m={m}' # The month (01-12) of the start date\time.
          line += '&d{d}' # The day (01-31) of the start date\time.
          line += '&H={H}' # The hour (00-23) of the start date\time.
          line += '&M={M}' # The minute (00-59) of the start date\time.
          line += '&S={S}' # The second (00-59) of the start date\time.
          line += '&duration={duration}' # The programme duration + any start and end buffer (if set).
          line += '&duration60={duration:60}' #  The programme duration (as above) divided by X seconds. Allows conversion to minutes and other time units. The minimum divider is 1, it must be an integer (not 1.5 or 2.25 etc.) and it must be a positive value. E.g. If you have a duration of 7200 seconds and you need 2 hours (2 hours is 7200 seconds), it means your divider is 3600: {duration:3600}. If you need minutes for the same duration you could use: {duration:60} which would result in a value of 120.
          line += '&offset60={offset:60}' # The current offset (now - start time) divided by X seconds. Allows conversion to minutes and other time units. The minimum divider is 1, it must be an integer (not 1.5 or 2.25 etc.) and it must be a positive value. E.g. If you need an offset of 720 for a start time of 2 hours ago (2 hours is 7200 seconds), it means your divider is 10: {offset:10}. If you need minutes for the same offset you could use: {offset:60} which would result in a value of 120.
          line += '&catchup-id={catchup-id}' # A programme specific identifier required in the catchup URL, value loaded from XMLTV programme entries.
          line += '"'


      line += ',{name}'.format_map(c)


      lines.append(line)
      if app == 'kodi':
        # 06/24: The new HLS streams do not yield any sound with Kodi's default inputstream plugin, so we force ffmpeg.
        lines.append('#KODIPROP:inputstream=inputstream.ffmpegdirect')
        lines.append('#KODIPROP:inputstream.ffmpegdirect.is_realtime_stream=true')

      if c['has_hls']:
        lines.append(c['hls_src'])
      else:
        lines.append(self.udpxy(c['src']))

    return(('\n'.join(lines))+'\n')

  def udpxy(self, address):
    """Wraps a udp address in udpxy if udpxy_address defined."""

    if not self.udpxy_address:
      return address

    # Assume that address has the form udp://@233.50.230.22:5000
    r = re.compile(r'udp://@([0-9.]+):(\d+)')
    m = r.match(address)
    if m:
      udp_ip = m.group(1)
      udp_port = m.group(2)
      return f'{self.udpxy_address}/udp/{udp_ip}:{udp_port}'

    # fallback
    return address


def read_config(config_file):

  with open(config_file) as conf:
    config = yaml.load(conf, Loader=yaml.FullLoader)
    if not 'port' in config:
      config['port'] = 80
    return config


def main():

  if len(sys.argv) > 1:
    config_file = sys.argv[1]
  else:
    config_file = 'config.yml'

  config = read_config(config_file)

  tv7 = TV7(config=config)
  tv7.update()

  print("Generating output")
  data = tv7.get_epg(app='kodi')
  with open('guide.xml', 'w+') as out:
    out.write(data.decode('utf-8'))

  m3u = tv7.get_m3u(app='kodi')
  with open('tv7.m3u', 'w+') as out:
    out.write(m3u)


if __name__ == "__main__":
  main()

