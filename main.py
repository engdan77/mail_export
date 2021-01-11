from exchangelib import Credentials, Account
import os
from peewee import *

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

    for item in account.inbox.all().order_by('-datetime_received')[:3]:
        datetime = item.datetime_received.strftime('%Y-%m-%d %H:%M:%S')
        body = item.body
        subject = item.subject
        to = ','.join([f'{_.name} <{_.email_address}>' for _ in item.to_recipients])
        sender = f'{item.sender.name} <{item.sender.email_address}>'
        cc = str(item.display_cc)

        fields = ('datetime', 'sender', 'to', 'cc', 'subject', 'body')

        for _ in fields:
            print(f'{_}: {locals().get(_)}')
            result = (Mail
                      .insert({_: locals().get(_) for _ in fields})
                      .on_conflict('replace')
                      .execute())
        print('-'*30)


if __name__ == '__main__':
    db.create_tables([Mail, ])

    email = os.environ.get('EMAIL')
    password = os.environ.get('PASSWORD')
    collect_mail(email, password)
