"""
Implementation of a `Job` as callback function represention.

Author: Jendrik A. Potyka, Fabian A. Preiss
"""
from __future__ import annotations

import datetime as dt
import threading

from typing import Callable, Optional, Union, Any, cast

import typeguard as tg

from scheduler.util import (
    TZ_ERROR_MSG,
    JobType,
    AbstractJob,
    SchedulerError,
    Weekday,
    next_minutely_occurrence,
    next_hourly_occurrence,
    next_daily_occurrence,
    next_weekday_occurrence,
    next_weekday_time_occurrence,
    prettify_timedelta,
    are_times_unique,
    are_weekday_times_unique,
)

# execution interval
TimingTypeCyclic = dt.timedelta
# time on the clock
TimingTypeDaily = Union[dt.time, list[dt.time]]

# day of the week or time on the clock
_TimingTypeDay = Union[Weekday, tuple[Weekday, dt.time]]
TimingTypeWeekly = Union[_TimingTypeDay, list[_TimingTypeDay]]

TimingJobTimerUnion = Union[dt.timedelta, dt.time, _TimingTypeDay]
TimingJobUnion = Union[TimingTypeCyclic, TimingTypeDaily, TimingTypeWeekly]

# specify point in time, distance to reference time, day of the week or time on the clock
TimingTypeOnce = Union[
    dt.datetime, dt.timedelta, Weekday, dt.time, tuple[Weekday, dt.time]
]

DUPLICATE_EFFECTIVE_TIME = "Times that are effectively identical are not allowed."

