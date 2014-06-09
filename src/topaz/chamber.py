#!/usr/bin/env python
# encoding: utf-8
'''chamber class, control the upper and lower chamber.
one chamber contains 8 channels.
'''
from topaz.pyaardvark import Adapter
from topaz.channel import channel_open, ChannelStates
from topaz import fsm
import logging
import time


class ChamberStates(fsm.States):
    pass


class Chamber(fsm.IFunc):
    '''chamber class
    '''

    def __init__(self, adapter_sn, chamber_id):
        self.i2c_adapter = Adapter()
        self.i2c_adapter.open(serialnumber=adapter_sn)
        self.chamber_id = chamber_id
        self.channel_list = []
        for i in range(chamber_id*8, chamber_id*8+8):
            my_channel = channel_open(ch_id=i, device=self.i2c_adapter)
            f = fsm.StateMachine(my_channel)
            f.run()
            self.channel_list.append(f)
        self.finish = False
        super(Chamber, self).__init__()

    def init(self):
        logging.debug("chamber " + str(self.chamber_id) + " in init")

    def idle(self):
        logging.debug("chamber " + str(self.chamber_id) + " in idle")

    def work(self, state):
        logging.debug("chamber " + str(self.chamber_id) + " start")
        wait_for_discharge = 0      # time to delay for empty channel
        while(not self.finish):
            self.finish = True
            for f in self.channel_list:
                if(f.status.value == ChannelStates.EXIT):
                    # check if already finished.
                    self.finish &= True
                    logging.info("-----channel finish.-----")
                    wait_for_discharge += 30
                    continue
                else:
                    self.finish &= False
                    logging.info("-----channel not finish.-----")
                logging.info("-----channel start-----")
                # start one cycle
                f.en_queue(ChannelStates.run)
                time.sleep(1)

                # wait for this cycle to finish
                while((f.status.value != ChannelStates.IDLE) and
                      (f.status.value != ChannelStates.EXIT)):
                    # check if the channle has finished burnin
                    time.sleep(5)
                logging.info("-----channel done.-----")
            if(not self.finish):
                # used to prevent only one channel left and
                # get not enough time to dischage
                time.sleep(wait_for_discharge)
            wait_for_discharge = 0
        logging.debug("chamber " + str(self.chamber_id) + " finish")

    def error(self):
        logging.debug("chamber " + str(self.chamber_id) + " in error")
        try:
            self.i2c_adapter.close()
        except Exception:
            pass
        self.queue.put(ChamberStates.EXIT)

    def exit(self):
        logging.debug("chamber " + str(self.chamber_id) + " in exit...")


if __name__ == "__main__":
    from pwr import PowerSupply
    from topaz.config import DEVICE_LIST

    import argparse
    parser = argparse.ArgumentParser(description="chamber.py")
    parser.add_argument('chamber_id', action='store', help='chamber to burnin')
    args = parser.parse_args()
    if(args.chamber_id == 0):
        device = DEVICE_LIST[0]
        ps_node = 5
    else:
        device = DEVICE_LIST[1]
        ps_node = 6

    ps = PowerSupply()
    setting = {"volt": 12.0, "curr": 15.0, "ovp": 13.0, "ocp": 20.0}

    try:
        ps.selectChannel(node=ps_node, ch=1)
        ps.activateOutput()
    except Exception:
        ps.deactivateOutput()
        raise Exception

    chamber = Chamber(device, chamber_id=int(args.chamber_id))
    f = fsm.StateMachine(chamber)
    f.run()

    f.en_queue(ChamberStates.INIT)
    f.en_queue(ChamberStates.WORK)
    f.en_queue(ChamberStates.EXIT)
