import time

class ExecInfoStorage():
    __count__: int = 10
    """Count of execution times to store"""
    __exec_time_store__: list[float] = []
    """Contains execution times for the function"""
    __start_time_store__: dict[str, float] = {}
    """Contains execution start time for each key"""

    def __init__(self, count: int = 10):
        if count < 1:
            raise ValueError("Count cannot be less than 1")
        self.__count__ = count

    def start(self, key: str):
        self.__start_time_store__[key] = time.time()

    def stop(self, key: str):
        if key not in self.__start_time_store__:
            return
        
        start_time = self.__start_time_store__[key]
        end_time = time.time()
        exec_time = end_time - start_time
        
        self.__exec_time_store__.append(exec_time)
        if len(self.__exec_time_store__) > self.__count__:
            self.__exec_time_store__.pop(0)
    
    def average(self) -> float | None:
        if len(self.__exec_time_store__) == 0:
            return None
        return round(sum(self.__exec_time_store__) / len(self.__exec_time_store__))