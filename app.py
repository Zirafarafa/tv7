import api

import yaml
from tv7 import TV7

from flask import Flask
from flask_cors import CORS

import sys


def read_config(config_file):

  with open(config_file) as conf:
    config = yaml.load(conf, Loader=yaml.FullLoader)
    if not 'port' in config:
      config['port'] = 80
    return config


def setup(config):
  tv7 = TV7(config=config)
  tv7.update()

  api.tv7 = tv7

  app = Flask(__name__)
  CORS(app)

  app.register_blueprint(api.bp)
  return app


if __name__ == "__main__":

  if len(sys.argv) > 1:
    config_file = sys.argv[1]
  else:
    config_file = 'config.yml'

  config = read_config(config_file)

  app = setup(config)
  app.run(host='0.0.0.0', port=int(config['port']))

