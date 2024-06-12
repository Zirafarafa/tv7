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
      c = t.get_channels()
      self.assertEqual(c, [{'pk': '1', 'canonical_name': 'ABC'}])


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
