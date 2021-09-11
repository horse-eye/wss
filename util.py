import timeit

def timed(func):
    ''' Prints the execution time of a function in milliseconds, using timeit default timer'''   
    def wrapper(*args, **kwargs):
        start = timeit.default_timer()
        result = func(*args, **kwargs)
        end = timeit.default_timer()
        exec_time = (end - start)
        print(func.__name__ + ": %.5f s" % exec_time)
        return result
    return wrapper  


def pf(obj, filename):
    '''Writes content to the specified file'''
    with open(filename, 'w') as f:
        print(obj, file=f)

def plf(obj, filename):
    '''Writes a list to the specified file, one item per line'''
    with open(filename, 'w') as f:
        for item in obj:
            print(item, file=f)
