#!/usr/bin/env python3

import argparse
import sys

from configparser import ConfigParser

import requests

from trello import TrelloApi


verbose = lambda *a, **kw: None

config = ConfigParser()
config.read("config.ini")
# sections for convenience
TRELLO = config["TRELLO"]
SERVER = config["SERVER"]


def _call_and_check(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except requests.exceptions.HTTPError as err:
        print(f"Request failed with the following error: {err.response.text}")
        verbose(err)
        sys.exit(1)


def create_webhook(callbackURL, idModel, description=None):
    trello = TrelloApi(TRELLO["AppKey"], TRELLO["Token"])
    _call_and_check(trello.webhooks.new, callbackURL, idModel, description=description)
    print("New webhook was created")


def list_webhooks():
    trello = TrelloApi(TRELLO["AppKey"], TRELLO["Token"])
    webhooks = _call_and_check(trello.tokens.get_webhook, TRELLO["Token"])
    for webhook in webhooks:
        print(webhook)


def delete_webhook(idWebhook):
    trello = TrelloApi(TRELLO["AppKey"], TRELLO["Token"])
    _call_and_check(trello.webhooks.delete, idWebhook)
    print(f"Webhook {idWebhook} was deleted")


def auto_setup():
    trello = TrelloApi(TRELLO["AppKey"], TRELLO["Token"])
    webhooks = _call_and_check(trello.tokens.get_webhook, TRELLO["Token"])

    for webhook in webhooks:
        # find webhook hooked to this site
        if webhook["callbackURL"] == SERVER["Address"]:
            # no need to setup anything if webhook is active
            if webhook["active"]:
                return

            print("deleting inactive webhook")
            trello.webhooks.delete(webhook["id"])

    # create new webhook
    print("setting up a new webhook")
    _call_and_check(trello.webhooks.new, SERVER["Address"], TRELLO["Board"],
                    description="Trello script webhook")


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="make error messages more verbose")
    subparsers = parser.add_subparsers(dest="action")

    subparser = subparsers.add_parser("add")
    subparser.add_argument("callbackURL")
    subparser.add_argument("idModel")
    subparser.add_argument("-d", "--description", default=None)

    subparsers.add_parser("list")

    subparser = subparsers.add_parser("delete")
    subparser.add_argument("idWebhook")

    subparsers.add_parser("auto",
        help="auto setup webhook for trello board based on the config file")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    if args.verbose:
        global verbose
        verbose = print

    if args.action == "add":
        create_webhook(args.callbackURL, args.idModel, args.description)
    elif args.action == "list":
        list_webhooks()
    elif args.action == "delete":
        delete_webhook(args.idWebhook)
    elif args.action == "auto":
        auto_setup()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
