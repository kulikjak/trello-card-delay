import subprocess

from flask import Flask
from flask import request
from flask import jsonify

app = Flask(__name__)

@app.route('/trellowebhook', methods=['GET', 'POST', 'HEAD'])
def webhook():
    # respond to HEAD request when new webhook is being created
    if request.method == "HEAD":
        return "", 200

    # run the script when any POST or GET request is received
    script = "..."
    res = subprocess.run(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return jsonify({
        "stdout": res.stdout.decode(),
        "stderr": res.stderr.decode(),
        "returncode": res.returncode}), 200


if __name__ == '__main__':
    ssl_context = ('cert.pem', 'key.pem')
    # trello needs https communication on port 443
    app.run(host='0.0.0.0', port=443, ssl_context=ssl_context)
