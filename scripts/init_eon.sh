#!/usr/bin/bash

if [ ! -f "/system/fonts/opensans_regular.ttf" ]; then
  mount -o remount,rw /system

  cp -rf /data/openpilot/installer/fonts/opensans* /system/fonts/
  cp -rf /data/openpilot/installer/fonts/fonts.xml /system/etc/fonts.xml
  chmod 644 /system/etc/fonts.xml
  chmod 644 /system/fonts/opensans*

  cp /data/openpilot/installer/fonts/bootanimation.zip /system/media/

  mount -o remount,r /system

  setprop persist.sys.locale en-US
  setprop persist.sys.local en-US
  setprop persist.sys.timezone Asia/Bangkok

  echo =================================================================
  echo Ko-KR NanumGothic font install complete
  echo en-US locale change complete
  echo Bootanimation change complete
  echo =================================================================
  echo Reboot Now..!!
  echo =================================================================
  reboot
fi

if [ ! -f "/BOOTLOGO" ]; then
  touch /BOOTLOGO
  #if $(grep -q "letv" /proc/cmdline); then
  if [ ! -f /LEECO ] && $(grep -q "letv" /proc/cmdline); then
    # lepro bootlogo
    touch /LEECO
    dd if=/data/openpilot/installer/fonts/splash.img of=/dev/block/bootdevice/by-name/splash
  elif [ ! -f /ONEPLUS ]; then
    # op3t bootlogo
    touch /ONEPLUS
    dd if=/data/openpilot/installer/fonts/logo.bin of=/dev/block/bootdevice/by-name/LOGO
    cp -f "$BASEDIR/selfdrive/hardware/eon/update.zip" "/sdcard/update.zip";
    echo -n 20 > /VERSION
  fi
  echo =================================================================
  echo Comma boot logo change complete
  echo =================================================================
fi

if [ ! -f "/data/params/DongleId" ]; then
  echo -n "N/A" > /data/params/d/DongleId;
fi

echo =================================================================
echo change public GithubSshkeys and force ssh enable
cp -f /data/openpilot/installer/fonts/GithubSshKeys /data/params/d/GithubSshKeys;
chmod 600 /data/params/d/GithubSshKeys
echo -n "Public Key" > /data/params/d/GithubUsername;
setprop persist.neos.ssh 1
echo =================================================================

exec ./launch_chffrplus.sh