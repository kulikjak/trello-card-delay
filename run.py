import fcntl
import json
import logging
import re
import os
import sys

from datetime import time
from datetime import datetime
from datetime import timedelta

from trello import TrelloApi


TRELLO_APP_KEY = '...'
TRELLO_TOKEN = '...'
TRELLO_BOARD = '...'

LABEL_TOMORROW = '...'
LABEL_SNOOZE = '...'
LABEL_IMPORTANT = '...'

PROGRESS_LABELS = [LABEL_SNOOZE, LABEL_TOMORROW]

LIST_TOMORROW = '...'


def integrity_check(card):
    # check that delayed (archived) cards do have a due date
    if card['closed'] and LABEL_SNOOZE in card['idLabels'] and not card['due']:
        return False, "Card does have delay label without any date set"

    return True, None


def handle_dollar_snoozing(trello, card):
    pattern = re.compile(r"\$\d*")

    # skip irelevant cards and find all dollars
    match = re.findall(pattern, card['name'])
    if not match:
        return

    # get the last $x value
    substr = match[-1].lstrip("$")
    delay = 1 if not substr else int(substr)
    delay_time = datetime.utcnow() + timedelta(days=delay)

    card['name'] = re.sub(pattern, "", card['name'])
    card['due'] = datetime.strftime(delay_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    card['idLabels'] = card['idLabels'] + [LABEL_SNOOZE]

    trello.cards.update(card['id'], name=card['name'], due=card['due'], idLabels=card['idLabels'])
    logging.info(f"[{datetime.now()}]: Card $ handled: {card['id']} : {card['name']}")


def snooze_card(trello, card):
    # only continue with relevant cards
    if LABEL_SNOOZE not in card['idLabels'] or not card['due']:
        return

    # skip those already sleeping
    if card['closed']:
        return

    # check if time is not here yet
    current_time = datetime.utcnow()
    card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
    if current_time > card_due:
        return

    card['closed'] = True

    trello.cards.update(card['id'], closed='true')
    logging.info(f"[{datetime.now()}]: Card snoozed: {card['id']} : {card['name']}")


def wake_card(trello, card):
    # only continue with relevant cards
    if LABEL_SNOOZE not in card['idLabels'] or not card['due']:
        return

    # check if time has come
    current_time = datetime.utcnow()
    card_due = datetime.strptime(card['due'], '%Y-%m-%dT%H:%M:%S.%fZ')
    if current_time < card_due:
        return

    card['closed'] = False
    card['due'] = None

    trello.cards.update(card['id'], closed='false', due='null')
    logging.info(f"[{datetime.now()}]: Card awaken: {card['id']} : {card['name']}")


def acquire_program_lock():
    queue_lock = None
    program_lock = None

    script_location = os.path.dirname(os.path.realpath(__file__))

    # first get into the queue
    try:
        queue_lock = os.open(os.path.join(script_location, ".queue_lock"), os.O_CREAT)
        fcntl.flock(queue_lock, fcntl.LOCK_NB | fcntl.LOCK_EX)
    except OSError:
        if queue_lock:
            os.close(queue_lock)
        return False

    program_lock = os.open(os.path.join(script_location, ".program_lock"), os.O_CREAT)
    fcntl.flock(program_lock, fcntl.LOCK_EX)

    # now unlock the .queue_lock
    fcntl.flock(queue_lock, fcntl.LOCK_UN)
    os.close(queue_lock)

    return True


def main():

    logging.basicConfig(filename='/root/logging.log', filemode='a', level=logging.INFO)
    logging.info(f"[{datetime.now()}]: Acquiring program lock.")

    if not acquire_program_lock():
        logging.info(f"[{datetime.now()}]: Program lock cannot be acquired.")
        sys.exit(1)

    trello = TrelloApi(TRELLO_APP_KEY, TRELLO_TOKEN)

    # retrieve all cards on the main board
    data = trello.boards.get_card(TRELLO_BOARD, filter='all')

    # we are not interested in cards, which are closed
    # and without any progress labels
    cards = [c for c in data if not c['closed'] or set(c['idLabels']) & set(PROGRESS_LABELS)]

    logging.info(f"Total board/relevant cards: {len(data)}/{len(cards)}")

    for card in cards:

        # check whether everything is ok with this card
        ok, reason = integrity_check(card)
        if not ok:
            # broken cards need to be returned
            trello.cards.update(card['id'],
                due='null',
                closed='false',
                name=f"[RESTORED] {card['name']}",
                desc=f"**This card was restored**\n{reason}\n\n{card['desc']}",
                idLabels=card['idLabels'] + [LABEL_IMPORTANT])
            continue

        # handle dollar snooze shortcuts
        handle_dollar_snoozing(trello, card)

        # snooze cards with date and delay label
        snooze_card(trello, card)

        # wake me up when time comes
        wake_card(trello, card)


    # schedule cards for tomorrow
    current_time = datetime.now().time()
    if time(1,0,0) <= current_time <= time(2,0,0):
        logging.info(f"[{datetime.now()}]: running tomorrow scheduling")

        for card in cards:
            # work with relevant cards only
            if LABEL_TOMORROW not in card['idLabels']:
                continue

            card['idList'] = LIST_TOMORROW
            card['idLabels'].remove(LABEL_TOMORROW)

            trello.cards.update(card['id'], idList=card['idList'])
            # labels cannot be removed with update in some cases (where none would remain)
            trello.cards.delete_idLabel_idLabel(LABEL_TOMORROW, card['id'])
            logging.info(f"[{datetime.now()}]: Card scheduled for tomorrow: {card['id']} : {card['name']}")


    # last thing: remove Zapier script checking card
    for card in cards:
        if card['name'] == "[CHECK] Problem with Trello script":
            trello.cards.delete(card['id'])
            logging.info(f"[{datetime.now()}]: Deleted Zapier check card")
            break


if __name__ == "__main__":
    main()
