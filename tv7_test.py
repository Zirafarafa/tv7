import unittest
import pytest
import requests_mock
import requests

import tv7

class TestTV7(unittest.TestCase):

  def test_get_catchup_url(self):
    t = tv7.TV7(config={})
    url = t.get_catchup_url('a', 100, 1200)
    expected = 'https://api.tv.init7.net/api/replay/?channel=a&start=1970-01-01T00:01:40Z&stop=1970-01-01T00:21:40Z'
    self.assertEqual(url, expected)


  def test_read_channels(self):
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
      t.read_channels()
      self.assertEqual(t.channels, [{'pk': '1', 'canonical_name': 'ABC'}])

  def test_read_channels_include(self):
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
      t.read_channels()
      self.assertEqual(t.channels, [{'pk': '1', 'canonical_name': 'ABC'}])
