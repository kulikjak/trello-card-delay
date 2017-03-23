#!./env/bin/python

import logging

from datetime import datetime
from datetime import timedelta

from trello import TrelloApi


TRELLO_APP_KEY = 'TRELLO_APP_KEY'
TRELLO_TOKEN = 'TRELLO_TOKEN'
DELAY_LABEL = 'DELAY_LABEL'


def hide_delayed_cards(trello):
    cards = trello.boards.get_card('vTWNRG2x', filter='open', fields='idLabels,name,due')
    for card in cards:
        if DELAY_LABEL not in card['idLabels']:
            continue

        if card['due'] is None:
            continue

        current_time = datetime.now()
        card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=1)
        if current_time > card_due:
            continue

        trello.cards.update_closed(card['id'], 'true')

        logging.info('[%s]: Card hidden: %s', datetime.now(), card['name'])


def show_delayed_cards(trello):
    cards = trello.boards.get_card('vTWNRG2x', filter='closed', fields='idLabels,name,due')
    for card in cards:
        if DELAY_LABEL not in card['idLabels']:
            continue

        if card['due'] is None:
            continue

        current_time = datetime.now()
        card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=1)
        if current_time < card_due:
            continue

        trello.cards.update_due(card['id'], 'null')
        trello.cards.update_closed(card['id'], 'false')

        logging.info('[%s]: Card restored: %s', datetime.now(), card['name'])


if __name__ == "__main__":

    logging.basicConfig(filename='./logging.log', filemode='a', level=logging.INFO)
    logging.info('[%s]: running Trello card delayer', datetime.now())

    trello = TrelloApi(TRELLO_APP_KEY, TRELLO_TOKEN)

    hide_delayed_cards(trello)
    show_delayed_cards(trello)
