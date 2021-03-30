import collections

class Event(collections.OrderedDict):
    """Event subscription.

    A dict of callable objects. Calling an instance of this will cause a
    call to each item in the dict in ascending order by index.

    Example Usage:
    ```python
    >>> def f(x):
    ...     print("f({})".format(x))
    >>> def g(x):
    ...     print("g({})".format(x))
    >>> e = Event()
    >>> e()
    >>> e["print"] = f
    >>> e(123)
    f(123)
    >>> del["print"]
    >>> e()
    >>> e["f"] = f
    >>> e["g"] = g
    >>> e(10)
    f(10)
    g(10)
    ```
    """
    def __call__(self, *args, **kwargs) -> None:
        for f in self.values():
            if callable(f):
                f(*args, **kwargs)

    def __repr__(self) -> str:
        return "Event({})".format(dict.__repr__(self))
    
