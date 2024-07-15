
import json
from flask import Flask, Response, request
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return "Hallo World!\n"

@app.route('/exec', methods=["POST"])
def exec():

    # コマンドの結果をリアルタイムで返すジェネレータ関数
    def generate(exec_cmd: str):
        popen = subprocess.Popen(exec_cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(popen.stdout.readline, ""):
            yield stdout_line
        popen.stdout.close()
        return_code = popen.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, cmd)

    try:
        data = request.data.decode('utf-8')
    except Exception as e:
        return "invalid encoding", 400
    try:
        data = json.loads(data)
    except Exception as e:
        return "invalid json", 400
    cmd = data.get('cmd')
    if not cmd:
        return "invalid args (cmd)", 400
    if not isinstance(cmd, list):
        return "invalid type (cmd)", 400
    exec_cmd = ['python', 'main.py'] + cmd

    return Response(generate(exec_cmd))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True)
