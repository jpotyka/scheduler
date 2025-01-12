import datetime as dt
import logging

import pytest
from ...helpers import fail, samples_seconds, ZERO_DIVISION_ERROR

from scheduler import Scheduler


@pytest.mark.parametrize(
    "timing, counts, patch_datetime_now",
    ([dt.timedelta(seconds=4), [1, 2], samples_seconds],),
    indirect=["patch_datetime_now"],
)
def test_threading_fail(timing, counts, patch_datetime_now, caplog):
    caplog.set_level(logging.DEBUG, logger="scheduler")

    sch = Scheduler()
    job = sch.cyclic(timing=timing, handle=fail)
    RECORD = (
        "scheduler",
        logging.ERROR,
        "Unhandled exception `%s` in `%r`!"
        % (
            ZERO_DIVISION_ERROR,
            job,
        ),
    )

    for count in counts:
        sch.exec_jobs()
        assert job.attempts == count
        assert job.failed_attempts == count

    assert caplog.record_tuples == [RECORD, RECORD]
