#!/usr/bin/env python
# encoding: utf-8
"""event-driven state machine
"""
from multiprocessing import Process, Queue, Value
from exceptions import NotImplementedError


class States(object):
    INIT = 0
    IDLE = 1
    WORK = 2
    ERROR = 3
    EXIT = 4


class IFunc(object):
    def __init__(self):
        self.queue = Queue()

    def init(self):
        raise NotImplementedError

    def idle(self):
        raise NotImplementedError

    def work(self):
        raise NotImplementedError

    def error(self):
        raise NotImplementedError

    def exit(self):
        raise NotImplementedError

    def empty(self):
        for i in range(self.queue.qsize()):
            self.queue.get()


class StateMachine(object):
    def __init__(self, ifunc):
        self.mf = ifunc
        self.q = ifunc.queue
        self.status = Value('d', 0)
        self.is_alive = True

    def en_queue(self, state):
        self.q.put(state)

    def run(self):
        p = Process(target=self.loop, args=(self.status, ))
        p.start()

    def quit(self):
        self.q.put(States.EXIT)
        self.is_alive = False

    def loop(self, s):
        while(self.is_alive):
            s.value = self.q.get()
            if(s.value == States.INIT):
                self.mf.init()
            elif(s.value == States.IDLE):
                self.mf.idle()
            elif(s.value == States.ERROR):
                self.mf.error()
            elif(s.value == States.EXIT):
                self.mf.exit()
                self.is_alive = False
            else:
                self.mf.work(s.value)
