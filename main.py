import os
from richlog import log
from rich.traceback import install
from rich import print
from exchange import Email
import argparse
from loguru import logger
from bullet import Bullet, Input, Password, SlidePrompt
from collections import namedtuple

install()

dt = namedtuple('dt', 'text pattern')('YYYY-MM-DD', '(\d{4}-\d{2}-\d{2})|^$')


def get_args():
    parser = argparse.ArgumentParser(description='Application for creating a local copy of your exchange mail account')
    parser.add_argument('--database', type=str, default='emails.sqlite', help='SQLite database file to store to')
    parser.add_argument('--email', type=str, help='E-mail to download from')
    parser.add_argument('--password', type=str, help='Password for e-mail account')
    args = parser.parse_args()
    for _ in ('email', 'password'):
        if getattr(args, _, None) is None:
            setattr(args, _, os.environ.get(_.upper(), None))
    return args


def bitem(bullet_item):
    return next(iter(bullet_item.split(' - ')))


class Menu:
    def __init__(self, args, email: Email):
        self.args = args
        self.email = email

    def info(self):
        self.email.print_db_status()

    def main(self):
        while True:
            self.info()
            items = {'Exit': exit,
                     'E-mail settings': self.get_mail_creds,
                     'Update date range filter': self.get_range,
                     'Update keyword filter': self.get_search_word,
                     'Reset filters': self.reset_filters}
            if all([self.email.email, self.email.password]):
                items['Download from account'] = self.email.collect_mail
            cli = Bullet(prompt='Choose:',
                         choices=list(items.keys())).launch()
            items.get(cli)()

    def get_mail_creds(self):
        cli = SlidePrompt([Input('E-mail address: '),
                          Password('Password: ')]).launch()
        v = dict(cli).values()
        self.email.email, self.email.password = v
        return cli

    def get_range(self):
        cli = SlidePrompt([
            Input(prompt=f'From date [{dt.text}]: ', pattern=dt.pattern),
            Input(prompt=f'To date [{dt.text}]: ', pattern=dt.pattern)]).launch()
        self.email.filter_range = [_[-1] for _ in cli]

    def get_search_word(self):
        words = Input(prompt='What filter words to use: ').launch()
        self.email.filter_keyword = words

    def reset_filters(self):
        self.email.filter_keyword = None
        self.email.filter_range = None, None


def init_log():
    logger.remove()
    logger.add('app.log', rotation='100 MB')


def main():
    init_log()
    args = get_args()
    email = Email(email=args.email, password=args.password)
    menu = Menu(args, email)
    menu.main()

    word = menu_get_search_word()
    print(word)
    f, t = menu_get_range()
    print(f, t)


    print(f"Welcome to [bold red]mail exporter[/bold red] :smile::e-mail::star:")

    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")

    store.print_db_status()

    # store.collect_mail()
    # store.get_db_records()
    store.print_db_records_table()
    # store.records_to_files()
    records = store.find_records("Daniel")
    s = store.select_records(records)
    store.show_record(s)


if __name__ == "__main__":
    main()