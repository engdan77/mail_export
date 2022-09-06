# Mail Export

### Background

While migrating from one online Exchange provider to another I was searching for a convinient method for exporting/archiving all my existing e-mails.
At the same time being able to easily search within this archive and read those wihin the console (parse HTML) and also save those into HTML-files when needed to remove dependencies to this application.
I chose to store those e-mails to a SQLite database being a portable format.

### Installation

```shell
$ pip install git+https://github.com/engdan77/mail_export.git
```

### Demo

[![asciicast](https://asciinema.org/a/b4gPeoUZn342aqhYPRvWlDrW3.svg)](https://asciinema.org/a/b4gPeoUZn342aqhYPRvWlDrW3)

### Usage

#### Using the menu system to access stored e-mails

```shell
$ mail_export --database ~/mail.sqlite

==================================================
Database: /Users/foo/mail.sqlite
E-mail account: foo@ebar.com
Stored count: 3726
Stored range: 2017-01-02 -> 2021-03-04
Filter range: 2020-01-01 <-> 2020-12-01
Filter keyword: regards
Filter count: 4
==================================================

Choose:

 ●Exit
 E-mail settings
 Update date range filter
 Update keyword filter
 Reset filters
 Show filtered e-mails
 Save filtered e-mails to folder
 Download from account
```

#### Example for downloading e-mail from specific server without auto-detec

```shell
$ mail_export --database mail.sqlite --email "daniel@engvalls.eu" --password "MyPassword" --server_name my.server.com --username "MyDomain\daniel" --archive_folders "Inbox,Sent Items" --download_now
```

#### Get help

```shell
$ mail_export --help                                                                                                                                               21  15:01
usage: __main__.py [-h] [--database DATABASE] [--email EMAIL] [--password PASSWORD] [--server_name SERVER_NAME] [--username USERNAME] [--archive_folders ARCHIVE_FOLDERS] [--download_now]

Application for creating a local copy of your exchange mail account

options:
  -h, --help            show this help message and exit
  --database DATABASE   SQLite database file to store to
  --email EMAIL         E-mail to download from
  --password PASSWORD   Password for e-mail account
  --server_name SERVER_NAME
                        (Optional) Server to download from and will disable auto-discover mode
  --username USERNAME   (Optional) Domain\Username user with server_name
  --archive_folders ARCHIVE_FOLDERS
                        (Optional) Comma-separated list of archive folders to download
  --download_now        Bypass menu and download immediately
```


### Run unittests and coverage

```shell script
$ pytest && pytest --cov ./exchange
```

### Troubleshooting

If you get an error related to installation of _cryptography_ package in MacOS and Python 3.10 you may try the following

```shell
env LDFLAGS="-L$(brew --prefix openssl@1.1)/lib" CFLAGS="-I$(brew --prefix openssl@1.1)/include" pipx install --verbose git+https://github.com/engdan77/mail_export.git
```