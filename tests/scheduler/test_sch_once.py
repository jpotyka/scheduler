import datetime as dt

import pytest

from scheduler import Scheduler, SchedulerError
from scheduler.job import Job
from scheduler.util import Weekday

from helpers import utc, ONCE_TYPE_ERROR_MSG, TZ_ERROR_MSG, samples, samples_utc, foo


@pytest.mark.parametrize(
    "timing, counts, patch_datetime_now, tzinfo, err_msg",
    (
        [
            dt.timedelta(seconds=8),
            [0, 1, 1, 1, 1, 1, 1, 1],
            samples,
            None,
            None,
        ],
        [
            dt.timedelta(seconds=9.5),
            [0, 0, 1, 1, 1, 1, 1, 1],
            samples_utc,
            utc,
            None,
        ],
        [
            dt.timedelta(days=10),
            [0, 0, 0, 0, 0, 0, 0, 1],
            samples,
            None,
            None,
        ],
        [
            Weekday.THURSDAY,
            [0, 0, 0, 0, 0, 1, 1, 1],
            samples,
            None,
            None,
        ],
        [
            dt.time(hour=5, minute=57, tzinfo=utc),
            [0, 0, 0, 0, 1, 1, 1, 1],
            samples_utc,
            utc,
            None,
        ],
        [
            (Weekday.THURSDAY, dt.time(hour=3, minute=57, tzinfo=utc)),
            [0, 0, 0, 0, 0, 1, 1, 1],
            samples_utc,
            utc,
            None,
        ],
        [
            (Weekday.THURSDAY, dt.time(hour=3, minute=57, tzinfo=None)),
            [0, 0, 0, 0, 0, 1, 1, 1],
            samples_utc,
            utc,
            TZ_ERROR_MSG,
        ],
        [[dt.time(), dt.timedelta()], [], samples, None, ONCE_TYPE_ERROR_MSG],
    ),
    indirect=["patch_datetime_now"],
)
def test_once(timing, counts, patch_datetime_now, tzinfo, err_msg):
    sch = Scheduler(tzinfo=tzinfo)

    if err_msg:
        with pytest.raises(SchedulerError) as msg:
            job = sch.once(timing=timing, handle=foo)
            assert msg == err_msg
    else:
        job = sch.once(timing=timing, handle=foo)
        for count in counts:
            sch.exec_jobs()
            assert job.attempts == count