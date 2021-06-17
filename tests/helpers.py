import datetime as dt

import pytest

# TODO remove static date from tests and store in this file
# TODO review the samples and see which ones are no longer needed,
# need to be adjusted or new ones are needed

utc = dt.timezone.utc
T_2021_5_26__3_55 = dt.datetime(2021, 5, 26, 3, 55)  # a Wednesday
T_2021_5_26__3_55_utc = dt.datetime(2021, 5, 26, 3, 55, tzinfo=utc)

CYCLIC_TYPE_ERROR_MSG = (
    "Wrong input for Cyclic! Select one of the following input types:\n"
    + "datetime.timedelta | list[datetime.timedelta]"
)
_DAILY_TYPE_ERROR_MSG = (
    "Wrong input for {0}! Select one of the following input types:\n"
    + "datetime.time | list[datetime.time]"
)
MINUTELY_TYPE_ERROR_MSG = _DAILY_TYPE_ERROR_MSG.format("Minutely")
HOURLY_TYPE_ERROR_MSG = _DAILY_TYPE_ERROR_MSG.format("Hourly")
DAILY_TYPE_ERROR_MSG = _DAILY_TYPE_ERROR_MSG.format("Daily")
WEEKLY_TYPE_ERROR_MSG = (
    "Wrong input for Weekly! Select one of the following input types:\n"
    + "DAY | list[DAY]\n"
    + "where `DAY = Weekday | tuple[Weekday, dt.time]`"
)

_TZ_ERROR_MSG = "Can't use offset-naive and offset-aware datetimes together for {0}."
TZ_ERROR_MSG = _TZ_ERROR_MSG[:-9] + "."


@pytest.fixture
def patch_datetime_now(monkeypatch, request):
    class DatetimePatch:
        it = iter(request.param)

        @classmethod
        def now(cls, tz=None):
            return next(cls.it)

    monkeypatch.setattr(dt, "datetime", DatetimePatch)


samples = [
    T_2021_5_26__3_55,  # scheduler init
    T_2021_5_26__3_55,  # job creation
    T_2021_5_26__3_55 + dt.timedelta(seconds=5),  # t1
    T_2021_5_26__3_55 + dt.timedelta(seconds=8),  # t2
    T_2021_5_26__3_55 + dt.timedelta(seconds=11),  # t3
    T_2021_5_26__3_55 + dt.timedelta(hours=1, minutes=3),  # t4
    T_2021_5_26__3_55 + dt.timedelta(hours=2, minutes=2),  # t5
    T_2021_5_26__3_55 + dt.timedelta(days=1, minutes=2),  # t6
    T_2021_5_26__3_55 + dt.timedelta(days=9, minutes=7),  # t7
    T_2021_5_26__3_55 + dt.timedelta(days=10, minutes=7),  # t8
]

samples_once_datetime = [
    T_2021_5_26__3_55,  # scheduler init
    T_2021_5_26__3_55 + dt.timedelta(seconds=5),  # t1
    T_2021_5_26__3_55 + dt.timedelta(seconds=6),  # t2
    T_2021_5_26__3_55 + dt.timedelta(seconds=7),  # t3
    T_2021_5_26__3_55 + dt.timedelta(seconds=8),  # t4
    T_2021_5_26__3_55 + dt.timedelta(days=9, minutes=1),  # t5
    T_2021_5_26__3_55 + dt.timedelta(days=9, minutes=2),  # t6
    T_2021_5_26__3_55 + dt.timedelta(days=9, minutes=7),  # t7
]

samples_seconds = [
    T_2021_5_26__3_55,  # scheduler creation
    T_2021_5_26__3_55,  # job creation
    T_2021_5_26__3_55 + dt.timedelta(seconds=5),  # t1
    T_2021_5_26__3_55 + dt.timedelta(seconds=8),  # t2
    T_2021_5_26__3_55 + dt.timedelta(seconds=11),  # t3
    T_2021_5_26__3_55 + dt.timedelta(seconds=11),  # t4
    T_2021_5_26__3_55 + dt.timedelta(seconds=14.999),  # t5
    T_2021_5_26__3_55 + dt.timedelta(seconds=15),  # t6
    T_2021_5_26__3_55 + dt.timedelta(seconds=15.001),  # t7
    T_2021_5_26__3_55 + dt.timedelta(seconds=15.002),  # t8
]

samples_days = [
    T_2021_5_26__3_55,  # scheduler creation
    T_2021_5_26__3_55,  # job creation
    T_2021_5_26__3_55 + dt.timedelta(days=1, seconds=5),  # t1
    T_2021_5_26__3_55 + dt.timedelta(days=1, seconds=8),  # t2
    T_2021_5_26__3_55 + dt.timedelta(days=3, seconds=11),  # t3
    T_2021_5_26__3_55 + dt.timedelta(days=4, seconds=11),  # t4
    T_2021_5_26__3_55 + dt.timedelta(days=10, seconds=5.999),  # t5
    T_2021_5_26__3_55 + dt.timedelta(days=10, seconds=6),  # t6
    T_2021_5_26__3_55 + dt.timedelta(days=10, seconds=6.001),  # t7
    T_2021_5_26__3_55 + dt.timedelta(days=11, seconds=6.002),  # t8
]

samples_job_creation = [
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
    T_2021_5_26__3_55,
]


def foo(msg="foo"):
    print(msg)


def bar(msg="bar"):
    print(msg)
