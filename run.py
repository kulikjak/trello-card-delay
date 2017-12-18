import re
import logging

from datetime import time
from datetime import datetime
from datetime import timedelta

from trello import TrelloApi

# Trello communication API_KEY and TOKEN
TRELLO_APP_KEY = 'TRELLO_APP_KEY'
TRELLO_TOKEN = 'TRELLO_TOKEN'

# Id of Trello board
TRELLO_BOARD = 'TRELLO_BOARD'
# List of all auto snooze lists
TRELLO_SNOOZE_LISTS = ['TRELLO_SNOOZE_LISTS']

# Id of label which is used as snooze mark
SNOOZE_LABEL = 'SNOOZE_LABEL'


def handle_dollar_sign(trello):
    """ Checks for cards with dollar sign and uses following number as
    an indication of how long card should snoozed (in days). If no dollar sign
    is present, card is snoozed for one day. Function only adds snooze tag and
    due date - card is archived in later function.
    """
    p = re.compile('\$\d*')

    cards = trello.boards.get_card(
        TRELLO_BOARD, filter='open', fields='idLabels,name,due')
    for card in cards:
        res = p.findall(card['name'])
        if not res:
            continue

        delay = int(res[-1][1:]) if len(res[-1]) > 1 else 1

        current_time = datetime.utcnow() + timedelta(days=delay)
        card['due'] = datetime.strftime(current_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        card['idLabels'].append(SNOOZE_LABEL)
        card['name'] = re.sub(p, "", card['name'])

        trello.cards.update(
            card['id'],
            idLabels=card['idLabels'],
            name=card['name'],
            due=card['due'])


def unarchive_auto_list_cards(trello):
    """ Restore all cards on auto snooze lists. This is done every day during the night.
    """

    now = datetime.utcnow()
    now_time = now.time()

    if not time(3, 30) <= now_time <= time(4, 30):
        return

    for tlist in TRELLO_SNOOZE_LISTS:
        cards = trello.lists.get_card(tlist, filter='closed')
        for card in cards:
            trello.cards.update_closed(card['id'], 'false')
            logging.info('[%s]: Auto card restored: %s', datetime.now(),
                         card['name'])


def archive_cards(trello):
    """ Archive all cards with due date higher than current date and snooze tag
    """
    cards = trello.boards.get_card(
        TRELLO_BOARD, filter='open', fields='idLabels,name,due')
    for card in cards:
        if SNOOZE_LABEL not in card['idLabels']:
            continue

        if card['due'] is None:
            continue

        current_time = datetime.utcnow()
        card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if current_time > card_due:
            continue

        trello.cards.update_closed(card['id'], 'true')

        logging.info('[%s]: Card hidden: %s', datetime.now(), card['name'])


def unarchive_cards(trello):
    """ Unarchive all cards with due date smaller than current
    date and snooze tag. Due date is removed from card.
    """
    cards = trello.boards.get_card(
        TRELLO_BOARD, filter='closed', fields='idLabels,name,due')
    for card in cards:
        if SNOOZE_LABEL not in card['idLabels']:
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

    logging.basicConfig(
        filename='./logging.log', filemode='a', level=logging.INFO)
    logging.info('[%s]: running Trello card snoozer', datetime.now())

    trello = TrelloApi(TRELLO_APP_KEY, TRELLO_TOKEN)

    handle_dollar_sign(trello)
    archive_cards(trello)
    unarchive_cards(trello)
    unarchive_auto_list_cards(trello)
