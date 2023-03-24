# libPixoo64

A Python library for the Divoom Pixoo 16 / 64.

# Usage

Please see `pixooapi/pixoo.py` and `pixooapi/types.py`

```python


from pixooapi import pixoo

# Find all Pixoo devices on your network
devices = pixoo.findDevices()
# >>> [{'DeviceName': 'Pixoo64', 'DeviceId': 100022491, 'DevicePrivateIP': '192.168.1.100', 'DeviceMac': 'a4bed121fa10'}]

# Then tell the pixoo module to use the first device
pixoo.setDevice(devices[0])
# >>> {'DeviceName': 'Pixoo64', 'DeviceId': 100022491, 'DevicePrivateIP': '192.168.1.100', 'DeviceMac': 'a4bed121fa10'}

# Or alternatively, get the first device on the network
pixoo.device = pixoo.getFirstDevice()
# >>> {'DeviceName': 'Pixoo64', 'DeviceId': 100022491, 'DevicePrivateIP': '192.168.1.100', 'DeviceMac': 'a4bed121fa10'}

# Set a heartbeat packet to the device
pixoo.heartbeat()
# >>> True 

# Read a list of commands from a URL and execute them
pixoo.sendCommandsFromURL(ipAddress="192.168.1.100", url="https://example.com/commandlist.txt")
# >>> True

# Gets the device's settings
pixoo.getSettings()
# >>> {"Brightness": 100, "RotationFlag": 1, ...}

# Gets the brightness of the screen
pixoo.getBrightness()
# >>> 100

# Gets the brightness of the screen
pixoo.setBrightness(brightness=100)
# >>> 100

# Set the white balance of the screen
rgb = {"Red": 255, "Green": 255, "Blue": 255}
# rgb = "FFCCFF"
# rgb = "#FFCCFF"
# rgb = pixoo.Colour(255, 128, 255)
# rgb = (255, 128, 255)
# rgb = [255, 128, 255]
pixoo.setWhiteBalance(rgb=rgb)
# >>> Colour(255, 255, 255)

# Set the channel (the currently displayed thing on the Pioo) to the visualizer
pixoo.setChannel(channel=pixoo.Channels.VISUALIZER.value)
# >>> 2

# Get the current channel as an integer
pixoo.getChannel()
# >>> 2

# Turn the screen on or off
pixoo.screenOn()
# >>> True
pixoo.screenOff()
# >>> False
# True for screen on, False for off
pixoo.setScreenState(state=True)
# >>> True

# Set the latitude / longitude so you can get the weather
pixoo.setLatLong(latitude=-12, longitude=34)
# >>> { "Latitude": -12, "Longitude": 34 }

# Gets the weather
pixoo.getWeather()
# >>> { "Weather": "Cloudy", "CurTemp": 22.00, ... }

# Set the temperature mode (e.g. metric or imperial)
pixoo.setTemperatureMode(mode=pixoo.TemperatureMode.FAHRENHEIT.value)
# >>> 1

# Switch to the custom channel and set the page (in the Divoom app, these are Custom 1, Custom 2 and Custom 3)
pixoo.setCustomPage(page=1)
# >>> 1

# Switch to the clock face channel and set the clock face to a specific ID
pixoo.setClockFace(clockFaceId=12)
# >>> 12

# Sets / stops a timer. Max timer is 59 minutes, 59 seconds. Timers longer than this will cause the timer to stop immediately
timer = 90 # Seconds
# timer = datetime.datetime(year=2023, month=3, day=1, hour=15, minute=0, second=0)
# timer = datetime.timedelta(seconds=60)
# timer = pixoo.Timer(minutes=2, seconds=30)
pixoo.setTimer(time=time, start=True)
# >>> datetime.timedelta(seconds=90)

# Start / stops / reset a stopwatch
pixoo.setStopwatch(start=False, reset=True)
# >>> True

# Sets the scoreboard scores.
pixoo.setScoreboard(redScore=10, blueScore=15)
# >>> { "Red": 10, "Blue": 15 }

# Reboot the device
pixoo.reboot()
# >>> True

# Sets the position of the EQ
pixoo.setVisualzerEQPosition(0)
# >>> 0

# Set the cloud category. See CloudChannelCategory in types.py for the other values
pixoo.setCloudChannelCategory(pixoo.CloudChannelCategory.RECOMMENDED.value)
# >>> 0

# Turns on the dB (noise) meter
pixoo.setNoiseMeter(True)
# >>> True

# Sends a GIF to the display
giftype = pixoo.GIFType.LOCALFILE.value
filename = "c:\\users\\JohnSmith\\Pictures\\MyGIF.gif"
pixoo.sendGIF(type=giftype, filename=filename)

# Draw text to the screen (only after using sendGIF with the LOCALFILE, DATA or URL GIF types)
textOptions = [{
    id: 0,
    x: 0,
    y: 0,
    direction: pixoo.TextDirection.LEFT.value,
    font: 8,
    width: 64,
    text: "Hello World!",
    colour: "#FF0000"
}, {
    id: 1,
    x: 0,
    y: 21,
    direction: pixoo.TextDirection.LEFT.value,
    font: 8,
    width: 64,
    text: "Another Line!",
    colour: "#00FF00"
}]

pixoo.drawText(options=textOptions)
# >>> [0, 1]

# There's a bunch of functions that are only accessible with a Divoom account. These are:

# Log in to the Divoom online API / your Divoom account
user = pixoo.divoomLogin(email="user@example.com", password="MyPassword1234")
# >>> {'Token': 1679639166, 'UserId': 402379837} 

# Log out of your Divoom account
pixoo.divoomLogout(userID=user.UserId, token=user.Token)
# >>> True

# Get all the alarms you've set
pixoo.getAlarms()
# >>> []

alarmTime = datetime.time(hour=8, minute=0)
pixoo.setAlarm(time=alarmTime)
# >>> 0

```