from exchangelib import Credentials, Account
import os
from peewee import *
from collections import namedtuple as nt

db = SqliteDatabase('emails.sqlite')


class Mail(Model):
    datetime = TextField()
    to = TextField()
    sender = TextField()
    cc = TextField()
    subject = TextField()
    body = TextField()

    class Meta:
        database = db


def collect_mail(email, password):
    credentials = Credentials(email, password)
    account = Account(email, credentials=credentials, autodiscover=True)
    fields = ('datetime', 'sender', 'to', 'cc', 'subject', 'body')

    for item in account.inbox.all().order_by('-datetime_received')[:3]:
        f = nt('f', fields)(str(item.datetime_received.strftime('%Y-%m-%d %H:%M:%S')),
                            f'{item.sender.name} <{item.sender.email_address}>',
                            ','.join([f'{_.name} <{_.email_address}>' for _ in item.to_recipients]),
                            str(item.display_cc),
                            item.subject,
                            item.body)
        print(f)
        result = (Mail
                  .insert(**f._asdict())
                  .on_conflict('replace')
                  .execute())


if __name__ == '__main__':
    db.create_tables([Mail, ])
    email = os.environ.get('EMAIL')
    password = os.environ.get('PASSWORD')
    collect_mail(email, password)
