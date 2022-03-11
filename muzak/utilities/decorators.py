from clilib.util.logging import Logging
import functools
import asyncio    

def retry(func, *args, retry_count=5, delay=5, allowed_exceptions=(), **kwargs):
    func_args = args
    func_kwargs = kwargs
    log = Logging("Muzak", "Retry").get_logger()
    def decorator(f):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            result = None
            last_exception = None
            for _ in range(retry_count):
                try:
                    result = func(*func_args, **kwargs)
                    if result: return result
                except allowed_exceptions as e:
                    last_exception = e
                log.info("Waiting for %d seconds before retrying again" % delay)
                await asyncio.sleep(delay)

            if last_exception is not None:
                raise last_exception

            return result

        return wrapper
    return decorator