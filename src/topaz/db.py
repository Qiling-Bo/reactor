#!/usr/bin/env python
# encoding: utf-8
"""database interface for topaz bi.
"""
from model import DUT, Cycle, SessionManager
cstring = "sqlite:///topaz.db"


class DBException(Exception):
    pass


class DB(object):
    """class to access the database, save, update and check status
    """

    def __init__(self):
        sm = SessionManager(cstring)
        sm.create_table()
        self.session = sm.get_session()

    def fetch(self, num):
        """read document of slotnum """
        d = self.session.query(DUT) \
            .filter(DUT.ARCHIEVED == 0) \
            .filter(DUT.SLOTNUM == num).first()
        if not d:
            #raise DBException("dut {0} is not found.".format(num))
            d = DUT()
            d.ARCHIEVED = 0
            d.SLOTNUM = num
            self.session.add(d)
        return d

    def commit(self):
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise DBException("db commit fail")

    def update_info(self, num, d):
        """update dut info with dict"""
        dut = self.fetch(num)
        for k, v in d.items():
            setattr(dut, k, v)
        self.commit()

    def add_cycle(self, num, c):
        """add cycle to dut"""
        dut = self.fetch(num)
        cycle = Cycle()
        cycle.CYCLENUM = dut.PWRCYCS + 1
        for k, v in c.items():
            setattr(cycle, k, v)
        dut.cycles.append(cycle)
        self.commit()

    def archieve(self, num):
        """update archieved to true"""
        dut = self.fetch(num)
        dut.ARCHIEVED = 1
        self.commit()

    def close(self):
        """close db connection."""
        self.session.close()


if __name__ == "__main__":
    db = DB()
    slotnum = 11
    mydut = {"SN": "123", "STATUS": 1}
    db.update_info(slotnum, mydut)

    cycle = {"VCAP": 112, "VIN": 120, "TEMP": 58, "TIME": 0.02}
    db.add_cycle(slotnum, cycle)
    db.close()
