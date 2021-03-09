import datetime

import pytest
from unittest.mock import Mock, MagicMock, patch
from exchange import Email
from collections import namedtuple as nt
from functools import wraps
from peewee import SqliteDatabase
import re


def with_test_db(dbs: tuple):
    """A decorator to simplify testing if Peewee
    https://www.dvlv.co.uk/a-super-helpful-decorator-for-peeweeflask-unit-testing.html

    :param dbs:
    :return:
    """
    def decorator(func):
        @wraps(func)
        def test_db_closure(*args, **kwargs):
            test_db = SqliteDatabase(":memory:")
            with test_db.bind_ctx(dbs):
                test_db.create_tables(dbs)
                try:
                    func(*args, **kwargs)
                finally:
                    test_db.drop_tables(dbs)
                    test_db.close()
        return test_db_closure
    return decorator


@pytest.fixture()
def mocked_email_db():
    email = Email(database=':memory:')
    return email


@pytest.fixture()
def mocked_data(faker):
    fields = ("datetime", "sender", "to", "cc", "subject", "body")
    # email_mock = Mock()
    # email_mock.configure_mock(name=faker.email(), email_address=faker.email())
    data = nt('email', fields)(faker.date_time().strftime('%Y-%m-%d %H:%M:%S'),
                               faker.email(),
                               faker.email(),
                               '',
                               faker.text(50),
                               faker.text(90))
    return data


def test_to_iso_dt(mocked_email_db):
    assert mocked_email_db.to_iso_dt('2021-01-01 01:00:00') == datetime.datetime(2021, 1, 1, 1, 0)


def test_print_db_status(capsys, mocked_email_db):
    mocked_email_db.print_db_status()
    out, err = capsys.readouterr()
    assert 'Database:' in out


def test_collect_mail(mocker, faker, mocked_email_db: Mock, mocked_data):
    mocker.patch('exchange.api.Credentials', return_value=MagicMock())

    # method needs Mock while property no
    inbox_mock = Mock(total_count=2, all=Mock(return_value=Mock(order_by=Mock(return_value=[mocked_data]))))
    account_mock = Mock(inbox=inbox_mock)
    mocker.patch('exchange.api.Account', return_value=account_mock)
    mocker.patch('exchange.api.Email.extract_email_items', return_value=mocked_data)
    mocker.patch('exchange.api.Mail',
                 select=Mock(return_value=Mock(where=Mock(return_value=Mock(count=Mock(return_value=0))))))
    mocker.patch('datetime.datetime', return_value=faker.date_time())
    mocked_email_db.collect_mail()
    assert mocked_email_db.extract_email_items.called is True


def test_print_db_records_table(capsys, mocked_email_db, mocked_data):
    mocked_email_db.add_record(mocked_data._asdict())
    mocked_email_db.print_db_records_table()
    out, err = capsys.readouterr()
    print(out)
    assert re.search(r'\S+@\S+', out), 'No email found in output'
