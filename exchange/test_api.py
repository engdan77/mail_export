import datetime

import pytest
from unittest.mock import Mock, MagicMock, patch
from exchange import Email
from collections import namedtuple as nt

@pytest.fixture()
def mocked_email_db():
    email = Email(database=':memory:')
    return email

@pytest.fixture()
def mocked_data(faker):
    fields = ("datetime", "sender", "to", "cc", "subject", "body")
    data = nt('email', fields)(faker.iso8601(),
                                   faker.email(),
                                   faker.email(),
                                   None,
                                   faker.text(50),
                                   faker.text(90))
    return Mock(**data._asdict())


def test_to_iso_dt(mocked_email_db):
    assert mocked_email_db.to_iso_dt('2021-01-01 01:00:00') == datetime.datetime(2021, 1, 1, 1, 0)


def test_print_db_status(capsys, mocked_email_db):
    mocked_email_db.print_db_status()
    out, err = capsys.readouterr()
    assert 'Database:' in out


def test_collect_mail(mocker, faker, mocked_email_db, mocked_data):
    mocker.patch('exchange.api.Credentials', return_value=MagicMock())

    # method needs Mock while property no
    inbox_mock = Mock(total_count=2, all=Mock(return_value=Mock(order_by=Mock(return_value=mocked_data))))
    account_mock = Mock(inbox=inbox_mock)
    mocker.patch('exchange.api.Account', return_value=account_mock)
    mocker.patch('exchange.api.nt', return_value=mocked_data)



    # mocker.patch.object('exchange.api.account', return_value=2)
    # mocker.patch('exchange.api.account', return_value=['foo', 'bar'])


    mocked_email_db.collect_mail()
    assert False
