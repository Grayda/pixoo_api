# pixoo_api

A Python library for the Divoom Pixoo 16 / 64.

# Usage

Run `python -m pydoc pixooapi.pixoo` and `python -m pydoc -w pixooapi.types` to see the complete, up-to-date documentation

```python


from pixooapi import pixoo

# Find all Pixoo devices on your network
alldevices = pixoo.findDevices()
# >>> [{'DeviceName': 'Pixoo64', 'DeviceId': 100022491, 'DevicePrivateIP': '192.168.1.100', 'DeviceMac': 'a4bed121fa10'}]

# Then tell the pixoo module to use the first device
pixoo.setDevice(deviceDetails=alldevices[0])
# >>> {'DeviceName': 'Pixoo64', 'DeviceId': 100022491, 'DevicePrivateIP': '192.168.1.100', 'DeviceMac': 'a4bed121fa10'}

# Or alternatively, get the first device on the network and set it.
pixoo.setDevice(deviceDetails=pixoo.getFirstDevice())
# >>> {'DeviceName': 'Pixoo64', 'DeviceId': 100022491, 'DevicePrivateIP': '192.168.1.100', 'DeviceMac': 'a4bed121fa10'}

# Set a heartbeat packet to the device
pixoo.heartbeat()
# >>> True 

# Send a bunch of commands together
pixoo.sendBatchCommands(parameters=[{
            “Command”:”Channel/SetBrightness”,
            “Brightness”:100
        }, {
            “Command”:”Device/SetWhiteBalance”,
            “RValue”:100,
            “GValue”:100,
            “BValue”:100
        }])
# >>> True

# Manually send a command
pixoo.sendCommand(command="Channel/SetBrightness", parameters={ "Brightness": 100 })
# >>> { "Brightness": 100 }

# Read a list of commands from a URL and execute them. 
# File should be the same format as sendBatchCommands
pixoo.sendCommandsFromURL(url="https://example.com/commandlist.json")
# >>> True

# Gets the device's settings
pixoo.getSettings()
# >>> {"Brightness": 100, "RotationFlag": 1, ...}

# Set the current time
pixoo.setTime(time=datetime.time(13, 0, 0))

# Gets the current time from the clock
pixoo.getTime()
# >>> datetime.time(13, 0, 0)

# Set the current timezone
pixoo.setTimezone(timezone="GMT-5")
# >>> GMT-5

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
pixoo.setVisualzerEQPosition(position=0)
# >>> 0

# Set the cloud category. See CloudChannelCategory in types.py for the other values
pixoo.setCloudChannelCategory(category=pixoo.CloudChannelCategory.RECOMMENDED.value)
# >>> 0

# Turns on the dB (noise) meter
pixoo.setNoiseMeter(enabled=True)
# >>> True

# Sends a GIF to the display
giftype = pixoo.GIFType.LOCALFILE.value
filename = "c:\\users\\JohnSmith\\Pictures\\MyGIF.gif"
pixoo.sendGIF(type=giftype, filename=filename)
# >>> True

# Get the ID of the GIF currently playing
pixoo.getGIFID()
# >>> 0

# Reset the GIF ID
pixoo.resetGIFID()
# >>> 0

# Draw text to the screen (only after using sendGIF with the LOCALFILE, DATA or URLDATA GIF types)
textOptions = [{
    "id": 0,
    "x": 0,
    "y": 0,
    "direction": pixoo.TextDirection.LEFT.value,
    "font": 8,
    "width": 64,
    "text": "Hello World!",
    "colour": "#FF0000"
}, {
    "id": 1,
    "x": 0,
    "y": 21,
    "direction": pixoo.TextDirection.LEFT.value,
    "font": 8,
    "width": 64,
    "text": "Another Line!",
    "colour": "#00FF00"
}]

pixoo.drawText(options=textOptions)
# >>> [0, 1]

# There's a bunch of functions that are only accessible with a Divoom account. These include:

# Log in to the Divoom online API / your Divoom account
pixoo.divoomLogin(email="user@example.com", password="MyPassword1234")
# >>> {'Token': 1679639166, 'UserId': 402379837} 

# Get details about the user
print(pixoo.user)
# >>> {'Token': 1679639166, 'UserId': 402379837} 

# Manually send a command to the Divoom online API
pixoo.sendOnlineCommand(command="Alarm/Get")
# >>> [{ "AlarmId": 0, "AlarmName": "Alarm", "AlarmTime": 1679639166, "DeviceId": 100022491, "EnableFlag": 1, "ImageFileId": '', "RepeatArray": [1, 1, 1, 1, 1, 1, 1] }, { "AlarmId": 1, ... }]

# Set some alarms
alarmTime1 = datetime.time(hour=8, minute=0)
pixoo.setAlarm(time=alarmTime1)
# >>> 0
alarmTime2 = datetime.time(hour=9, minute=0)
pixoo.setAlarm(time=alarmTime2)
# >>> 1
pixoo.deleteAlarm(id=0)
# pixoo.deleteAlarm("all")
# >>> 0

# Get all the alarms you've set
pixoo.getAlarms()
# >>> [{ "AlarmId": 0, "AlarmName": "Alarm", "AlarmTime": 1679639166, "DeviceId": 100022491, "EnableFlag": 1, "ImageFileId": '', "RepeatArray": [1, 1, 1, 1, 1, 1, 1] }, { "AlarmId": 1, ... }]

# Set Night Mode to dim the display during certain hours
pixoo.setNightMode(state=True, start=datetime.time(23, 30, 0), end=datetime.time(6, 0, 0), brightness=50)
# >>> { "start": datetime.time(23, 30, 0), "end": datetime.time(6, 0, 0), "state": True, "brightness": 50 }

# Get the night mode settings
pixoo.getNightMode()
# >>> { "start": datetime.time(23, 30, 0), "end": datetime.time(6, 0, 0), "state": True, "brightness": 50 }

# Set the date format. To get the date format, use getSettings()
pixoo.setDateFormat(format=pixoo.DateFormat.YYYYMMDDHYPHEN.value)
# >>> 0

# Sets the enhanced brightness mode to make the display
# brighter. Requires a 5V, 3A or higher power supply
# otherwise the device will just continuously reboot
pixoo.setEnhancedBrightnessMode(enabled=True)
# >>> True

# Sets the device to 12 or 24 hour mode
pixoo.setHourMode(mode=pixoo.TimeMode.TIME12HOUR.value)
# >>> 0

# Mirror the display
pixoo.setMirroredMode(mirrored=True)
# >>> True

# Rotate the display
pixoo.setRotationAngle(angle=pixoo.Rotation.ROTATE180.value)
# >>> 2

# Log out of your Divoom account
pixoo.divoomLogout(userID=user.UserId, token=user.Token)
# >>> True

```