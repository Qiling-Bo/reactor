#!/usr/bin/env python
# encoding: utf-8
from topaz import fsm
from topaz.config import DEVICE_LIST
from topaz.chamber import Chamber, ChamberStates
from topaz.pwr import PowerSupply


def main():
    ps = PowerSupply()
    setting = {"volt": 12.0, "curr": 30.0, "ovp": 13.0, "ocp": 40.0}
    try:
        ps.selectChannel(node=5, ch=1)
        ps.set(setting)
        ps.activateOutput()
        #ps.selectChannel(node=6, ch=1)
        #ps.set(setting)
        #ps.activateOutput()
    except Exception:
        ps.deactivateOutput()
        ps.reset()
        raise Exception

    chamber1 = Chamber(DEVICE_LIST[0], chamber_id=0)
    chamber2 = Chamber(DEVICE_LIST[1], chamber_id=1)

    f1 = fsm.StateMachine(chamber1)
    f1.run()
    f2 = fsm.StateMachine(chamber2)
    f2.run()

    f1.en_queue(ChamberStates.INIT)
    f1.en_queue(ChamberStates.WORK)
    f1.en_queue(ChamberStates.EXIT)

    f2.en_queue(ChamberStates.INIT)
    f2.en_queue(ChamberStates.WORK)
    f2.en_queue(ChamberStates.EXIT)


if __name__ == "__main__":
    main()
