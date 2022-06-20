#!/usr/bin/env python3
# simple boardd wrapper that updates the panda first
import os
import usb1
import time
import subprocess
from typing import NoReturn
from functools import cmp_to_key

from panda import DEFAULT_FW_FN, DEFAULT_H7_FW_FN, MCU_TYPE_H7, Panda, PandaDFU
from common.basedir import BASEDIR
from common.gpio import gpio_set
from common.params import Params
from common.spinner import Spinner
from selfdrive.hardware import TICI
from selfdrive.hardware.tici.pins import GPIO
from selfdrive.swaglog import cloudlog


def get_expected_signature(panda: Panda) -> bytes:
  fn = DEFAULT_H7_FW_FN if (panda.get_mcu_type() == MCU_TYPE_H7) else DEFAULT_FW_FN

  try:
    return Panda.get_signature_from_firmware(fn)
  except Exception:
    cloudlog.exception("Error computing expected signature")
    return b""


def flash_panda(panda_serial: str) -> Panda:
  panda = Panda(panda_serial)

  fw_signature = get_expected_signature(panda)

  panda_version = "bootstub" if panda.bootstub else panda.get_version()
  panda_signature = b"" if panda.bootstub else panda.get_signature()
  cloudlog.warning(f"Panda {panda_serial} connected, version: {panda_version}, signature {panda_signature.hex()[:16]}, expected {fw_signature.hex()[:16]}")

  if panda.bootstub or panda_signature != fw_signature:
    cloudlog.info("Panda firmware out of date, update required")

    if TICI and not panda.bootstub:
      panda.reset(enter_bootstub=True)
      if not panda.bootstub:
        cloudlog.error(f"Panda unable to enter bootstub. Attempting to recover.")

        gpio_set(GPIO.STM_RST_N, 1)
        gpio_set(GPIO.STM_BOOT0, 1)
        time.sleep(2)
        gpio_set(GPIO.STM_RST_N, 0)

        panda.recover(skip_enter_dfu=True)

        gpio_set(GPIO.STM_RST_N, 1)
        gpio_set(GPIO.STM_BOOT0, 0)
        time.sleep(2)
        gpio_set(GPIO.STM_RST_N, 0)

    panda.flash()
    cloudlog.info("Done flashing")

  if panda.bootstub:
    bootstub_version = panda.get_version()
    cloudlog.info(f"Flashed firmware not booting, flashing development bootloader. Bootstub version: {bootstub_version}")

    spinner = Spinner()
    spinner.update("Restoring panda")
    h7 = panda.get_mcu_type() == MCU_TYPE_H7
    panda.reset(enter_bootstub=True)
    panda.reset(enter_bootloader=True)
    time.sleep(1)
    try:
      if h7:
        os.system("/usr/bin/dfu-util -d 0483:df11 -a 0 -s 0x08020000 -D /data/openpilot/panda/board/obj/panda_h7.bin.signed")
        os.system("/usr/bin/dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D /data/openpilot/panda/board/obj/bootstub.panda_h7.bin")
        panda.flash('/data/openpilot/panda/board/obj/panda_h7.bin.signed')
      else:
        os.system("/usr/bin/dfu-util -d 0483:df11 -a 0 -s 0x08004000 -D /data/openpilot/panda/board/obj/panda.bin.signed")
        os.system("/usr/bin/dfu-util -d 0483:df11 -a 0 -s 0x08000000:leave -D /data/openpilot/panda/board/obj/bootstub.panda.bin")
        panda.flash('/data/openpilot/panda/board/obj/panda.bin.signed')
    finally:
      panda.reset()
      panda.reconnect()

    cloudlog.info("Done flashing bootloader")

    if panda.bootstub:
      spinner.update("Try manualley Panda Recover")
      time.sleep(60)
    else:
      spinner.close()

  if panda.bootstub:
    cloudlog.info("Panda still not booting, exiting")
    raise AssertionError

  panda_signature = panda.get_signature()
  if panda_signature != fw_signature:
    cloudlog.info("Version mismatch after flashing, exiting")
    raise AssertionError

  return panda

def panda_sort_cmp(a: Panda, b: Panda):
  a_type = a.get_type()
  b_type = b.get_type()

  # make sure the internal one is always first
  if a.is_internal() and not b.is_internal():
    return -1
  if not a.is_internal() and b.is_internal():
    return 1

  # sort by hardware type
  if a_type != b_type:
    return a_type < b_type

  # last resort: sort by serial number
  return a.get_usb_serial() < b.get_usb_serial()


def main() -> NoReturn:
  params = Params()

  while True:
    try:
      params.delete("PandaSignatures")

      # Flash all Pandas in DFU mode
      for p in PandaDFU.list():
        cloudlog.info(f"Panda in DFU mode found, flashing recovery {p}")
        PandaDFU(p).recover()
      time.sleep(1)

      panda_serials = Panda.list()
      if len(panda_serials) == 0:
        continue

      cloudlog.info(f"{len(panda_serials)} panda(s) found, connecting - {panda_serials}")

      # Flash pandas
      pandas = []
      for serial in panda_serials:
        pandas.append(flash_panda(serial))

      # check health for lost heartbeat
      for panda in pandas:
        health = panda.health()
        if health["heartbeat_lost"]:
          params.put_bool("PandaHeartbeatLost", True)
          cloudlog.event("heartbeat lost", deviceState=health, serial=panda.get_usb_serial())

      # sort pandas to have deterministic order
      pandas.sort(key=cmp_to_key(panda_sort_cmp))
      panda_serials = list(map(lambda p: p.get_usb_serial(), pandas))

      # log panda fw versions
      params.put("PandaSignatures", b','.join(p.get_signature() for p in pandas))

      # close all pandas
      for p in pandas:
        p.close()
    except (usb1.USBErrorNoDevice, usb1.USBErrorPipe):
      # a panda was disconnected while setting everything up. let's try again
      cloudlog.exception("Panda USB exception while setting up")
      continue

    # run boardd with all connected serials as arguments
    os.environ['MANAGER_DAEMON'] = 'boardd'
    os.chdir(os.path.join(BASEDIR, "selfdrive/boardd"))
    subprocess.run(["./boardd", *panda_serials], check=True)

if __name__ == "__main__":
  main()
