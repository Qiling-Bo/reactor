"""test sqlalchemy orm
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
import datetime
Base = declarative_base()


class SessionManager(object):
    def __init__(self, connectString):
        self.engine = create_engine(connectString)
        self.session = sessionmaker(bind=self.engine)
        self.maketable = False

    def create_table(self):
        if(not self.maketable):
            DUT.metadata.create_all(self.engine)     # create table
            Cycle.metadata.create_all(self.engine)     # create table
            self.maketable = True

    def get_session(self):
        return self.session()


class DUT(Base):
    __tablename__ = "dut"

    ID = Column(Integer, primary_key=True)
    PWRCYCS = Column("PWRCYCS", Integer)
    LASTCAP = Column(Integer)
    MODEL = Column(String(10))
    FWVER = Column(String(10))
    HWVER = Column(String(10))
    CAPPN = Column(String(10))
    SN = Column(String(10))
    PCBVER = Column(String(10))
    MFDATE = Column(String(10))
    ENDUSR = Column(String(10))
    PCA = Column(String(10))
    CINT = Column(Integer)

    SLOTNUM = Column(Integer)
    ARCHIEVED = Column(Integer)   # 0 for running and 1 for archieved.
    STATUS = Column(Integer, nullable=True)
    MESSAGE = Column(String(20))
    TESTDATE = Column(DateTime, default=datetime.datetime.utcnow)

    #DUT is one to many class refer to Cycles
    cycles = relationship("Cycle", backref="dut")


class Cycle(Base):
    __tablename__ = "cycle"

    ID = Column(Integer, primary_key=True)
    CYCLENUM = Column(Integer, nullable=True)
    READINESS = Column(Integer)
    PGEMSTAT = Column(Integer)
    TEMP = Column(Integer)
    VIN = Column(Integer)
    VCAP = Column(Integer)
    VC1 = Column(Integer)
    VC2 = Column(Integer)
    VC3 = Column(Integer)
    VC4 = Column(Integer)
    VC5 = Column(Integer)
    VC6 = Column(Integer)
    RESERVED = Column(Integer)
    TIME = Column(Integer)
    DUTID = Column(Integer, ForeignKey("dut.ID"))


if __name__ == "__main__":
    sm = SessionManager("sqlite:///topaz.db")
    sm.create_table()
    session = sm.get_session()

    dut = DUT()
    dut.PWRCYCS = 150
    dut.LASTCAP = 117
    dut.MODEL = "topaz"

    session.add(dut)
    session.commit()

    try:
        dut = session.query(DUT).filter(DUT.MODEL == "topaz").first()

        #dut.__dict__.update({"sn": "12345", "slotnum": 7})
        d = {"SN": "54321", "SLOTNUM": 17}
        for k, v in d.items():
            setattr(dut, k, v)

        cycle = Cycle()
        cycle.CYCLENUM = dut.PWRCYCS + 1
        c = {"VIN": 47, "VCAP": 43, "TEMP": 20}
        for k, v in c.items():
            setattr(cycle, k, v)
        dut.cycles.append(cycle)

        session.commit()
    except Exception as e:
        print e
        session.rollback()
