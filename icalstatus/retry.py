import random
import time
from collections.abc import Iterable
from logging import warning
from typing import Any, Protocol


class Callback(Protocol):
    def __call__(self, *args: str) -> None: ...


def retry(
    func: Callback,
    args: Iterable[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    exception_classes: Iterable[type[Exception]] = [],
    max_retries: int = 15,
) -> Any:
    """
    Retries calling a function up to a maximum number of attempts.

    :param func: function to retry
    :param args: positional arguments for the function
    :param kwargs: keyword arguments for the function
    :param exception_classes: iterable of exceptions to retry on.
    :param max_retries: maximum number of retries (use 0 to retry indefinietely)
    :return: the return value of ``func(*args, **kwargs)``
    """
    args = args or ()
    kwargs = kwargs or {}
    exception_classes = exception_classes or (Exception,)
    retries = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if any(isinstance(e, exc) for exc in exception_classes) and (
                (not max_retries) or (retries < max_retries)
            ):
                retries += 1
                if (max_retries > 0) and (retries > max_retries):
                    raise

                warning(
                    f"retry: attempt({retries}/{max_retries}) failed, retrying. "
                    f"function={func}, args={args}, kwargs={kwargs}. Error: {e}."
                )
                time.sleep(min(random.random() * retries, 10))
                continue
            raise
