import api

import yaml
from tv7 import TV7

from flask import Flask
from flask_cors import CORS

def main():
   with open("config.yml") as file:
     config = yaml.load(file, Loader=yaml.FullLoader)
     tv7 = TV7(config=config)
     tv7.update()

     api.tv7 = tv7

     app = Flask(__name__)
     CORS(app)

     app.register_blueprint(api.bp)
     app.run(host='0.0.0.0')

if __name__ == "__main__":
  main()
