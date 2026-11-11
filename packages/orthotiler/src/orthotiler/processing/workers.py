
import os


def get_worker_count(
    workers=None,
    task_count=None,
):
    """
    Determines the number of parallel workers.

    The default is the available CPU count minus two.

    Parameters
    ----------
    workers : int or None
        Explicit number of workers.

    task_count : int or None
        Number of available tasks.

    Returns
    -------
    int
        Number of workers.
    """

    cpu_count = os.cpu_count() or 1

    # Use CPU count minus two as the default
    if workers is None:
        workers = max(
            1,
            cpu_count - 2,
        )

    if isinstance(workers, bool) or not isinstance(workers, int):
        raise TypeError(
            "workers must be an integer or None."
        )

    if workers < 1:
        raise ValueError(
            "The number of workers must be at least 1."
        )

    if task_count is not None:

        if isinstance(task_count, bool) or not isinstance(task_count, int):
            raise TypeError(
                "task_count must be an integer or None."
            )

        if task_count < 0:
            raise ValueError(
                "task_count cannot be negative."
            )

        if task_count == 0:
            return 0

        workers = min(
            workers,
            task_count,
        )

    return workers
