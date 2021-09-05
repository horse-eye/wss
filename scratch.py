import concurrent.futures
import asyncio
import time

# https://stackoverflow.com/questions/41063331/how-to-use-asyncio-with-existing-blocking-library

# https://medium.com/@vladbezden/execute-blocking-code-on-a-different-thread-using-asyncio-db4baa956d1f

def blocking(delay):
    time.sleep(delay)
    print('Completed.')

async def non_blocking(loop, executor):
    # Run three of the blocking tasks concurrently. asyncio.wait will
    # automatically wrap these in Tasks. If you want explicit access
    # to the tasks themselves, use asyncio.ensure_future, or add a
    # "done, pending = asyncio.wait..." assignment
    await asyncio.wait(
        fs={
            # Returns after delay=12 seconds
            loop.run_in_executor(executor, blocking, 12),
            
            # Returns after delay=14 seconds
            loop.run_in_executor(executor, blocking, 14),
            
            # Returns after delay=16 seconds
            loop.run_in_executor(executor, blocking, 16)
        },
        return_when=asyncio.ALL_COMPLETED
    )

loop = asyncio.get_event_loop()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
loop.run_until_complete(non_blocking(loop, executor))

# If you want to schedule these tasks using a for loop (as in your example), you have several different strategies, 
# but the underlying approach is to schedule the tasks using the for loop (or list comprehension, etc), 
# await them with asyncio.wait, and then retrieve the results. Example:

done, pending = await asyncio.wait(
    fs=[loop.run_in_executor(executor, blocking_foo, *args) for args in inps],
    return_when=asyncio.ALL_COMPLETED
)

# Note that any errors raise during the above will be raised here; to
# handle errors you will need to call task.exception() and check if it
# is not None before calling task.result()
results = [task.result() for task in done]