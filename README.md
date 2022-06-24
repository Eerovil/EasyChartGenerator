
# Clone Hero difficulties generator script

How to use:

* Download script from `https://github.com/Eerovil/EasyChartGenerator/blob/main/easygen.py`
* Usage: `python3 easygen.py mysong.chart`

Will generate a new file called easy_mysong.chart in the current directory.

Get more options with --help flag

GUI:

Ubuntu 20:

`python3 -m pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04 wxPython`
`python3 -m pip install Gooey`
`python3 graphical_interface.py`


Change Log:

23-06-2022 @ 05:00 GMT: Screenshots: https://imgur.com/a/pBLCUqS
* Fixed songs with star power
* Fixed songs with events
* Fixed songs with existing parts
* Don't always replace exisiting parts (set FORCE_REPLACE_PARTS if you need this)

24-06-2022 @ 17:00 GMT:
* Added batch support
* Added in_place support
* Added easy/medium/hard difficulty support
* Added automatic bpm cutoff support