CYCLIC_TYPE_ERROR_MSG = (
    "Wrong input for Cyclic! Expected input type:\n" + "datetime.timedelta"
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


_TZ_ERROR_MSG = TZ_ERROR_MSG[:-1] + " for {0}."

START_STOP_ERROR = "Start argument must be smaller than the stop argument."


JOB_TIMING_TYPE_MAPPING = {
    JobType.CYCLIC: {"type": TimingTypeCyclic, "err": CYCLIC_TYPE_ERROR_MSG},
    JobType.MINUTELY: {"type": TimingTypeDaily, "err": MINUTELY_TYPE_ERROR_MSG},
    JobType.HOURLY: {"type": TimingTypeDaily, "err": HOURLY_TYPE_ERROR_MSG},
    JobType.DAILY: {"type": TimingTypeDaily, "err": DAILY_TYPE_ERROR_MSG},
    JobType.WEEKLY: {"type": TimingTypeWeekly, "err": WEEKLY_TYPE_ERROR_MSG},
}

JOB_NEXT_DAYLIKE_MAPPING = {
    JobType.MINUTELY: next_minutely_occurrence,
    JobType.HOURLY: next_hourly_occurrence,
    JobType.DAILY: next_daily_occurrence,
}


class JobTimer:
    """
    The class provides the internal `datetime.datetime` calculations for a `Job`.

    Parameters
    ----------
    job_type : JobType
        Indicator which defines which calculations has to be used.
    timing : TimingJobTimerUnion
        Desired execution time(s).
    start : datetime.datetime
        Timestamp reference from which future executions will be calculated.
    skip_missing : bool
        If ``True`` a |Job| will only schedule it's newest planned
        execution and drop older ones.
    """

    def __init__(
        self,
        job_type: JobType,
        timing: TimingJobTimerUnion,
        start: dt.datetime,
        skip_missing: bool = False,
    ):
        self.__lock = threading.RLock()
        self.__job_type = job_type
        self.__timing = timing
        self.__next_exec = start
        self.__skip = skip_missing

    def calc_next_exec(self, ref: Optional[dt.datetime] = None) -> None:
        """
        Generate the next execution `datetime.datetime` stamp.

        Parameters
        ----------
        ref : Optional[datetime.datetime]
            Datetime reference for scheduling the next execution datetime.
        """
        with self.__lock:
            if self.__job_type == JobType.CYCLIC:
                if self.__skip and ref is not None:
                    self.__next_exec = ref
                self.__next_exec = self.__next_exec + cast(dt.timedelta, self.__timing)
                return

            if self.__job_type == JobType.WEEKLY:
                #  check for _TimingTypeDay = Union[Weekday, tuple[Weekday, dt.time]]
                if isinstance(self.__timing, Weekday):
                    self.__next_exec = next_weekday_occurrence(
                        self.__next_exec, self.__timing
                    )
                else:
                    self.__timing = cast(tuple[Weekday, dt.time], self.__timing)
                    if self.__timing[1].tzinfo:
                        self.__next_exec = self.__next_exec.astimezone(
                            self.__timing[1].tzinfo
                        )
                    self.__next_exec = next_weekday_time_occurrence(
                        self.__next_exec, *self.__timing
                    )

            else:  # self.__job_type in JOB_NEXT_DAYLIKE_MAPPING:
                self.__timing = cast(dt.time, self.__timing)
                if self.__next_exec.tzinfo:
                    self.__next_exec = self.__next_exec.astimezone(self.__timing.tzinfo)
                self.__next_exec = JOB_NEXT_DAYLIKE_MAPPING[self.__job_type](
                    self.__next_exec, self.__timing
                )

            if self.__skip and ref is not None and self.__next_exec < ref:
                self.__next_exec = ref
                self.calc_next_exec()

    @property
    def datetime(self) -> dt.datetime:
        """
        Get the `datetime.datetime` object for the planed execution.

        Returns
        -------
        datetime.datetime
            Execution `datetime.datetime` stamp.
        """
        return self.__next_exec

    def timedelta(self, dt_stamp: dt.datetime) -> dt.timedelta:
        """
        Get the `datetime.timedelta` until the execution of this `Job`.

        Parameters
        ----------
        dt_stamp : datetime.datetime
            Time to be compared with the planned execution time
            to determine the time difference.

        Returns
        -------
        datetime.timedelta
            `datetime.timedelta` to the execution.
        """
        return self.__next_exec - dt_stamp


class JobUtil:
    @staticmethod
    def sane_timing_types(job_type: JobType, timing: TimingJobUnion) -> None:
        """
        Determine if the `JobType` is fulfilled by the type of the specified `timing`.

        Parameters
        ----------
        job_type : JobType
            :class:`~scheduler.job.JobType` to test agains.
        timing : TimingJobUnion
            The `timing` object to be tested.

        Raises
        ------
        TypeError
            If the `timing` object has the wrong `Type` for a specific `JobType`.
        """
        try:
            tg.check_type("timing", timing, JOB_TIMING_TYPE_MAPPING[job_type]["type"])
        except TypeError as err:
            raise SchedulerError(JOB_TIMING_TYPE_MAPPING[job_type]["err"]) from err

    @staticmethod
    def standardize_timing_format(
        job_type: JobType, timing: TimingJobUnion, tzinfo: Optional[dt.tzinfo]
    ) -> tuple[TimingJobUnion, Optional[list[tuple[Weekday, dt.time]]]]:
        if isinstance(timing, list):
            if job_type is JobType.MINUTELY:
                timing = [
                    time.replace(hour=0, minute=0)
                    for time in cast(list[dt.time], timing)
                ]
            elif job_type is JobType.HOURLY:
                timing = [time.replace(hour=0) for time in cast(list[dt.time], timing)]
            elif job_type is JobType.WEEKLY:
                return timing, [
                    ele if isinstance(ele, tuple) else (ele, dt.time(tzinfo=tzinfo))
                    for ele in cast(list[_TimingTypeDay], timing)
                ]
        else:
            if job_type is JobType.MINUTELY:
                timing = cast(dt.time, timing).replace(hour=0, minute=0)
            elif job_type is JobType.HOURLY:
                timing = cast(dt.time, timing).replace(hour=0)
        return timing, None

    @staticmethod
    def check_timing_tzinfo(
        job_type: TimingJobUnion,
        timing: TimingJobUnion,
        tzinfo: Optional[dt.tzinfo],
        expanded_timing: Optional[list[tuple[Weekday, dt.time]]],
    ):
        if isinstance(timing, list):
            if job_type is JobType.WEEKLY:
                for _, time in cast(list[tuple[Weekday, dt.time]], expanded_timing):
                    if bool(time.tzinfo) ^ bool(tzinfo):
                        raise SchedulerError(TZ_ERROR_MSG)
            elif job_type in (JobType.MINUTELY, JobType.HOURLY, JobType.DAILY):
                for time in cast(list[dt.time], timing):
                    if bool(time.tzinfo) ^ bool(tzinfo):
                        raise SchedulerError(TZ_ERROR_MSG)
        else:
            if job_type is JobType.WEEKLY and isinstance(timing, tuple):
                if bool(timing[1].tzinfo) ^ bool(tzinfo):
                    raise SchedulerError(TZ_ERROR_MSG)
            elif job_type in (JobType.MINUTELY, JobType.HOURLY, JobType.DAILY):
                if bool(cast(dt.time, timing).tzinfo) ^ bool(tzinfo):
                    raise SchedulerError(TZ_ERROR_MSG)

    @staticmethod
    def check_duplicate_effective_timings(
        job_type: JobType,
        timing: TimingJobUnion,
        tzinfo: dt.tzinfo,
        expanded_timing: Optional[list[tuple[Weekday, dt.time]]],
    ):
        if not isinstance(timing, list):
            return
        if job_type is JobType.WEEKLY:
            if not are_weekday_times_unique(
                cast(list[tuple[Weekday, dt.time]], expanded_timing), tzinfo
            ):
                raise SchedulerError(DUPLICATE_EFFECTIVE_TIME)
        elif job_type in (
            JobType.MINUTELY,
            JobType.HOURLY,
            JobType.DAILY,
        ):
            if not are_times_unique(cast(list[dt.time], timing)):
                raise SchedulerError(DUPLICATE_EFFECTIVE_TIME)

    @staticmethod
    def set_start_check_stop_tzinfo(
        start: dt.datetime, stop: dt.datetime, tzinfo: dt.tzinfo
    ) -> dt.datetime:
        if start:
            if bool(start.tzinfo) ^ bool(tzinfo):
                raise SchedulerError(_TZ_ERROR_MSG.format("start"))
        else:
            start = dt.datetime.now(tzinfo)

        if stop:
            if bool(stop.tzinfo) ^ bool(tzinfo):
                raise SchedulerError(_TZ_ERROR_MSG.format("stop"))

        if stop is not None:
            if start >= stop:
                raise SchedulerError(START_STOP_ERROR)
        return start

    @staticmethod
    def init_job_timers(
        timing: TimingJobUnion,
        job_type: JobType,
        start: dt.datetime,
        skip_missing: bool,
    ) -> list[JobTimer]:
        if not isinstance(timing, list):
            timing = [timing]
        timers = [JobTimer(job_type, tim, start, skip_missing) for tim in timing]

        # generate first dt_stamps for each JobTimer
        for timer in timers:
            timer.calc_next_exec()

        return timers

    @staticmethod
    def get_pending_timer(timers: list[JobTimer]) -> JobTimer:
        """Get the pending timer at the moment."""
        unsorted_timer_datetimes: dict[JobTimer, dt.datetime] = {}
        for timer in timers:
            unsorted_timer_datetimes[timer] = timer.datetime
        sorted_timers = sorted(
            unsorted_timer_datetimes,
            key=unsorted_timer_datetimes.get,  # type: ignore
        )
        return sorted_timers[0]


class Job(AbstractJob):
    r"""
    `Job` class bundling time and callback function methods.

    Parameters
    ----------
    job_type : JobType
        Indicator which defines which calculations has to be used.
    timing : TimingTypeWeekly
        Desired execution time(s).
    handle : Callable[..., None]
        Handle to a callback function.
    params : dict[str, Any]
        The payload arguments to pass to the function handle within a
        |Job|.
    weight : float
        Relative `weight` against other |Job|\ s.
    delay : bool
        If ``True`` wait with the execution for the next scheduled time.
    start : Optional[datetime.datetime]
        Set the reference `datetime.datetime` stamp the |Job|
        will be scheduled against. Default value is `datetime.datetime.now()`.
    stop : Optional[datetime.datetime]
        Define a point in time after which a |Job| will be stopped
        and deleted.
    max_attempts : int
        Number of times the |Job| will be executed where ``0 <=> inf``.
        A |Job| with no free attempt will be deleted.
    skip_missing : bool
        If ``True`` a |Job| will only schedule it's newest planned
        execution and drop older ones.
    tzinfo : datetime.tzinfo
        Set the timezone of the |Scheduler| the |Job|
        is scheduled in.

    Returns
    -------
    Job
        Instance of a scheduled |Job|.
    """
    __type: JobType
    __timing: TimingJobUnion
    __handle: Callable[..., None]
    __params: Optional[dict[str, Any]]
    __max_attempts: int
    __weight: float
    __delay: bool
    __start: Optional[dt.datetime]
    __stop: Optional[dt.datetime]
    __skip_missing: bool
    __tzinfo: Optional[dt.tzinfo]

    __lock: threading.RLock
    __mark_delete: bool
    __attempts: int
    __pending_timer: JobTimer
    __timers: list[JobTimer]

    def __init__(
        self,
        job_type: JobType,
        timing: TimingJobUnion,
        handle: Callable[..., None],
        params: Optional[dict[str, Any]] = None,
        max_attempts: int = 0,
        weight: float = 1,
        delay: bool = True,
        start: Optional[dt.datetime] = None,
        stop: Optional[dt.datetime] = None,
        skip_missing: bool = False,
        tzinfo: Optional[dt.tzinfo] = None,
    ):
        timing, expanded_timing = JobUtil.standardize_timing_format(
            job_type, timing, tzinfo
        )

        JobUtil.sane_timing_types(job_type, timing)
        JobUtil.check_duplicate_effective_timings(
            job_type, timing, tzinfo, expanded_timing
        )
        JobUtil.check_timing_tzinfo(job_type, timing, tzinfo, expanded_timing)

        self.__start = JobUtil.set_start_check_stop_tzinfo(start, stop, tzinfo)

        self.__type = job_type
        self.__timing = timing
        self.__handle = handle
        self.__params = {} if params is None else params
        self.__max_attempts = max_attempts
        self.__weight = weight
        self.__delay = delay
        self.__stop = stop
        self.__skip_missing = skip_missing
        self.__tzinfo = tzinfo

        self.__lock = threading.RLock()

        # self.__mark_delete will be set to True if the new Timer would be in future
        # relativ to the self.__stop variable
        self.__mark_delete = False
        self.__attempts = 0

        # create JobTimers
        self.__timers = JobUtil.init_job_timers(
            timing=timing,
            job_type=job_type,
            start=self.__start,
            skip_missing=skip_missing,
        )
        # self.__set_pending_timer()
        self.__pending_timer = JobUtil.get_pending_timer(self.__timers)

        if self.__stop is not None:
            if self.__pending_timer.datetime > self.__stop:
                self.__mark_delete = True

    def _exec(self) -> None:
        """Execute the callback function."""
        with self.__lock:
            self.__handle(**self.__params)
            self.__attempts += 1

    def __lt__(self, other: Job):
        dt_stamp = dt.datetime.now(self.__tzinfo)
        return (
            self.timedelta(dt_stamp).total_seconds()
            < other.timedelta(dt_stamp).total_seconds()
        )

    def __repr__(self) -> str:
        with self.__lock:
            return "scheduler.Job({})".format(
                ", ".join(
                    (
                        repr(elem)
                        for elem in (
                            self.__type,
                            self.__timing,
                            self.__handle,
                            self.__params,
                            self.__max_attempts,
                            self.__weight,
                            self.__delay,
                            self.__start,
                            self.__stop,
                            self.__skip_missing,
                            self.tzinfo,
                        )
                    )
                )
            )

    def _str(
        self,
    ) -> tuple[
        str,
        str,
        str,
        dt.datetime,
        str,
        Optional[str],
        dt.timedelta,
        str,
        int,
        Union[float, int],
        float,
    ]:
        """Return the objects relevant for readable string representation."""
        with self.__lock:
            dt_timedelta = self.timedelta(dt.datetime.now(self.__tzinfo))
            if hasattr(self.handle, "__code__"):
                f_args = "(..)" if self.handle.__code__.co_nlocals else "()"
            else:
                f_args = "(?)"
            return (
                self.__type.name if self.max_attempts != 1 else "ONCE",
                self.handle.__qualname__,
                f_args,
                self.datetime,
                str(self.datetime)[:19],
                self.datetime.tzname(),
                dt_timedelta,
                prettify_timedelta(dt_timedelta),
                self.attempts,
                float("inf") if self.max_attempts == 0 else self.max_attempts,
                self.weight,
            )

    def __str__(self) -> str:
        return "{0}, {1}{2}, at={4}, tz={5}, in={7}, #{8}/{9}, w={10:.3f}".format(
            *self._str()
        )

    def _calc_next_exec(self, ref_dt: dt.datetime) -> None:
        """
        Calculate the next estimated execution `datetime.datetime` of the `Job`.

        Parameters
        ----------
        ref_dt : datetime.datetime
            Reference time stamp to which the |Job| calculates
            it's next execution.
        """
        with self.__lock:
            if self.__skip_missing:
                for timer in self.__timers:
                    if (timer.datetime - ref_dt).total_seconds() <= 0:
                        timer.calc_next_exec(ref_dt)
            else:
                self.__pending_timer.calc_next_exec(ref_dt)
            self.__pending_timer = JobUtil.get_pending_timer(self.__timers)
            if self.__stop is not None and self.__pending_timer.datetime > self.__stop:
                self.__mark_delete = True

    @property
    def type(self) -> JobType:
        """
        Return the `JobType` of the `Job` instance.

        Returns
        -------
        JobType
            :class:`~scheduler.job.JobType` of the |Job|.
        """
        return self.__type

    @property
    def handle(self) -> Callable[..., None]:
        """
        Get the callback function handle.

        Returns
        -------
        Callable
            Callback function.
        """
        return self.__handle

    @property
    def params(self) -> dict[str, Any]:
        r"""
        Get the payload arguments to pass to the function handle within a `Job`.

        .. warning:: When running |Job|\ s in parallel threads,
            be sure to implement possible side effects of parameter accessing in a
            thread safe manner.

        Returns
        -------
        dict[str, Any]
            The payload arguments to pass to the function handle within a
            |Job|.
        """
        return self.__params

    @property
    def weight(self) -> float:
        """
        Return the weight of the `Job` instance.

        Returns
        -------
        float
            |Job| `weight`.
        """
        return self.__weight

    @property
    def delay(self) -> bool:
        """
        Return ``True`` if the first `Job` execution will wait for the next scheduled time.

        Returns
        -------
        bool
            If ``True`` wait with the execution for the next scheduled time. If ``False``
            the first execution will target the time of `Job.start`.
        """
        return self.__delay

    @property
    def start(self) -> Optional[dt.datetime]:
        """
        Get the timestamp at which the `JobTimer` starts.

        Returns
        -------
        Optional[datetime.datetime]
            The start datetime stamp.
        """
        return self.__start

    @property
    def stop(self) -> Optional[dt.datetime]:
        """
        Get the timestamp after which no more executions of the `Job` should be scheduled.

        Returns
        -------
        Optional[datetime.datetime]
            The stop datetime stamp.
        """
        return self.__stop

    @property
    def max_attempts(self) -> int:
        """
        Get the execution limit for a `Job`.

        Returns
        -------
        int
            Max execution attempts.
        """
        return self.__max_attempts

    @property
    def skip_missing(self) -> bool:
        """
        Return ``True`` if `Job` will only schedule it's newest planned execution.

        Returns
        -------
        bool
            If ``True`` a |Job| will only schedule it's newest planned
            execution and drop older ones.
        """
        return self.__skip_missing

    @property
    def tzinfo(self) -> Optional[dt.tzinfo]:
        r"""
        Get the timezone of the `Job`'s next execution.

        Returns
        -------
        Optional[datetime.tzinfo]
            Timezone of the |Job|\ s next execution.
        """
        return self.datetime.tzinfo

    @property
    def _tzinfo(self) -> Optional[dt.tzinfo]:
        """
        Get the timezone of the `Scheduler` in which the `Job` is living.

        Returns
        -------
        Optional[datetime.tzinfo]
            Timezone of the |Job|.
        """
        return self.__tzinfo

    @property
    def has_attempts_remaining(self) -> bool:
        """
        Check if a `Job` has remaining attempts.

        This function will return True if the |Job| has open
        execution counts and the stop argument is not in the past relative to the
        next planed execution.

        Returns
        -------
        bool
            True if the |Job| has execution attempts.
        """
        with self.__lock:
            if self.__mark_delete:
                return False
            if self.__max_attempts == 0:
                return True
            return self.__attempts < self.__max_attempts

    @property
    def attempts(self) -> int:
        """
        Get the number of executions for a `Job`.

        Returns
        -------
        int
            Execution attempts.
        """
        return self.__attempts

    @property
    def datetime(self) -> dt.datetime:
        """
        Give the `datetime.datetime` object for the planed execution.

        Returns
        -------
        datetime.datetime
            Execution `datetime.datetime` stamp.
        """
        with self.__lock:
            if not self.__delay and self.__attempts == 0:
                return cast(dt.datetime, self.__start)
            return self.__pending_timer.datetime

    def timedelta(self, dt_stamp: Optional[dt.datetime] = None) -> dt.timedelta:
        """
        Get the `datetime.timedelta` until the next execution of this `Job`.

        Parameters
        ----------
        dt_stamp : Optional[datetime.datetime]
            Time to be compared with the planned execution time to determine the time difference.

        Returns
        -------
        timedelta
            `datetime.timedelta` to the next execution.
        """
        with self.__lock:
            if dt_stamp is None:
                dt_stamp = dt.datetime.now(self.__tzinfo)
            if not self.__delay and self.__attempts == 0:
                return cast(dt.datetime, self.__start) - dt_stamp
            return self.__pending_timer.timedelta(dt_stamp)
