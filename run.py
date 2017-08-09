#!./venv/bin/python

import re
import logging

from datetime import datetime
from datetime import timedelta

from trello import TrelloApi

TRELLO_APP_KEY = 'TRELLO_APP_KEY'
TRELLO_TOKEN = 'TRELLO_TOKEN'
TRELLO_BOARD = 'TRELLO_BOARD'

DELAY_LABEL = 'DELAY_LABEL'


def handle_cards_with_delay_sign(trello):
    p = re.compile('\$\d*')

    cards = trello.boards.get_card(TRELLO_BOARD, filter='open', fields='idLabels,name,due')
    for card in cards:
        res = p.findall(card['name'])
        if not res:
            continue

        delay = int(res[-1][1:]) if len(res[-1]) > 1 else 1

        current_time = datetime.utcnow() + timedelta(days=delay)
        card['due'] = datetime.strftime(current_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        card['idLabels'].append(DELAY_LABEL)
        card['name'] = re.sub(p, "", card['name'])

        trello.cards.update(card['id'], idLabels=card['idLabels'], name=card['name'], due=card['due'])


def hide_delayed_cards(trello):
    cards = trello.boards.get_card(TRELLO_BOARD, filter='open', fields='idLabels,name,due')
    for card in cards:
        if DELAY_LABEL not in card['idLabels']:
            continue

        if card['due'] is None:
            continue

        current_time = datetime.utcnow()
        card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if current_time > card_due:
            continue

        trello.cards.update_closed(card['id'], 'true')

        logging.info('[%s]: Card hidden: %s', datetime.now(), card['name'])


def show_delayed_cards(trello):
    cards = trello.boards.get_card(TRELLO_BOARD, filter='closed', fields='idLabels,name,due')
    for card in cards:
        if DELAY_LABEL not in card['idLabels']:
            continue

        if card['due'] is None:
            continue

        current_time = datetime.utcnow()
        card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if current_time < card_due:
            continue

        trello.cards.update_due(card['id'], 'null')
        trello.cards.update_closed(card['id'], 'false')

        logging.info('[%s]: Card restored: %s', datetime.now(), card['name'])


if __name__ == "__main__":

    logging.basicConfig(filename='./logging.log', filemode='a', level=logging.INFO)
    logging.info('[%s]: running Trello card delayer', datetime.now())

    trello = TrelloApi(TRELLO_APP_KEY, TRELLO_TOKEN)

    handle_cards_with_delay_sign(trello)

    hide_delayed_cards(trello)
    show_delayed_cards(trello)
