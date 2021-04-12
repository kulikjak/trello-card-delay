#!/usr/bin/env python3

import fcntl
import logging
import re
import os
import sys

from configparser import ConfigParser
from datetime import time
from datetime import datetime
from datetime import timedelta

from trello import TrelloApi

config = ConfigParser()
config.read("config.ini")
# sections for convenience
LABEL = config["LABEL"]
LIST = config["LIST"]
TRELLO = config["TRELLO"]


# correctly determine current location
script_location = os.path.dirname(os.path.realpath(__file__))
# setup logging
logfile = os.path.join(script_location, "logging.log")
logging.basicConfig(filename=logfile, filemode="a", level=logging.INFO)


def integrity_check(card):
    # check that delayed (archived) cards do have a due date
    if card["closed"] and LABEL["Snooze"] in card["idLabels"] and not card["due"]:
        return False, "Card does have delay label without any date set"

    return True, None


def handle_dollar_snoozing(trello, card):
    pattern = re.compile(r"\$\d*")

    # skip irelevant cards and find all dollars
    match = re.findall(pattern, card["name"])
    if not match:
        return

    # get the last $x value
    substr = match[-1].lstrip("$")
    delay = 1 if not substr else int(substr)
    delay_time = datetime.utcnow() + timedelta(days=delay)

    card["name"] = re.sub(pattern, "", card["name"])
    card["due"] = datetime.strftime(delay_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    card["idLabels"] = card["idLabels"] + [LABEL["Snooze"]]

    trello.cards.update(card["id"], name=card["name"], due=card["due"], idLabels=card["idLabels"])
    logging.info(f"[{datetime.now()}]: Card $ handled: {card['id']} : {card['name']}")


def snooze_card(trello, card):
    # only continue with relevant cards
    if LABEL["Snooze"] not in card["idLabels"] or not card["due"]:
        return

    # skip those already sleeping
    if card["closed"]:
        return

    # check if time is not here yet
    current_time = datetime.utcnow()
    card_due = datetime.strptime(card["due"], "%Y-%m-%dT%H:%M:%S.%fZ")
    if current_time > card_due:
        return

    card["closed"] = True

    trello.cards.update(card["id"], closed="true")
    logging.info(f"[{datetime.now()}]: Card snoozed: {card['id']} : {card['name']}")


def wake_card(trello, card):
    # only continue with relevant cards
    if LABEL["Snooze"] not in card["idLabels"] or not card["due"]:
        return

    # check if time has come
    current_time = datetime.utcnow()
    card_due = datetime.strptime(card["due"], "%Y-%m-%dT%H:%M:%S.%fZ")
    if current_time < card_due:
        return

    card["closed"] = False
    card["due"] = None

    trello.cards.update(card["id"], closed="false", due="null")
    logging.info(f"[{datetime.now()}]: Card awaken: {card['id']} : {card['name']}")


def _run_trellohelper():

    trello = TrelloApi(TRELLO["AppKey"], TRELLO["Token"])

    # retrieve all cards on the main board
    data = trello.boards.get_card(TRELLO["Board"], filter="all", checklists="all")

    # we are not interested in cards, which are closed
    # and without any progress labels
    progress_labels = {LABEL["Snooze"], LABEL["Tomorrow"]}
    cards = [c for c in data if not c["closed"] or set(c["idLabels"]) & progress_labels]

    logging.info(f"Total board/open cards: {len(data)}/{len(cards)}")

    for card in cards:

        # check whether everything is ok with this card
        ok, reason = integrity_check(card)
        if not ok:
            # broken cards need to be returned
            trello.cards.update(
                card["id"],
                due="null",
                closed="false",
                name=f"[RESTORED] {card['name']}",
                desc=f"**This card was restored**\n{reason}\n\n{card['desc']}",
                idLabels=card["idLabels"] + [LABEL["Important"]]
            )
            continue

        # handle dollar snooze shortcuts
        handle_dollar_snoozing(trello, card)

        # snooze cards with date and delay label
        snooze_card(trello, card)

        # wake me up when time comes
        wake_card(trello, card)

    # schedule cards for tomorrow
    current_time = datetime.now().time()
    if time(1, 0, 0) <= current_time <= time(2, 0, 0):
        logging.info(f"[{datetime.now()}]: running tomorrow scheduling")

        for card in cards:
            # work with relevant cards only
            if LABEL["Tomorrow"] not in card["idLabels"]:
                continue

            card["idList"] = LIST["Tomorrow"]
            card["idLabels"].remove(LABEL["Tomorrow"])

            trello.cards.update(card["id"], idList=card["idList"])
            # labels cannot be removed with update in some cases (where none would remain)
            trello.cards.delete_idLabel_idLabel(LABEL["Tomorrow"], card["id"])
            logging.info(
                f"[{datetime.now()}]: Card scheduled for tomorrow: {card['id']} : {card['name']}"
            )

    # handle projects and project related labels
    cards = [c for c in data if any(a["color"] is None for a in c["labels"])]

    projects = {}
    project_cards = []

    # at first go through individual cards (not the project one)
    for card in cards:

        if card["idList"] == LIST["Projects"]:
            # save project related cards for later quicker use
            project_cards.append(card)
            continue

        if LABEL["Snooze"] in card["idLabels"]:
            # do not consider snoozed cards in any way
            continue

        for label in card["labels"]:

            if label["color"] is not None:
                continue

            if label["id"] not in projects:
                projects[label["id"]] = []

            projects[label["id"]].append((card["name"], card["closed"]))

    # now handle project checklists
    for card in project_cards:

        for label in card["labels"]:
            # continue only with colorless labels with the project name
            if label["name"] != card["name"] or label["color"] is not None:
                continue

            if label["id"] not in projects:
                # this label is not present on any other card
                # and thus the checklist would be empty
                continue

            # get project related checklist
            checklist = next(
                (c for c in card["checklists"] if c["name"] == f"@{card['name']}"), None
            )
            if checklist is None:
                # create new checklist if one does not exist yet
                checklist = trello.cards.new_checklist(card["id"], name=f"@{card['name']}")

            for item in checklist["checkItems"]:
                for desc, closed in projects[label["id"]]:
                    if desc != item["name"]:
                        continue

                    if closed and item["state"] != "complete":
                        # change status to complete
                        trello.cards.update_checkItem_idCheckItem(
                            item["id"], card["id"], state="complete"
                        )

                    if not closed and item["state"] != "incomplete":
                        # change status to incomplete
                        trello.cards.update_checkItem_idCheckItem(
                            item["id"], card["id"], state="incomplete"
                        )

                    # remove this from projects
                    projects[label["id"]].remove((desc, closed))
                    break
                else:
                    trello.checklists.delete_checkItem_idCheckItem(
                        item["id"], checklist["id"]
                    )

            for desc, closed in projects[label["id"]]:
                trello.checklists.new_checkItem(
                    checklist["id"], desc, checked="true" if closed else "false"
                )

            break

        else:
            # in case we did not found any label, remove project checklist
            checklist = next(
                (c for c in card["checklists"] if c["name"] == f"@{card['name']}"), None
            )
            if checklist is not None:
                trello.checklists.delete(checklist["id"])

    # last thing: remove Zapier script checking card
    for card in data:
        if card["name"] == "[CHECK] Problem with Trello script":
            trello.cards.delete(card["id"])
            logging.info(f"[{datetime.now()}]: Deleted Zapier check card")
            break

    logging.info(f"[{datetime.now()}]: Done")


def run():
    logging.info(f"[{datetime.now()}]: Acquiring script lock.")

    # acquire lock to run this script. This assures that no more than
    # one instance of this script is running at the same time.
    try:
        script_lock = os.open(os.path.join(script_location, ".script_lock"), os.O_CREAT)
        fcntl.flock(script_lock, fcntl.LOCK_NB | fcntl.LOCK_EX)
    except OSError:
        logging.info(f"[{datetime.now()}]: Script lock cannot be acquired.")
        if script_lock:
            os.close(script_lock)
        return False

    try:
        _run_trellohelper()
    except BaseException:
        # no matter what happened we want to release the lock
        os.close(script_lock)
        raise

    os.close(script_lock)
    return True


if __name__ == "__main__":
    sys.exit(not run())
