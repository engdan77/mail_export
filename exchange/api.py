from exchangelib import Credentials, Account
from peewee import *
from collections import namedtuple as nt
import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print
from richlog import log
import re
from pathlib import Path
from bullet import ScrollBar
import htmllaundry
from markdownify import markdownify as md


ISO_FORMAT = "%Y-%m-%d %H:%M:%S"
database_proxy = DatabaseProxy()


class Mail(Model):
    datetime = DateTimeField()
    to = TextField()
    sender = TextField()
    cc = TextField()
    subject = TextField()
    body = TextField()

    class Meta:
        database = database_proxy


class Email:
    def __init__(self, /, filename="emails.sqlite", email=None, password=None):
        db = SqliteDatabase(filename)
        database_proxy.initialize(db)
        self.email = email
        self.password = password

        db.create_tables(
            [
                Mail,
            ]
        )

    @staticmethod
    def to_iso_dt(dt_string):
        return datetime.datetime.strptime(dt_string, ISO_FORMAT)

    def collect_mail(self):
        credentials = Credentials(self.email, self.password)
        account = Account(self.email, credentials=credentials, autodiscover=True)
        fields = ("datetime", "sender", "to", "cc", "subject", "body")
        tot = account.inbox.total_count
        log.info(f"total items inbox {tot}")

        for item in track(
            account.inbox.all().order_by("-datetime_received")[:3], total=tot
        ):
            f = nt("f", fields)(
                self.to_iso_dt(str(item.datetime_received.strftime(ISO_FORMAT))),
                f"{item.sender.name} <{item.sender.email_address}>",
                ",".join([f"{_.name} <{_.email_address}>" for _ in item.to_recipients]),
                str(item.display_cc),
                item.subject,
                item.body,
            )
            if Mail.select().where(Mail.datetime == f.datetime).count() == 0:
                Mail.insert(**f._asdict()).execute()

    @staticmethod
    def get_db_records(**kwargs):
        f, t = kwargs.get("f", 0), kwargs.get("t", Mail.select().count())
        records = Mail.select().where((Mail.id >= f) & (Mail.id <= t)).dicts()
        return records

    def print_db_records_table(self):
        cols = Mail._meta.columns.keys()
        table = Table(show_header=True, header_style="bold magenta", min_width=300)
        for _ in cols:
            table.add_column(_)
        next(
            c for c in table.columns if c.header in ["body", "to", "sender"]
        ).width = 20
        for _ in self.get_db_records():
            table.add_row(*[str(_[c])[:40] for c in cols])
        Console().print(table)

    def records_to_files(self, out="./out"):
        for r in self.get_db_records():
            fn = f"{r['datetime'].strftime('%y%m%d_%H%M')}"
            fn += f"__{r['sender'].split()[0]}__"
            fn += re.sub(r"[^\w]", "", f"{'_'.join(r['subject'].split()[:10])}")
            fn += f".html"
            Path(out).mkdir(parents=True, exist_ok=True)
            f = Path(out) / Path(fn)
            log.info(f"writing {f}")
            f.write_text(r["body"])

    @staticmethod
    def find_records(search_word):
        records = (
            Mail.select()
            .where(
                (Mail.to.contains(search_word))
                | (Mail.sender.contains(search_word))
                | (Mail.subject.contains(search_word))
                | (Mail.body.contains(search_word))
            )
            .dicts()
        )
        log.info(f"found {len(records)} records")
        return records

    def select_records(self, records=None):
        if not records:
            records = self.get_db_records()
        l = ["Exit"]
        l.extend(
            [
                f"{r['id']} - {r['datetime'].strftime('%y%m%d %H:%M')} - {r['subject']}"
                for r in records
            ]
        )
        cli = ScrollBar(
            prompt="Which one would you like to look at?", choices=l, height=10
        ).launch()
        i = next(iter(cli.split(" - ")))
        return i if i != "Exit" else None

    @staticmethod
    def format_html(input):
        html = htmllaundry.sanitize(input, htmllaundry.cleaners.LineCleaner)
        m = md(html)
        lines = [line for line in m.split("\n") if line.strip() != ""]
        return "\n".join(lines[:40])

    def show_record(self, record_id):
        r = Mail.select().where(Mail.id == record_id).first()
        markdown = self.format_html(r.body)
        print("[white]_[/white]" * 50)
        print(f"[bold red]From:[/bold red] {r.sender}")
        print(f"[bold red]To:[/bold red] {r.to}")
        print(f"[bold red]Cc:[/bold red] {r.cc}")
        print(f"[bold red]Subject:[/bold red][bold yellow] {r.subject}[/bold yellow]")
        print("[white]_[/white]" * 50)
        print(markdown)