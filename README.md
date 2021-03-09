# Mail Export

#### Background

While migrating from one online Exchange provider to another I was searching for a convinient method for exporting/archiving all my existing e-mails.
At the same time being able to easily search within this archive and read those wihin the console (parse HTML) and also save those into HTML-files when needed to remove dependencies to this application.
I chose to store those e-mails to a SQLite database being a portable format.

#### Installation

```shell
$ pip install git+https://github.com/engdan77/mail_export.git
```



#### Sample usage

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



#### Run unittests and coverage

```shell script
$ pytest && pytest --cov ./exchange
```