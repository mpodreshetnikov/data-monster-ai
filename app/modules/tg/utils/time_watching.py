import time

class ExecInfoStorage():
    __count__: int = 10
    __exec_time_store__: dict[str, list[float]] = {}
    __start_time_store__: dict[str, float] = {}

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
        
        if key not in self.__exec_time_store__:
            self.__exec_time_store__[key] = []
        self.__exec_time_store__[key].append(exec_time)
        
        if len(self.__exec_time_store__[key]) > self.__count__:
            self.__exec_time_store__[key].pop(0)
    
    def average(self, key: str) -> float | None:
        if key not in self.__exec_time_store__:
            return None
        return round(sum(self.__exec_time_store__[key]) / len(self.__exec_time_store__[key]))