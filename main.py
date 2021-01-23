import os
from richlog import log
from rich.traceback import install
from rich import print
from exchange import Email

install()


if __name__ == "__main__":
    print(f"Welcome to [bold red]owa exporter[/bold red] :smile:")

    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")
    store = Email(email=email, password=password)

    # store.collect_mail()
    # store.get_db_records()
    store.print_db_records_table()
    # store.records_to_files()
    records = store.find_records("Daniel")
    s = store.select_records(records)
    store.show_record(s)
