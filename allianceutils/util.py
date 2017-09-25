def retry_fn(fn, allowable_exceptions, retry_count=5):
    """
    Call fn, retrying if exception type in allowable_exceptions is raised up to retry_count times
    """
    for i in range(0, retry_count):
        try:
            return fn()
        except allowable_exceptions as ex:
            if i == retry_count - 1:
                raise
