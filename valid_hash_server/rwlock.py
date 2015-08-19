# Modified Public domain file from https://majid.info/blog/a-reader-writer-lock-for-python/
# Simple reader-writer locks in Python
# Many readers can hold the lock XOR one and only one writer

import threading

class RWLock:

    """
    A simple reader-writer lock Several readers can hold the lock
    simultaneously, XOR one writer. Write locks have priority over reads to
    prevent write starvation.
    """

    def __init__(self):
        self.rwlock = 0
        self.writers_waiting = 0
        self.monitor = threading.Lock()
        self.readers_ok = threading.Condition(self.monitor)
        self.writers_ok = threading.Condition(self.monitor)

    def acquire_read(self):
        """
        Acquire a read lock. Several threads can hold this type of lock.
        It is exclusive with write locks.
        """

        with self.monitor:
            while self.rwlock < 0 or self.writers_waiting > 0:
                self.readers_ok.wait()
            self.rwlock += 1

    def acquire_write(self):
        """
        Acquire a write lock. Only one thread can hold this lock, and
        only when no read locks are also held.
        """

        with self.monitor:
            while self.rwlock != 0:
                self.writers_waiting += 1
                self.writers_ok.wait()
                self.writers_waiting -= 1
            self.rwlock = -1

    def release(self):
        """
        Release a lock, whether read or write.
        """

        with self.monitor:

            if self.rwlock < 0:
                self.rwlock = 0
            else:
                self.rwlock -= 1

            wake_writers = self.writers_waiting > 0 and self.rwlock == 0
            wake_readers = self.writers_waiting == 0

        if wake_writers:

            with self.writers_ok:
                self.writers_ok.notify()

        elif wake_readers:

            with self.readers_ok:
                self.readers_ok.notifyAll()

    def writer(self):
        return WLock(self)

    def reader(self):
        return RLock(self)

class LockContext:

    def __init__(self, lock):
        self.lock = lock

    def __exit__(self, extype, value, traceback):
        self.lock.release()
        return False

class WLock(LockContext):

    def __enter__(self):
        self.lock.acquire_write()

class RLock(LockContext):

    def __enter__(self):
        self.lock.acquire_read()

