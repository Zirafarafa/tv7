import unittest
import pytest
import requests_mock
import requests

import tv7

class TestTV7(unittest.TestCase):
  """Tests TV7 class."""

  def test_get_catchup_url(self):
    """Test formatting of the catchup URL."""
    t = tv7.TV7(config={})
    url = t.get_catchup_url('a', 100, 1200)
    expected = (
      'https://api.tv.init7.net/api/replay/'
      '?channel=a&start=1970-01-01T00:01:40Z&stop=1970-01-01T00:21:40Z'
    )
    self.assertEqual(url, expected)

  def test_udpxy_passthrough(self):
    """Verify that udpxy() returns unchanged if udpxy_address is not set."""
    t = tv7.TV7(config={})
    address = 'udp://@1.2.3.4:5'
    self.assertEqual(address, t.udpxy(address))

  def test_udpxy_wrap(self):
    """Verify that udpxy() correctly wraps the address."""
    t = tv7.TV7(config={'udpxy_address': 'http://a.b.c.d:4022'})
    address = 'udp://@1.2.3.4:5'
    self.assertEqual('http://a.b.c.d:4022/udp/1.2.3.4:5', t.udpxy(address))

  def test_read_channels(self):
    """Test that channels are read correctly from the api."""
    json = {
      'next': None,
      'results': [
        { 'pk': '1', 'canonical_name': 'ABC'},
      ]
    }
    session = requests.Session()
    with requests_mock.Mocker(session=session) as s:
      s.get('https://api.tv.init7.net/api/tvchannel/', json=json, status_code=200)

      t = tv7.TV7(config={}, session=session)
      t.m3u_channel_urls_with_priority = []
      c = t.get_channels()
      self.assertEqual(c, [{'pk': '1', 'canonical_name': 'ABC'}])

  def test_read_channels_include(self):
    """Test that include_channels works."""
    json = {
      'next': None,
      'results': [
        { 'pk': '1', 'canonical_name': 'ABC'},
        { 'pk': '2', 'canonical_name': 'DEF'}
      ]
    }
    session = requests.Session()
    with requests_mock.Mocker(session=session) as s:
      s.get('https://api.tv.init7.net/api/tvchannel/', json=json, status_code=200)

      t = tv7.TV7(config={'include_channels': ['ABC']}, session=session)
      t.m3u_channel_urls_with_priority = []
      c = t.get_channels()
      self.assertEqual(c, [{'pk': '1', 'canonical_name': 'ABC'}])


  def _merge_fixture(self):
    """API channels and two m3u sources for the merge tests."""
    api_json = {
      'next': None,
      'results': [
        # Offers HLS and multicast.
        {'pk': '1', 'canonical_name': 'ABC',
         'hls_src': 'https://old/abc.m3u8', 'src': 'udp://@1.1.1.1:5000'},
        # Multicast only.
        {'pk': '2', 'canonical_name': 'DEF',
         'hls_src': None, 'src': 'udp://@2.2.2.2:5000'},
        # No URL keys at all.
        {'pk': '3', 'canonical_name': 'GHI'},
      ]
    }
    high = (
      '#EXTM3U\n'
      '#EXTINF:-1 tvg-name="ABC" group-title="de",ABC HD\n'
      'https://high/abc.m3u8\n'
      '#EXTINF:-1 tvg-name="DEF",DEF HD\n'
      'https://high/def.m3u8\n'
      '#EXTINF:-1 tvg-name="GHI",GHI HD\n'
      'https://high/ghi.m3u8\n'
      '#EXTINF:-1 tvg-name="XYZ",Unknown\n'
      'https://high/xyz.m3u8\n'
    )
    low = (
      '#EXTM3U\n'
      '#EXTINF:-1 tvg-name="ABC",ABC HD\n'
      'https://low/abc.m3u8\n'
      '#EXTINF:-1 tvg-name="ABC",ABC HD\n'
      'udp://@1.1.1.9:5000\n'
      '\n'
      '#EXTINF:-1 tvg-name="DEF",DEF HD\n'
      '#EXTVLCOPT:network-caching=1000\n'
      'udp://@2.2.2.9:5000\n'
    )
    return api_json, high, low

  def _make_tv7(self, session):
    t = tv7.TV7(config={}, session=session)
    t.m3u_channel_urls_with_priority = [
      ('https://m3u/high.m3u', 2),
      ('https://m3u/low.m3u', 1),
      ('https://m3u/ignored.m3u', 0),
    ]
    return t

  def test_merge_m3u_channel_data(self):
    """Higher-priority m3u URLs win, and only existing URL kinds are replaced."""
    api_json, high, low = self._merge_fixture()
    session = requests.Session()
    with requests_mock.Mocker(session=session) as s:
      s.get('https://api.tv.init7.net/api/tvchannel/', json=api_json)
      s.get('https://m3u/high.m3u', text=high)
      s.get('https://m3u/low.m3u', text=low)
      ignored = s.get('https://m3u/ignored.m3u', text='')

      c = self._make_tv7(session).get_channels()

      self.assertIsInstance(c, list)
      self.assertFalse(ignored.called)
    self.assertEqual(c, [
      {'pk': '1', 'canonical_name': 'ABC',
       'hls_src': 'https://high/abc.m3u8', 'src': 'udp://@1.1.1.9:5000'},
      {'pk': '2', 'canonical_name': 'DEF',
       'hls_src': None, 'src': 'udp://@2.2.2.9:5000'},
      {'pk': '3', 'canonical_name': 'GHI'},
    ])

  def test_merge_m3u_channel_data_source_unavailable(self):
    """A failing m3u source is skipped and the others still apply."""
    api_json, _, low = self._merge_fixture()
    session = requests.Session()
    with requests_mock.Mocker(session=session) as s:
      s.get('https://api.tv.init7.net/api/tvchannel/', json=api_json)
      s.get('https://m3u/high.m3u', status_code=503)
      s.get('https://m3u/low.m3u', text=low)

      with self.assertLogs(level='WARNING'):
        c = self._make_tv7(session).get_channels()

    self.assertEqual(c[0]['hls_src'], 'https://low/abc.m3u8')
    self.assertEqual(c[0]['src'], 'udp://@1.1.1.9:5000')

  def test_read_epg_for_channel(self):
    epg_json = [{
      "count": 4,
      "next": "https://api.tv.init7.net/api/epg/?channel=1&offset=2",
      "previous": None,
      'results': [
        { 'pk': '1', 'title': 'ABC'},
        { 'pk': '2', 'title': 'DEF'}
      ]
    }, {
      "count": 4,
      "next": None,
      "previous": "https://api.tv.init7.net/api/epg/?channel=1&offset=0",
      'results': [
        { 'pk': '3', 'title': 'GHI'},
        { 'pk': '4', 'title': 'JKL'}
      ]
    }]
    session = requests.Session()
    with requests_mock.Mocker(session=session) as s:
      s.get('https://api.tv.init7.net/api/epg/?channel=1', json=epg_json[0], status_code=200)
      s.get('https://api.tv.init7.net/api/epg/?channel=1&offset=2', json=epg_json[1], status_code=200)

      t = tv7.TV7(config={'include_channels': ['ABC']}, session=session)
      res = t.read_epg_for_channel(1)
      self.assertEqual(res, [
        { 'pk': '1', 'title': 'ABC'},
        { 'pk': '2', 'title': 'DEF'},
        { 'pk': '3', 'title': 'GHI'},
        { 'pk': '4', 'title': 'JKL'},
      ])
