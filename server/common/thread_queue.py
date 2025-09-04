import threading
from collections import deque

class ThreadQueue:
    def __init__(self, maxsize=0):
        self._maxsize = maxsize
        self._queue = deque()

        self._mutex = threading.Lock()
        self._not_empty = threading.Condition(self._mutex)
        self._not_full = threading.Condition(self._mutex)
        self._all_tasks_done = threading.Condition(self._mutex)

        self._unfinished_tasks = 0

    def qsize(self):
        with self._mutex:
            return len(self._queue)

    def empty(self):
        with self._mutex:
            return not self._queue

    def full(self):
        with self._mutex:
            return self._maxsize > 0 and len(self._queue) >= self._maxsize

    def put(self, item):
        with self._not_full:
            while self._maxsize > 0 and len(self._queue) >= self._maxsize:
                self._not_full.wait()
            self._queue.append(item)
            self._unfinished_tasks += 1
            self._not_empty.notify()

    def get(self):                
        with self._not_empty:
            while not self._queue:
                self._not_empty.wait()
            item = self._queue.popleft()
            self._not_full.notify()
            return item

    def task_done(self):
        with self._all_tasks_done:
            if self._unfinished_tasks <= 0:
                raise ValueError("task_done() called too many times")
            self._unfinished_tasks -= 1
            if self._unfinished_tasks == 0:
                self._all_tasks_done.notify_all()

    def join(self):
        with self._all_tasks_done:
            while self._unfinished_tasks:
                self._all_tasks_done.wait()
