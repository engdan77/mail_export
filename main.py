from exchangelib import Credentials, Account
import os
from peewee import *
from collections import namedtuple as nt
import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.logging import RichHandler
import logging
import re
from pathlib import Path

logging.basicConfig(
    level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger(__name__)

ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

db = SqliteDatabase("emails.sqlite")


class Mail(Model):
    datetime = DateTimeField()
    to = TextField()
    sender = TextField()
    cc = TextField()
    subject = TextField()
    body = TextField()

    class Meta:
        database = db


def to_iso_dt(dt_string):
    return datetime.datetime.strptime(dt_string, ISO_FORMAT)


def collect_mail(email, password):
    credentials = Credentials(email, password)
    account = Account(email, credentials=credentials, autodiscover=True)
    fields = ("datetime", "sender", "to", "cc", "subject", "body")
    tot = account.inbox.total_count
    log.info(f"total items inbox {tot}")

    for item in track(
        account.inbox.all().order_by("-datetime_received")[:3], total=tot
    ):
        f = nt("f", fields)(
            to_iso_dt(str(item.datetime_received.strftime(ISO_FORMAT))),
            f"{item.sender.name} <{item.sender.email_address}>",
            ",".join([f"{_.name} <{_.email_address}>" for _ in item.to_recipients]),
            str(item.display_cc),
            item.subject,
            item.body,
        )
        if Mail.select().where(Mail.datetime == f.datetime).count() == 0:
            Mail.insert(**f._asdict()).execute()


def get_db_records(**kwargs):
    f, t = kwargs.get("f", 0), kwargs.get("t", Mail.select().count())
    records = Mail.select().where((Mail.id >= f) & (Mail.id <= t)).dicts()
    return records


def print_db_records(records):
    cols = Mail._meta.columns.keys()
    table = Table(show_header=True, header_style="bold magenta", min_width=300)
    for _ in cols:
        table.add_column(_)
    next(c for c in table.columns if c.header in ["body", "to", "sender"]).width = 20
    for _ in records:
        table.add_row(*[str(_[c])[:40] for c in cols])
    Console().print(table)


def records_to_files(records, out="./out"):
    for r in records:
        fn = f"{r['datetime'].strftime('%y%m%d_%H%M')}"
        fn += f"__{r['sender'].split()[0]}__"
        fn += re.sub(r"[^\w]", "", f"{'_'.join(r['subject'].split()[:10])}")
        fn += f".html"
        Path(out).mkdir(parents=True, exist_ok=True)
        f = Path(out) / Path(fn)
        log.info(f"writing {f}")
        f.write_text(r["body"])


if __name__ == "__main__":
    log.info("starting")
    db.create_tables(
        [
            Mail,
        ]
    )
    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")
    # collect_mail(email, password)
    records = get_db_records()
    print_db_records(records)
    records_to_files(records)
