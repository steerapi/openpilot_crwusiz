How to install on Oneplus 3t
------
1. clone openpilot to /data/ and make sure it's named openpilot:

```
first install latest support op3t neos15 is openpilot v0.8.2
custom software install -> https://smiskol.com/fork/crwusiz-open

connect ssh
cd /data/ && mv openpilot openpilot082 
rm -fr openpilot; git clone https://github.com/crwusiz/openpilot.git openpilot; cd openpilot; git checkout master0810t
```

2. run command:

```
cd /data/openpilot/scripts && ./op3t_neos_update.sh
```

3. Let it download and complete it update, after a couple of reboot, your screen will then stay in fastboot mode.


4. In fastboot mode, select use volume button to select to `Recovery mode` then press power button.


5. In Recovery mode, tap `apply update` -> `Choose from emulated` -> `0/` -> `update.zip` -> `Reboot system now`


6. You should be able to boot into openpilot, `if touch screen is not working`, try to `reboot` again.
