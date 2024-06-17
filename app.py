import api

import logging

import yaml
from tv7 import TV7

from flask import Flask
from flask_cors import CORS
from flask.logging import default_handler

import sys


def read_config(file):

  with open(file) as conf:
    c = yaml.load(conf, Loader=yaml.FullLoader)
    if not 'port' in c:
      c['port'] = 80
    return c


def setup(cfg):
  tv7 = TV7(config=cfg)
  tv7.update()

  api.tv7 = tv7

  setup_app = Flask(__name__)
  CORS(setup_app)

  setup_app.register_blueprint(api.bp)
  return setup_app


if __name__ == "__main__":

  if len(sys.argv) > 1:
    config_file = sys.argv[1]
  else:
    config_file = 'config.yml'

  logging.basicConfig()
  root = logging.getLogger()
  root.setLevel(logging.INFO)

  config = read_config(config_file)

  app = setup(config)
  app.run(host='0.0.0.0', port=int(config['port']))

