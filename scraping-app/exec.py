
import re
import json
from flask import Flask, render_template
from flask import request
import subprocess
import traceback

app = Flask(__name__)

@app.route('/')
def index():
    return "Hallo World!\n"

@app.route('/exec', methods=["POST"])
def exec():
    data = request.data.decode('utf-8')
    httprespons = ""
    httpstatus = 200
    try:
        data = json.loads(data)
        cmd = data.get('cmd')
        exec_cmd = re.split(r' +', f'python main.py {cmd}')
        res = subprocess.run(
            # ["ls", "-l"],
            exec_cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        httprespons = res.stdout
        if res.returncode != 0:
            httpstatus = 500
    except Exception as ex:
        httprespons = ''.join(traceback.TracebackException.from_exception(ex).format())
        httpstatus = 500
    return httprespons, httpstatus

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True)
