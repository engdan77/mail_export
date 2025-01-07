import time
from exchangelib import Credentials, Account, Configuration, DELEGATE
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
from lxml_html_clean import clean_html
from markdownify import markdownify as md
import operator
from functools import reduce
from typing import Annotated, NamedTuple

ISO_FORMAT = "%Y-%m-%d %H:%M:%S"
database_proxy = DatabaseProxy()


class Mail(Model):
    datetime = DateTimeField()
    to = TextField()
    sender = TextField()
    cc = TextField(null=True)
    subject = TextField(null=True)
    body = TextField(null=True)
    folder = TextField(null=True)

    class Meta:
        database = database_proxy


class Email:
    def __init__(
        self,
        /,
        database="emails.sqlite",
        email=None,
        password=None,
        server_name=None,
        username=None,
        archive_folders=None,
        download_now=None,
        purge_mail_older_than=None,
    ):
        self.filter_keyword = ""
        self.filter_range = None, None
        self.filter_folder = None
        self.filename = database
        self.db = SqliteDatabase(self.filename)
        database_proxy.initialize(self.db)
        self.email = email
        self.password = password
        self.server_name = server_name
        self.username = username
        self.archive_folders = archive_folders
        self.filtered_records = []
        self.download_now = download_now
        self.purge_older_than = purge_mail_older_than

        self.db.create_tables(
            [
                Mail,
            ]
        )

    @staticmethod
    def to_iso_dt(dt_string) -> datetime.datetime:
        """Parse datetime

        :param dt_string: Raw datetime string
        :return:
        """
        return datetime.datetime.strptime(dt_string, ISO_FORMAT)

    def print_db_status(self) -> None:
        """Prints the status of emails within the database.

        :rtype: None
        """
        print("=" * 50)
        print(f"[bold]Database:[/bold] {self.filename}")
        print(f"[bold]E-mail account:[/bold] {self.email}")
        print(f"[bold]Stored count:[/bold] {self.db_count}")
        s, e = [_.strftime("%Y-%m-%d") for _ in self.db_date_range]
        print(f"[bold]Stored range:[/bold] {s} -> {e}")
        print(f"[bold]Filter folder:[/bold] {self.filter_folder}")
        print("[bold]Filter range:[/bold] {} <-> {}".format(*self.filter_range))
        print(f"[bold]Filter keyword:[/bold] {self.filter_keyword}")
        print(f"[bold]Filter count:[/bold] {len(self.filtered_records)}")
        print("=" * 50)

    @property
    def db_count(self) -> int:
        """Count DB records

        :return: count
        """
        return Mail.select().count()

    @property
    def db_date_range(self) -> Annotated[tuple, "from and to range"]:
        """Return a from, to for the range of emails in DB

        :return: from, to tuple
        """
        try:
            return (
                Mail.select().order_by(Mail.datetime).first().datetime,
                Mail.select().order_by(Mail.datetime.desc()).first().datetime,
            )
        except AttributeError:
            _ = datetime.datetime.now()
            return _, _

    @property
    def db_get_folders(self) -> Annotated[tuple, "folder"]:
        """Return list of folders"""
        return tuple(_.folder for _ in Mail.select(Mail.folder).group_by(Mail.folder))

    def process_mail(self) -> None:
        """Downloads all emails from account into database

        :return: None
        """

        if all((self.server_name, self.username, self.email)):
            credentials = Credentials(username=self.username, password=self.password)
            config = Configuration(server=self.server_name, credentials=credentials)
            account = Account(
                primary_smtp_address=self.email,
                config=config,
                autodiscover=False,
                access_type=DELEGATE,
            )
        else:
            credentials = Credentials(self.email, self.password)
            account = Account(self.email, credentials=credentials, autodiscover=True)
        fields = ("datetime", "sender", "to", "cc", "subject", "body")

        download_folders = {"Inbox": account.inbox, "Sent": account.sent}

        if self.archive_folders:
            for folder in self.archive_folders.split(","):
                download_folders[f"Archive/{folder}"] = (
                    account.archive_msg_folder_root / folder
                )

        for folder, func in reversed(list(download_folders.items())):
            count = func.total_count
            log.info(f'processing folder "{folder}" with {count} items')
            bail_out, passed = False, False
            counter = 0
            tot = func.total_count
            # for item in track(func.all().order_by("-datetime_received"), total=tot):
            mail_iterator = iter(func.all().order_by("-datetime_received"))
            try:
                while True:
                    try:
                        item = next(mail_iterator)
                    except KeyError as e:
                        log.warning(f"error parsing email: {e}")
                        time.sleep(10)
                        continue
                    counter += 1
                    log.info(f"processing {counter}/{tot} in folder {folder}")
                    if bail_out:
                        return
                    try:
                        mail_fields = self.extract_email_items(fields, item)
                    except TypeError:
                        log.warn(f"Unable to process email, skipping: {item}")
                        continue
                    except AttributeError as e:
                        log.warn(f"{e.args} - skipping")
                        continue
                    if self.purge_older_than:
                        log.info(f"purging {counter}/{tot}")
                        if mail_fields.datetime <= (
                            datetime.datetime.now()
                            - datetime.timedelta(days=self.purge_older_than)
                        ):
                            self.purge_email_from_server(item, mail_fields, folder)
                        else:
                            log.info(f"skipping item {counter}, not within range")
                    else:
                        bail_out, passed = self.store_mail_to_db(
                            mail_fields, folder, passed, bail_out
                        )
            except StopIteration:
                log.info("completed!!!")

    @staticmethod
    def purge_email_from_server(item, mail_fields, folder):
        log.info(
            f"purging mail in {folder} [{mail_fields.datetime}] {mail_fields.subject}"
        )
        try:
            item.delete()
        except Exception as e:
            log.warning(f"failed removing due to {e.args}")

    def store_mail_to_db(self, mail_fields, current_folder, passed, bail_out_flag):
        if Mail.select().where(Mail.datetime == mail_fields.datetime).count() == 0:
            try:
                Mail.insert(**mail_fields._asdict(), folder=current_folder).execute()
            except IntegrityError as e:
                log.warn(f"Unable to update db: {e.args}")
                breakpoint()
        elif not self.download_now and not passed:
            bail_out_flag = (
                "y"
                in input(
                    "I have found existing e-mail stored, would you like to abort (y/n):"
                ).lower()
            )
            passed = True
        return bail_out_flag, passed

    def add_record(self, input_dict):
        Mail.insert(**input_dict).execute()

    def extract_email_items(self, fields, item) -> NamedTuple:
        f: NamedTuple = nt("f", fields)(
            self.to_iso_dt(str(item.datetime_received.strftime(ISO_FORMAT))),
            f"{item.sender.name} <{item.sender.email_address}>",
            ",".join([f"{_.name} <{_.email_address}>" for _ in item.to_recipients]),
            str(item.display_cc),
            item.subject,
            item.body,
        )
        return f

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

    # noinspection PyProtectedMember
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
            fn_ = f"{r['datetime'].strftime('%y%m%d_%H%M')}"
            fn_ += f"__{r['sender'].split()[0]}__"
            fn_ += re.sub(r"[^\w]", "", f"{'_'.join(r['subject'].split()[:10])}")
            fn_ += f".html"
            Path(out).mkdir(parents=True, exist_ok=True)
            f = Path(out) / Path(fn_)
            log.info(f"writing {f}")
            t = r["body"]
            if "<html" not in t:
                t = f'<meta http-equiv="Content-Type" content="text/html" charset="utf-8"/>{t}'.replace(
                    "\n", "<br>"
                )
            f.write_text(t)

    def apply_filter(self) -> Annotated[tuple, "List of records"]:
        """Apply filter based on filter_keyword and filter_range criteria

        :return: List of records
        """
        search_word = self.filter_keyword
        from_to_date = self.filter_range
        folder = self.filter_folder
        if not any([folder, search_word, any(from_to_date)]):
            self.filtered_records = Mail.select().dicts()
            return self.filtered_records

        and_items = []

        if search_word:
            s = search_word.lower()
            or_items = [
                (Mail.to.contains(s)),
                (Mail.sender.contains(s)),
                (Mail.subject.contains(s)),
                (Mail.body.contains(s)),
            ]
            item_expression = reduce(operator.or_, or_items)
            and_items.append(item_expression)

        if any(from_to_date):
            from_, to_ = from_to_date
            date_expression = (Mail.datetime >= from_) & (Mail.datetime <= to_)
            and_items.append(date_expression)

        log.debug(f"filtering on folder {folder}")
        if folder:
            and_items.append((Mail.folder == folder))

        if len(and_items) > 0:
            expression = reduce(operator.and_, and_items)
        else:
            expression = and_items[0]

        records = Mail.select().where(expression).dicts()
        log.info(f"found {len(records)} records")
        self.filtered_records = records
        return records

    def select_records(
        self, filtered: bool = False, records: bool = None
    ) -> Annotated[int, "id of selected record"]:
        """Supply a selection list and ability to pick one

        :param filtered: Only display filtered or all records
        :param records: Optional list of records as input
        :return: An ID of the record selected
        """
        if filtered:
            records = self.filtered_records
        elif not records:
            records = self.get_db_records()
        choices = ["Exit"]
        choices.extend(
            [
                f"{r['id']} - {r['datetime'].strftime('%y%m%d %H:%M')} - [{r['folder']}] {r['subject']}"
                for r in records
            ]
        )
        print("=" * 79)
        cli = ScrollBar(
            prompt="Which one would you like to look at?", choices=choices, height=10
        ).launch()
        i = next(iter(cli.split(" - ")))
        return i if i != "Exit" else None

    @staticmethod
    def format_html(input_: Annotated[str, "HTML text"]) -> str:
        """Format and prints MarkDown from HTML within the terminal

        :param input_: Input data HTML
        :return:
        """
        # html = htmllaundry.sanitize(input_, htmllaundry.cleaners.LineCleaner)
        from lxml_html_clean import clean_html
        html = clean_html(input_)
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
        print(f"[bold red]Folder:[/bold red] {r.folder}")
        print(f"[bold red]From:[/bold red] {r.sender}")
        print(f"[bold red]To:[/bold red] {r.to}")
        print(f"[bold red]Cc:[/bold red] {r.cc}")
        print(f"[bold red]Subject:[/bold red][bold yellow] {r.subject}[/bold yellow]")
        print("[white]_[/white]" * 50)
        print(markdown)
