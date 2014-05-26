#!/usr/bin/env python
# encoding: utf-8
"""open 1 channel, return Channel object,
and control the burin in process on this channel
"""
from topaz import fsm
from topaz.pyaardvark import Adapter
from topaz.i2c_basic import set_relay, switch, hwrd, re_position, deswitch
from topaz.i2c_basic import dut_info, dut_reg
from topaz.db import DB
from topaz.model import DUT, Cycle
from topaz.config import CHARGE, DISCHARGE, SLOTNUM
from topaz.config import DUTStatus, LIMITS, DELAY
from topaz.gauge import gauge
import logging
import time
import sys
import traceback


def channel_open(ch_id, device):
    return Channel(ch_id, device)


class ChannelStates(fsm.States):
    run = 0xFF
    charging = 0xA0
    discharging = 0xA1
    precheck = 0xA2
    postcheck = 0xA3


class CycleStatus(object):
    """to indicate one cycle's status for each DUT"""
    CHARGING = 0
    CHARGE_FINISH = 1
    DISCHARGING = 2
    DISCHARGE_FINISH = 3
    IDLING = 4
    BLANK = 5
    FAIL = 6
    PASS = 7


class Channel(fsm.IFunc):
    def __init__(self, ch_id, device):
        self.ch_id = ch_id
        self.device = device
        self.chamber = (ch_id+1) / SLOTNUM
        #index = re_position(self.chamber, ch_id, 0)
        self.db = DB()
        self.matrix = 0x00      # 0 for blank
        self.result = [CycleStatus.IDLING] * SLOTNUM      # 8 dut status
        super(Channel, self).__init__()

    def init(self):
        logging.debug("channel " + str(self.ch_id) + " in init")

    def idle(self):
        logging.debug("channel " + str(self.ch_id) + " in idle")

    def work(self, state):
        if(state == ChannelStates.charging):
            # CHARGING
            logging.debug("channel " + str(self.ch_id) + " in charging")
            try:
                self.process_charge(timeout=LIMITS.MAX_CHARGE_TIME)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                logging.error(repr(traceback.format_exception(exc_type,
                                                              exc_value,
                                                              exc_tb)))
                self.empty()    # clear states in queue
                self.queue.put(ChannelStates.ERROR)
            else:
                self.queue.put(ChannelStates.discharging)
        elif(state == ChannelStates.discharging):
            # DISCHARGING
            logging.debug("channel " + str(self.ch_id) + " in discharging")
            try:
                self.process_discharge(timeout=LIMITS.MAX_DISCHANGE_TIME)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                logging.error(repr(traceback.format_exception(exc_type,
                                                              exc_value,
                                                              exc_tb)))
                self.empty()    # clear states in queue
                self.queue.put(ChannelStates.ERROR)
            else:
                self.queue.put(ChannelStates.postcheck)
        elif(state == ChannelStates.postcheck):
            # Post Check
            logging.debug("channel " + str(self.ch_id) + " in post-check")
            try:
                finish = self.process_postcheck()
                if(finish):
                    self.queue.put(ChannelStates.EXIT)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                logging.error(repr(traceback.format_exception(exc_type,
                                                              exc_value,
                                                              exc_tb)))
                self.empty()    # clear states in queue
                self.queue.put(ChannelStates.ERROR)
            else:
                self.queue.put(ChannelStates.IDLE)
        elif(state == ChannelStates.precheck):
            # Pre Check
            logging.debug("channel " + str(self.ch_id) + " in pre-check")
            try:
                self.matrix = self.process_precheck()
                if(not self.continue_test()):
                    logging.debug("channel " + str(self.ch_id) +
                                  " : no dut need to test.")
                    self.empty()
                    self.queue.put(ChannelStates.EXIT)
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                logging.error(repr(traceback.format_exception(exc_type,
                                                              exc_value,
                                                              exc_tb)))
                self.empty()    # clear states in queue
                self.queue.put(ChannelStates.ERROR)
            else:
                self.queue.put(ChannelStates.charging)
        elif(state == ChannelStates.run):
            # Start Running
            self.queue.put(ChannelStates.precheck)
        else:
            logging.debug("unknow dut state, exit...")
            self.queue.put(ChannelStates.EXIT)

    def error(self):
        logging.debug("channel " + str(self.ch_id) + " in error")
        try:
            set_relay(self.device, self.ch_id, 0x00,  status=DISCHARGE)
            #save self.result to db
            self.process_error()
        except:
            pass
        self.queue.put(ChannelStates.EXIT)

    def exit(self):
        self.db.close()
        logging.debug("channel " + str(self.ch_id) + " in exit...")

    def continue_test(self):
        """if this cycle is finished"""
        for i in self.result:
            if((i != CycleStatus.PASS) and (i != CycleStatus.BLANK) and (i != CycleStatus.FAIL)):
                # not finished.
                return True
        return False

    def process_precheck(self):
        """pre check"""
        set_relay(self.device, self.ch_id, 0xFF, status=CHARGE)
        time.sleep(DELAY.POWERON)       # wait for device to be ready
        matrix = hwrd(self.device, self.ch_id)
        set_relay(self.device, self.ch_id, matrix, status=CHARGE)
        for i in range(SLOTNUM):
            dut_id = re_position(self.chamber, self.ch_id, i)
            dut = {}
            if(matrix & (0x01 << i)):
                # dut present
                switch(self.device, self.ch_id, i)
                dut.update(dut_info(self.device))
                dut["STATUS"] = DUTStatus.TESTING
                if(dut["PWRCYCS"] >= LIMITS.POWER_CYCLE):
                    dut["STATUS"] = DUTStatus.PASSED
                    dut["MESSAGE"] = "DUT PASSED."
                    self.result[i] = CycleStatus.PASS
                    logging.info("[+]" + str(dut["_id"]) + " " +
                                 dut["SN"] + " passed.")
                logging.info("[+] " + "Found " + dut["MODEL"] + " " +
                             dut["SN"] + " " + str(dut["PWRCYCS"]) + " on "
                             + str(re_position(self.chamber, self.ch_id, i)))
            else:
                logging.debug(str(dut_id) + " is not ready.")
                dut["STATUS"] = DUTStatus.BLANK
                self.result[i] = CycleStatus.BLANK
            self.db.update_info(dut_id, dut)
        deswitch(self.device, self.ch_id)
        #set_relay(device, ch_id, matrix, status=DISCHARGE)
        return matrix

    @gauge
    def process_charge(self):
        #set_relay(device, ch_id, matrix, status=CHARGE)
        start_s = time.time()
        finish = False
        while(not finish):
            finish = True
            for i in range(SLOTNUM):
                if(self.result[i] == CycleStatus.BLANK or
                   self.result[i] == CycleStatus.PASS or
                   self.result[i] == CycleStatus.FAIL):
                    continue

                switch(self.device, self.ch_id, i)
                self.result[i] = CycleStatus.CHARGING

                dut_id = re_position(self.chamber, self.ch_id, i)
                dut = {}
                result = dut_reg(self.device)
                result.update({"TIME": time.time()-start_s})
                vcap = result["VCAP"]
                temp = result["TEMP"]

                if(vcap >= LIMITS.VCAP_THRESH_HIGH and
                   temp <= LIMITS.TEMP_LIMITS_HIGH):
                    finish &= True
                    self.result[i] = CycleStatus.CHARGE_FINISH
                elif(vcap > LIMITS.VCAP_LIMITS_HIGH):
                    # over charge voltage, fail
                    logging.error("[-]" + " over charge voltage: " + str(vcap))
                    dut["STATUS"] = DUTStatus.FAILED
                    dut["MESSAGE"] = "DUT VCAP HIGH."
                    self.result[i] = CycleStatus.FAIL
                    finish &= True
                elif(temp > LIMITS.TEMP_LIMITS_HIGH):
                    # over temperature, fail
                    logging.error("[-]" + " over temperature: " + str(temp))
                    dut["STATUS"] = DUTStatus.FAILED
                    dut["MESSAGE"] = "DUT TEMP HIGH."
                    self.result[i] = CycleStatus.FAIL
                    finish &= True
                else:
                    finish &= False

                # record result
                #curr_cycle = "CYCLES" + str(int(dut["PWRCYCS"]) + 1)
                #if curr_cycle not in dut:
                #    dut.update({curr_cycle: []})
                #dut[curr_cycle].append(result)
                self.db.update_info(dut_id, dut)
                self.db.add_cycle(dut_id, result)

                display = str(dut_id) + " VCAP: " + str(vcap) + " TEMP: " + str(temp)
                logging.info(display)
            logging.info(" ")    # seperator for diaplay
            deswitch(self.device, self.ch_id)
            time.sleep(DELAY.READCYCLE)

    @gauge
    def process_discharge(self):
        set_relay(self.device, self.ch_id, self.matrix, status=DISCHARGE)
        start_s = time.time()
        finish = False
        while(not finish):
            finish = True
            for i in range(SLOTNUM):
                if(self.result[i] == CycleStatus.BLANK or
                   self.result[i] == CycleStatus.PASS or
                   self.result[i] == CycleStatus.FAIL):
                    continue

                switch(self.device, self.ch_id, i)
                self.result[i] = CycleStatus.DISCHARGING

                dut_id = re_position(self.chamber, self.ch_id, i)
                dut = {}
                result = dut_reg(self.device)
                result.update({"TIME": time.time()-start_s})
                vcap = result["VCAP"]
                temp = result["TEMP"]

                if(vcap <= LIMITS.VCAP_THRESH_LOW and
                   temp <= LIMITS.TEMP_LIMITS_HIGH):
                    finish &= True
                    self.result[i] = CycleStatus.DISCHARGE_FINISH
                elif(vcap > LIMITS.VCAP_LIMITS_HIGH):
                    # over charge voltage, fail
                    logging.error("[-]" + " over charge voltage: " + str(vcap))
                    dut["STATUS"] = DUTStatus.FAILED
                    dut["MESSAGE"] = "DUT VCAP HIGH."
                    self.result[i] = CycleStatus.FAIL
                    finish &= True
                elif(temp > LIMITS.TEMP_LIMITS_HIGH):
                    # over temperature, fail
                    logging.error("[-]" + " over temperature: " + str(temp))
                    dut["STATUS"] = DUTStatus.FAILED
                    dut["MESSAGE"] = "DUT TEMP HIGH."
                    self.result[i] = CycleStatus.FAIL
                    finish &= True
                else:
                    finish &= False

                # record result
                #curr_cycle = "CYCLES" + str(int(dut["PWRCYCS"]) + 1)
                #if curr_cycle not in dut:
                #    dut.update({curr_cycle: []})
                #dut[curr_cycle].append(result)
                self.db.update_info(dut_id, dut)
                self.db.add_cycle(dut_id, result)

                display = str(dut_id) + " VCAP: " + str(vcap) + " TEMP: " + str(temp)
                logging.info(display)
            logging.info(" ")    # seperator for diaplay
            deswitch(self.device, self.ch_id)
            time.sleep(DELAY.READCYCLE)

    def process_postcheck(self):
        result = True
        for i in range(SLOTNUM):
            self.result[i] = CycleStatus.IDLING
            dut_id = re_position(self.chamber, self.ch_id, i)
            dut = self.db.fetch(dut_id)
            if(dut.STATUS == DUTStatus.TESTING):
                dut.STATUS = DUTStatus.IDLE
                self.db.commit()
                result &= False
        return result

    def process_error(self):
        for i in range(SLOTNUM):
            dut_id = re_position(self.chamber, self.ch_id, i)
            dut = self.db.fetch(dut_id)
            if(self.result[i] == CycleStatus.CHARGING):
                # dut failed
                dut.STATUS = DUTStatus.FAILED
                dut.MESSAGE = "ERROR OCCURED IN CHARGING."
            elif(self.result[i] == CycleStatus.DISCHARGING):
                # dut failed
                dut.STATUS = DUTStatus.FAILED
                dut.MESSAGE = "ERROR OCCURED IN DISCHARGING."
            else:
                dut.STATUS = DUTStatus.IDLE
            self.db.commit()


