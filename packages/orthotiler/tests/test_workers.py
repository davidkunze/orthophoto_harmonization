from orthotiler.processing import get_worker_count

workers = get_worker_count(
    workers=None,
    task_count=100,
)

print(workers)