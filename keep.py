from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def index():
  return "Hello World"

def run():
  app.run(host='0.0.0.0', port=8080)

def keep ():
  t = Thread(target=run)
  t.start()


