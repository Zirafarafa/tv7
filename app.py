import api

import yaml
from tv7 import TV7

from flask import Flask
from flask_cors import CORS

import sys


def setup(config_file):
  with open(config_file) as conf:
    config = yaml.load(conf, Loader=yaml.FullLoader)
    tv7 = TV7(config=config)
    tv7.update()

    api.tv7 = tv7

    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(api.bp)
    return app


if __name__ == "__main__":

  config_file = 'config.yml'

  if len(sys.argv) > 1:
    config_file = sys.argv[1]

  app = setup(config_file)
  app.run(host='0.0.0.0', port=80)

