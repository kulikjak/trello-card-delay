# Trello card snoozer
This simple script will let you snooze some of your trello cards and hide them before their time will come.

If you miss start date for your trello cards, you can use this script to add this functionality.

* GitHub repo: https://github.com/Kulikjak/trello-card-snooze

### Installation
Simply download the python script and fill in your Trello details (`API_KEY`, `TOKEN`, `SNOOZE_LABEL`, `TRELLO_BOARD`).

You can find your `API_KEY` and `TOKEN` on https://trello.com/app-key.

Then create one trello label, that will serve as snooze label and get its id. These can be found by adding `.json` to your trello board web address and then search a little...

### Usage
Run this script manually or use cron to run it periodically.

To snooze your card, set its start date (use Due date for that) and then add a snooze label to it. The script will automatically hide this card and reveal it again when its time will come. You can also write dolar sign and number after it and tell script that you want to snooze your card for n days.

To automatically unarchive cards every night on some lists, fill in list ids in `TRELLO_SNOOZE_LISTS` variable. All lists in this list will be unarchived every day during deep night.

### Author
* Jakub Kulik, <kulikjak@gmail.com>
