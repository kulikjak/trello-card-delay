#!/usr/bin/env python3
import io
import sys

from configparser import ConfigParser
from contextlib import redirect_stdout, redirect_stderr

from flask import Flask
from flask import request
from flask import jsonify

from cheroot.wsgi import Server as WSGIServer
from cheroot.wsgi import PathInfoDispatcher
from cheroot.ssl.builtin import BuiltinSSLAdapter

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

    wsgi_app = PathInfoDispatcher({"/": app})
    server = WSGIServer(("0.0.0.0", port), wsgi_app)

    try:
        cert_file = config["SERVER"]["CertFile"]
        pkey_file = config["SERVER"]["PKeyFile"]

        server.ssl_adapter = BuiltinSSLAdapter(cert_file, pkey_file)
    except KeyError:
        # ssl certificates are not available
        sys.stderr.write("Running without ssl!\n")

    server.start()


if __name__ == "__main__":
    main()
