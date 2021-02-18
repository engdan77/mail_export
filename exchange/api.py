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
from bullet import ScrollBar, YesNo
import htmllaundry
from markdownify import markdownify as md
from loguru import logger
import operator
from functools import reduce
from typing import Annotated


ISO_FORMAT = "%Y-%m-%d %H:%M:%S"
database_proxy = DatabaseProxy()


class Mail(Model):
    datetime = DateTimeField()
    to = TextField()
    sender = TextField()
    cc = TextField(null=True)
    subject = TextField(null=True)
    body = TextField(null=True)

    class Meta:
        database = database_proxy


class Email:
    def __init__(self, /, database="emails.sqlite", email=None, password=None):
        self.filter_keyword = ''
        self.filter_range = None, None
        self.filename = database
        db = SqliteDatabase(self.filename)
        database_proxy.initialize(db)
        self.email = email
        self.password = password
        self.filtered_records = []

        db.create_tables(
            [
                Mail,
            ]
        )

    @staticmethod
    def to_iso_dt(dt_string):
        return datetime.datetime.strptime(dt_string, ISO_FORMAT)

    def print_db_status(self) -> None:
        """Prints the status of emails within the database.

        :rtype: None
        """
        print('='*50)
        print(f'[bold]Database:[/bold] {self.filename}')
        print(f'[bold]E-mail account:[/bold] {self.email}')
        print(f'[bold]Stored count:[/bold] {self.db_count}')
        s, e = [_.strftime('%Y-%m-%d') for _ in self.db_date_range]
        print(f'[bold]Stored range:[/bold] {s} -> {e}')
        print('[bold]Filter range:[/bold] {} <-> {}'.format(*self.filter_range))
        print(f'[bold]Filter keyword:[/bold] {self.filter_keyword}')
        print(f'[bold]Filter count:[/bold] {len(self.filtered_records)}')
        print('=' * 50)

    @property
    def db_count(self) -> int:
        return Mail.select().count()

    @property
    def db_date_range(self) -> Annotated[tuple, "from and to range"]:
        try:
            return (Mail.select().order_by(Mail.datetime).first().datetime,
                    Mail.select().order_by(Mail.datetime.desc()).first().datetime)
        except AttributeError:
            _ = datetime.datetime.now()
            return _, _

    def collect_mail(self) -> None:
        """Downloads all emails from account into database

        :return: None
        """
        credentials = Credentials(self.email, self.password)
        account = Account(self.email, credentials=credentials, autodiscover=True)
        fields = ("datetime", "sender", "to", "cc", "subject", "body")
        tot = account.inbox.total_count
        log.info(f"total items inbox {tot}")

        bail_out, passed = False, False
        for item in track(
            account.inbox.all().order_by("-datetime_received"), total=tot
        ):
            if bail_out:
                return
            try:
                f = nt("f", fields)(
                    self.to_iso_dt(str(item.datetime_received.strftime(ISO_FORMAT))),
                    f"{item.sender.name} <{item.sender.email_address}>",
                    ",".join([f"{_.name} <{_.email_address}>" for _ in item.to_recipients]),
                    str(item.display_cc),
                    item.subject,
                    item.body,
                )
            except TypeError as e:
                log.warn(f'Unable to process email, skipping: {item}')
            if Mail.select().where(Mail.datetime == f.datetime).count() == 0:
                try:
                    Mail.insert(**f._asdict()).execute()
                except IntegrityError as e:
                    log.warn(f'Unable to update db: {e.args}')
                    breakpoint()
            elif not passed:
                bail_out = 'y' in input('I have found existing e-mail stored, would you like to abort (y/n):').lower()
                passed = True

    @staticmethod
    def get_db_records(**kwargs) -> Annotated[tuple, "List of records"]:
        """

        :keyword int from_id: Filter from specific id
        :keyword int to_id: Filter to specific id
        :return:
        """
        f, t = kwargs.get("from_id", 0), kwargs.get("to_id", Mail.select().count())
        records = Mail.select().where((Mail.id >= f) & (Mail.id <= t)).dicts()
        return records

    def print_db_records_table(self, filtered: bool = False) -> None:
        """Prints a pretty table of records

        :param filtered: Print either filtered records or all
        """
        cols = Mail._meta.columns.keys()
        table = Table(show_header=True, header_style="bold magenta", min_width=300)
        for _ in cols:
            table.add_column(_)
        next(
            c for c in table.columns if c.header in ["body", "to", "sender"]
        ).width = 20
        if not filtered:
            items = self.get_db_records()
        else:
            items = self.filtered_records
        for _ in items:
            table.add_row(*[str(_[c])[:40] for c in cols])
        Console().print(table)

    def records_to_files(self, out: str = "./out", filtered: bool = False) -> None:
        """Exports records to html files

        :param out: Path to export to
        :param filtered: Either export filtered or all records
        """
        if filtered:
            items = self.filtered_records
        else:
            items = self.get_db_records()
        for r in items:
            fn = f"{r['datetime'].strftime('%y%m%d_%H%M')}"
            fn += f"__{r['sender'].split()[0]}__"
            fn += re.sub(r"[^\w]", "", f"{'_'.join(r['subject'].split()[:10])}")
            fn += f".html"
            Path(out).mkdir(parents=True, exist_ok=True)
            f = Path(out) / Path(fn)
            log.info(f"writing {f}")
            t = r["body"]
            if not '<html' in t:
                t = f'<meta http-equiv="Content-Type" content="text/html" charset="utf-8"/>{t}'.replace('\n', '<br>')
            f.write_text(t)

    def apply_filter(self) -> Annotated[tuple, "List of records"]:
        """Apply filter based on filter_keyword and filter_range criterias

        :return: List of records
        """
        search_word = self.filter_keyword
        from_to_date = self.filter_range
        if not any([search_word, any(from_to_date)]):
            self.filtered_records = Mail.select().dicts()
            return

        and_items = []

        if search_word:
            s = search_word.lower()
            or_items = [(Mail.to.contains(s)),
                        (Mail.sender.contains(s)),
                        (Mail.subject.contains(s)),
                        (Mail.body.contains(s))]
            item_expression = reduce(operator.or_, or_items)
            and_items.append(item_expression)

        if any(from_to_date):
            from_, to_ = from_to_date
            date_expression = (Mail.datetime >= from_) & (Mail.datetime <= to_)
            and_items.append(date_expression)

        if len(and_items) > 0:
            expression = reduce(operator.and_, and_items)
        else:
            expression = and_items[0]

        records = (
            Mail.select()
            .where(expression)
            .dicts()
        )
        logger.info(f"found {len(records)} records")
        self.filtered_records = records
        return records

    def select_records(self, filtered: bool = False, records: bool = None) -> Annotated[int, "id of selected record"]:
        """Supply a selection list and ability to pick one

        :param filtered: Only display filtered or all records
        :param records: Optional list of records as input
        :return: An ID of the record selected
        """
        if filtered:
            records = self.filtered_records
        elif not records:
            records = self.get_db_records()
        l = ["Exit"]
        l.extend(
            [
                f"{r['id']} - {r['datetime'].strftime('%y%m%d %H:%M')} - {r['subject']}"
                for r in records
            ]
        )
        print('='*79)
        cli = ScrollBar(
            prompt="Which one would you like to look at?", choices=l, height=10
        ).launch()
        i = next(iter(cli.split(" - ")))
        return i if i != "Exit" else None

    @staticmethod
    def format_html(input: Annotated[str, "HTML text"]) -> None:
        """Format and prints MarkDown from HTML within the terminal

        :param input: Input data HTML
        :return:
        """
        html = htmllaundry.sanitize(input, htmllaundry.cleaners.LineCleaner)
        m = md(html)
        lines = [line for line in m.split("\n") if line.strip() != ""]
        return "\n".join(lines[:40])

    def show_record(self, record_id: int) -> None:
        r = Mail.select().where(Mail.id == record_id).first()
        try:
            markdown = self.format_html(r.body)
        except AttributeError:
            return
        print("[white]_[/white]" * 50)
        print(f"[bold red]From:[/bold red] {r.sender}")
        print(f"[bold red]To:[/bold red] {r.to}")
        print(f"[bold red]Cc:[/bold red] {r.cc}")
        print(f"[bold red]Subject:[/bold red][bold yellow] {r.subject}[/bold yellow]")
        print("[white]_[/white]" * 50)
        print(markdown)
