#!/usr/bin/env python3
import io
import ssl

from configparser import ConfigParser
from contextlib import redirect_stdout, redirect_stderr

from flask import Flask
from flask import request
from flask import jsonify

import run


app = Flask(__name__)


@app.route("/")
def index():
    # just to check that the webserver works
    return "Nothing to see here!"


@app.route("/trellowebhook", methods=["GET", "POST", "HEAD"])
def webhook():
    # respond to HEAD request when new webhook is being created
    if request.method == "HEAD":
        return "", 200

    # call the trello script main function with the stdout
    # and stdout redirected to variables
    with io.StringIO() as out, io.StringIO() as err:
        with redirect_stdout(out), redirect_stderr(err):
            returncode = run.main()

        return jsonify({
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
            "returncode": returncode}), 200


def main():
    config = ConfigParser()
    config.read("config.ini")

    port = config["SERVER"].getint("Port")

    try:
        cert_file = config["SERVER"]["CertFile"]
        pkey_file = config["SERVER"]["PKeyFile"]

        ctx = ssl.SSLContext()
        ctx.load_cert_chain(cert_file, pkey_file)
    except KeyError:
        # ssl certificates are not available
        ctx = "adhoc"

    app.run(host="0.0.0.0", port=port, ssl_context=ctx)


if __name__ == "__main__":
    main()