if __name__ == "__main__":
    import pwr
    ps = pwr.PowerSupply()
    ps.selectChannel(node=5, ch=1)
    setting = {"volt": 12.0, "curr": 10.0, "ovp": 13.0, "ocp": 15.0}
    ps.set(setting)
    try:
        ps.activateOutput()
    except Exception as e:
        ps.deactivateOutput()
        logging.error(e)

    i2c_adapter = Adapter()
    i2c_adapter.open(serialnumber=2237594253)

    import argparse
    parser = argparse.ArgumentParser(description="channel.py")
    parser.add_argument('channel', action='store', help='channel to burnin')
    args = parser.parse_args()

    my_channel = channel_open(ch_id=int(args.channel)-1, device=i2c_adapter)
    f = fsm.StateMachine(my_channel)
    f.run()

    finish = False
    while(not finish):
        # start one cycle
        f.en_queue(ChannelStates.run)
        time.sleep(1)   # wait for the process to run, refresh the status.
        # wait for this cycle to finish
        while((f.status.value != ChannelStates.IDLE) and
              (f.status.value != ChannelStates.EXIT)):
            # check if the channle has finished burnin
            time.sleep(5)
        if(f.status.value == ChannelStates.EXIT):
            finish = True
        else:
            # wait the PGEM PowerCycle number change, stupid.
            time.sleep(5)

    ps.deactivateOutput()
