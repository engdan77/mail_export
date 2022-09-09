import os
import sys

from rich.traceback import install
from rich.console import Console
from exchange import Email
import argparse
from loguru import logger
from bullet import Bullet, Input, Password, SlidePrompt, ScrollBar
from collections import namedtuple

install()  # install rich print

dt = namedtuple("dt", "text pattern")("YYYY-MM-DD", "(\d{4}-\d{2}-\d{2})|^$")


def get_args() -> argparse.Namespace:
    """Get command arguments.

    :rtype: args
    """
    parser = argparse.ArgumentParser(
        description="Application for creating a local copy of your exchange mail account"
    )
    parser.add_argument(
        "--database",
        type=str,
        default="emails.sqlite",
        help="SQLite database file to store to",
    )
    parser.add_argument("--email", type=str, help="E-mail to download from")
    parser.add_argument("--password", type=str, help="Password for e-mail account")
    parser.add_argument(
        "--server_name",
        type=str,
        help="(Optional) Server to download from and will disable auto-discover mode",
    )
    parser.add_argument(
        "--username", type=str, help="(Optional) Domain\\Username user with server_name"
    )
    parser.add_argument(
        "--archive_folders",
        type=str,
        help="(Optional) Comma-separated list of archive folders to download",
    )
    parser.add_argument(
        "--download_now",
        action="store_true",
        help="Bypass menu and download immediately",
    )
    parser.add_argument(
        "--purge_mail_older_than",
        type=int,
        help="(Optional) Instead of download mail, remove it if older than X days",
    )
    args = parser.parse_args()
    if args.download_now and args.purge_mail_older_than:
        print(
            "ERROR: You cannot use --download_now and --purge_mail_older_than at the same time"
        )
        sys.exit(1)
    for _ in ("email", "password"):
        if getattr(args, _, None) is None:
            setattr(args, _, os.environ.get(_.upper(), None))
    return args


def bitem(bullet_item) -> str:
    """Helper function for selecting email.

    :param bullet_item:
    :return:
    """
    return next(iter(bullet_item.split(" - ")))


class Menu:
    def __init__(self, args, email: Email):
        self.args = args
        self.email = email

    def info(self) -> None:
        """Display info in menu"""
        self.email.print_db_status()

    def main(self) -> None:
        """Main menu"""
        while True:
            Console().clear()
            self.email.apply_filter()
            self.info()
            items = {
                "Exit": exit,
                "E-mail settings": self.get_mail_creds,
                "Update date range filter": self.get_range,
                "Update folder to filter": self.get_folder,
                "Update keyword filter": self.get_search_word,
                "Reset filters": self.reset_filters,
                "Show filtered e-mails": self.display_filtered_email,
                "Save filtered e-mails to folder": self.save_filtered_emails,
            }
            if all([self.email.email, self.email.password]):
                items["Download from account"] = self.email.process_mail
            cli = Bullet(prompt="Choose:", choices=list(items.keys())).launch()
            items.get(cli)()

    def get_mail_creds(self) -> list:
        """Return credentials.

        :return: List with username and password
        """
        cli = SlidePrompt([Input("E-mail address: "), Password("Password: ")]).launch()
        v = dict(cli).values()
        self.email.email, self.email.password = v
        return cli

    def get_range(self) -> None:
        """Get and set date range filter."""

        cli = SlidePrompt(
            [
                Input(prompt=f"From date [{dt.text}]: ", pattern=dt.pattern),
                Input(prompt=f"To date [{dt.text}]: ", pattern=dt.pattern),
            ]
        ).launch()
        self.email.filter_range = [_[-1] for _ in cli]

    def get_folder(self) -> None:
        """Get folder to filter"""

        current_folders = self.email.db_get_folders
        cli = ScrollBar(
            prompt="Which folder would you like to filter?",
            choices=current_folders,
            height=10,
        ).launch()
        self.email.filter_folder = cli

    def get_search_word(self) -> None:
        """Get and set search for to filter."""

        words = input("What filter words to use: ")
        self.email.filter_keyword = words

    def reset_filters(self) -> None:
        """Reset filters."""

        self.email.filter_keyword = None
        self.email.filter_range = None, None
        self.email.filter_folder = None

    def display_filtered_email(self) -> None:
        """Display those filtered emails."""

        while True:
            record = self.email.select_records(filtered=True)
            if record is None:
                break
            self.email.show_record(record)

    def save_filtered_emails(self) -> None:
        """Save filtered emails as files."""

        self.email.print_db_records_table(filtered=True)
        folder = input(f"Export folder: ")
        self.email.records_to_files(out=folder, filtered=True)


def init_log() -> None:
    """Initialize logging"""
    logger.remove()
    logger.add("app.log", rotation="100 MB")
    logger.level("DEBUG")


def main():
    init_log()
    args = get_args()
    email = Email(**args.__dict__)
    if args.download_now or args.purge_mail_older_than:
        email.process_mail()
        exit(0)
    menu = Menu(args, email)
    menu.main()


if __name__ == "__main__":
    main()
