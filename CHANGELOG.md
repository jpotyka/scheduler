# Changelog

## 0.4.0

+ Switched to LGPLv3 License

### Features

+ Delete all scheduled `Job`s using a single command.
+ Added `__repr__` and `__str__` methods to `Job` and `Scheduler`
+ Execute all scheduled `Job`s regardless of when they are scheduled.
+ Added optional `Job` flag: Discard missed executions befor the last pending execution
+ `Job`s can be passed to `Scheduler.__init__`
+ `Job` exposes property `tzinfo`
+ `Job`s support a `start` and `stop` datetime
+ Improved Exception handling
+ Extensive documentation rework

### API changes

+ completely overhauled `Scheduler` API

### Bugfixes

+ Fixed infinite recursion in `JobTimer` of `calc_next_exec`

### Misc

+ Improved examples and docs.
+ Added Guides and FAQ

## 0.3.0

### Features

+ Allowed parameters to be passed to the function handled by `Job`

### Misc

+ Improved examples and docs
+ Full test coverage :)

## 0.2.0

### API changes

+ Switched `Scheduler` arguments `max_exec` and `tzinfo`.

### Features

+ A `weight_function` can be passed to Scheduler for customizable `Job` weighting.

### Misc

+ Added a changelog
+ Revision of `setup.py`
+ Fixed readthedocs configuration
+ Small optimizations in `README.md` and docs
+ `README.md` embedded within sphinx documentation.
+ Provide a `secrets.py` to support local PyPI caching
+ Improved test coverage

## 0.1.0

+ Initial beta release