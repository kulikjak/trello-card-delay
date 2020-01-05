from trello import TrelloApi

TRELLO_APP_KEY = '...'
TRELLO_TOKEN = '...'
TRELLO_BOARD = '...'

WEBHOOK_ADDRESS = '...'


def setup_webhook():
    trello = TrelloApi(TRELLO_APP_KEY, TRELLO_TOKEN)
    webhooks = trello.tokens.get_webhook(TRELLO_TOKEN)

    for webhook in webhooks:
        # find webhook hooked to this site
        if webhook['callbackURL'] == WEBHOOK_ADDRESS:
            # no need to setup anything if webhook is active
            if webhook['active']:
                return

            print("deleting inactive webhook")
            trello.webhooks.delete(webhook['id'])

    # create new webhook
    print("setting up a new webhook")
    trello.webhooks.new(WEBHOOK_ADDRESS, TRELLO_BOARD, description="Trello script webhook")


if __name__ == '__main__':
    setup_webhook()
