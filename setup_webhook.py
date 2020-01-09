from trello import TrelloApi

from config import TRELLO
from config import WEBHOOK


def setup_webhook():
    trello = TrelloApi(TRELLO.APP_KEY, TRELLO.TOKEN)
    webhooks = trello.tokens.get_webhook(TRELLO.TOKEN)

    for webhook in webhooks:
        # find webhook hooked to this site
        if webhook['callbackURL'] == WEBHOOK.ADDRESS:
            # no need to setup anything if webhook is active
            if webhook['active']:
                return

            print("deleting inactive webhook")
            trello.webhooks.delete(webhook['id'])

    # create new webhook
    print("setting up a new webhook")
    trello.webhooks.new(WEBHOOK.ADDRESS, TRELLO.BOARD, description="Trello script webhook")


if __name__ == '__main__':
    setup_webhook()
