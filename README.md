# Trello card delayer
This simple script will let you delay some of your trello cards and hide them before their time will come.

If you miss start date for your trello cards, you can use this script to add this functionality.

* GitHub repo: https://github.com/Kulikjak/trello-card-delay

### Installation
Simply download the python script and fill in your Trello details (`API_KEY`, `TOKEN`, `DELAY_LABEL`).

You can find your `API_KEY` and `TOKEN` on https://trello.com/app-key.

Then create one trello label, that will serve as delay label and get its id. These can be found by adding `.json` to your trello board web address and then search a little...

### Usage
Run this script manually or use cron to run it periodically.

To delay your card, set its start date (use Due date for that) and then assign a delay label to it. The script will automatically hide this card and reveal it again when its time will come.

### Author
* Jakub Kulik, <kulikjak@gmail.com>
