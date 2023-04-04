from requests import request
from typing import List
from urllib.parse import urlparse  # For validating URLs
from PIL import Image, ImageOps
import datetime
import base64
import hashlib
from io import BytesIO
from math import floor
import json

# Import our enums and such so that you can easily use them in the same class
from pixooapi.types import *

# The device that we're communicating with.
device: dict | DivoomDevice = None

# Your user details, if logging in to the Divoom API (instead of the local one)
user: dict | DivoomUser = None

# A list of alarms set on the device
alarms: list[Alarm] = []


def getFirstDevice():
    """
    Get the first Pixoo found on the network

    Finds and returns the first Pixoo device found on the network

    Parameters
    ----------

    Returns
    -------

    DivoomDevice | None
        The first device found, or None if nothing found 

    """

    # Find all the devices on the same network
    foundDevices = findDevices()

    # If we found one, return the first one, otherwise, return None
    if len(foundDevices) > 0:
        return foundDevices[0]
    else:
        return None


def setDevice(deviceDetails: dict | str | DivoomDevice = None):
    """
    Set the device for API calls

    Sets the device that will be used for subsequent API calls.

    Parameters
    ----------

    device : dict | str | DivoomDevice, optional
        Defaults to None. If a dict is passed, 

    Returns
    -------

    DivoomDevice
        Returns a DivoomDevice

    """

    global device

    # If we passed a string (i.e. an IP address)
    if isinstance(device, str):
        # Find all the devices and pick the first one that matches the IP address.
        # Technically we don't need to findDevices(), but for the online commands we need the device ID
        devices = findDevices()

        search = {"DevicePrivateIP": device}
        for d in devices:
            if {key: d[key] for key in d.keys() & search} == search:
                device = d
                break

        if len(devices) > 0:
            device = devices[0]
        else:
            raise Exception("No devices found!")
    # If we were handed a string (i.e. an IP address), set as appropriate
    elif isinstance(deviceDetails, DivoomDevice):
        device = deviceDetails
    elif isinstance(deviceDetails, dict):
        print(device)
        device = DivoomDevice(DevicePrivateIP=deviceDetails["DevicePrivateIP"], DeviceMac=deviceDetails["DeviceMac"],
                        DeviceId=deviceDetails["DeviceId"], DeviceName=deviceDetails["DeviceName"])

    return device


def _checkForDevice():
    """
    Check that a device has been discovered / set

    Checks that device is properly set.

    Parameters
    ----------

    Returns
    -------

    bool
        Returns True if device is set, False otherwise
    """

    return device is not None and isinstance(device, DivoomDevice)

def _isLoggedIn():
    """
    Check if the user has logged in to Divoom

    Checks if the user has logged in to their Divoom account

    Parameters
    ----------

    Returns
    -------

    bool
        Returns True if the user has logged in, False if not

    """

    return user is not None and isinstance(user, DivoomUser)

def sendOnlineCommand(command: str, parameters={}):
    """
    Send a command to the Divoom Online API

    Sends a command to Divoom's online API. This constructs the necessary payload for you

    Parameters
    ----------

    command : str
        The command you want to call (e.g. Alarm/Get)
    parameters : dict
        Any additional parameters you want to send (e.g. { "EqPosition": 0 })

    Returns
    -------
    dict
        Returns the results
    Exception
        Returns an exception if the API or the request returned an error

    """

    # If the command we're calling is one of the "doesn't require login" ones
    if command in ["UserLogin", "UserLogout", "Device/ReturnSameLANDevice"]:

        # Just call the API
        try:
            print(command)
            return callPixooAPI(data=parameters, hostname="appin.divoom-gz.com", endpoint=command, https=True)
        except Exception as e:
            raise e

    else:

        # And if we haven't logged in
        if not _isLoggedIn():
            
            # Return an error, because we need to log in to use these
            raise Exception(
                "Can't call command, not logged in to Divoom API!")

        # Or if we haven't set a device 
        elif not _checkForDevice():
            raise Exception(
                "Can't call command, no device set!")

    # Add the common fields here
    data = {
        "DeviceId": device["DeviceId"],
        "Token": user["Token"],
        "UserId": user["UserId"]
    }

    # Then tack on any parameters (which are a dictionary)
    data.update(parameters)
    
    try:
        return callPixooAPI(data=data, hostname="appin.divoom-gz.com", endpoint=command, https=True)

    except Exception as e:
        raise e


def sendCommand(command: str, parameters={}, batch=False):
    """
    Send a command to the device

    Sends a command to the device. This puts together the necessary payload

    Parameters
    ----------

    command : str
        The command you want to call (e.g. Channel/SetEqPosition)
    parameters : dict
        Any additional parameters you want to send (e.g. { "EqPosition": 0 })
    port : int, optional
        The port to send on. Defaults to port 80 if not specified
    batch : bool
        If True, will return the command instead of executing it. You can use this to send multiple commands in one API call using Draw/CommandList, or you can save it to a server and call Draw/UseHTTPCommandSource

    Returns
    -------
    dict
        If batch is False, the response as a dict. If batch is True, the command
    Exception
        Returns an exception if the API or the request returned an error

    """

    if not _checkForDevice():
        raise Exception("No device has been set up")

    # Add the common fields here
    data = {
        "Command": command
    }

    # Then tack on any parameters (which are a dictionary)
    data.update(parameters)

    try:
        # If we're batching calls, just return the command, ready to send
        if batch:
            return data
        # Otherwise, send the call.
        else:
            return callPixooAPI(data=data)

    except Exception as e:
        raise e


def sendBatchCommands(parameters: list[dict], port=80, wait=False):
    """
    Send multiple commands to the device

    Seconds a batch of commands to the device. 

    Parameters
    ----------

    parameters : list[dict]
        A list of commands to send. Same format as sendCommand, but in a list
    port : int, optional
        The port to send on. Defaults to port 80 if not specified

    Returns
    -------
    
    bool
        Returns True, as the API won't return the results for each request. This means you can't use this to retrieve the weather and settings in one call, for example
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        response = sendCommand(command="Draw/CommandList",
                               parameters={"CommandList": parameters}, port=port, wait=wait)
    except Exception as e:
        raise e

    return response


def callPixooAPI(data: dict, hostname=None, endpoint="post", https=False):
    """
    Send a message to the device or online API

    Sends data to the device or online API using the requests library

    Parameters
    ----------

    data : dict
        A dictionary that contains a valid Command, and optional parameters
    hostname : str, optional
        The ipAddress or hostname to send the command to. Defaults to the first discovered Pixoo on the network
    endpoint : str, optional
        The command you want to run. To get a list of alarms, this would be "Alarm/Get". Defaults to "post"
    https : bool, optional
        If true, uses HTTPS instead of HTTP

    Returns
    -------
    dict
        The response as a dict
    Exception
        Returns an exception if the API or the request returned an error

    """

    if hostname is None:
        hostname = device["DevicePrivateIP"]

    url = "http{s}://{hostname}/{endpoint}".format(
        s="s" if https else "", hostname=hostname, endpoint=endpoint)
    parsedUrl = urlparse(url)
    # If we've got a valid URL
    if all([parsedUrl.scheme, parsedUrl.netloc]):
        response = request(
            method="post", url=url, json=data).json()
    else:
        raise Exception("URL {url} is not valid!".format(url=url))

    if response:
        # Now we need to check for errors
        error = _checkForErrors(response)

        if error:
            raise Exception("Error code returned from API: {message} ({code})".format(
                message=error["message"], code=error["code"]))

    return response


def _checkForErrors(response: dict):
    """
    Checks a response for errors

    Looks through a response from the API and tries to discover any error messages

    Parameters
    ----------
    response : dict
        The dictionary to look through

    Returns
    -------
    None
        If no errors are found, None is returned
    Exception
        If an error is found, the error is returned. This lets the other functions raise errors

    """

    error = {}

    # If we've got a ReturnCode
    if "ReturnCode" in response:
        if response["ReturnCode"] != 0:
            error["message"] = response["ReturnMessage"]
            error["code"] = response["ReturnCode"]

    # If we've got an error_code instead..
    if "error_code" in response:
        if response["error_code"] != 0:
            error["message"] = "n/a"
            error["code"] = response["error_code"]

    if error:
        return error
    else:
        return None


def heartbeat():
    """
    Send a heartbeat packet

    Sends a heartbeat message to the device. Doesn't really do much, other than confirm
    that the device is powered on and accepting messages. The Divoom app mostly uses it

    Parameters
    ----------

    Returns
    -------
    bool
        Returns True on success

    Exception
        Returns an exception if the API or the request returned an error        
    """

    try:
        # IMPORTANT: That's not a typo! It really is "Hearbeat", with the missing "T" in the middle!!
        sendCommand(command="Device/Hearbeat")
    except Exception as e:
        raise e

    return True


def findDevices():
    """
    Find devices on the network

    Finds any devices on the local network. 

    Parameters
    ----------


    Returns
    -------
    list
        A list of dictionaries, each dictionary containing a device.

        A device dict will include:

        DeviceName : str
            The name of the device. For a Pixoo64, it'll default to "Pixoo64"
        DeviceId : int
            The unique ID of the device. Will look something like this: 300000020
        DevicePrivateIP : str
            The IP address of the device
        DeviceMac : str
            The MAC address of the device. No colons between the bytes. Will look similar to this: "a8032aff46b1"
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        response = sendOnlineCommand(command="Device/ReturnSameLANDevice")
    except Exception as e:
        raise e

    return response["DeviceList"]


def sendCommandsFromURL(url: str):
    """
    Execute commands from a URL

    Retrieves a set of commands from a URL and executes them. You can use this to batch together calls to
    make your own display dashboard or similar (e.g. send a command to draw an image, send a command to draw text, etc.)

    Parameters
    ----------

    url : str
        A valid URL. Should contain a list of commands as JSON. For example:

        [{
            “Command”:”Channel/SetBrightness”,
            “Brightness”:100
        }, {
            “Command”:”Device/SetWhiteBalance”,
            “RValue”:100,
            “GValue”:100,
            “BValue”:100
        }]

    Returns
    -------
    bool
        Returns True if successful. Using this will not return results, so if you request the weather, it won't return the weather
    Exception
        Returns an exception if the API or the request returned an error or if the URL isn't valid

    """

    try:

        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            sendCommand(command="Draw/UseHTTPCommandSource",
                                parameters={"CommandUrl": url})
        else:
            raise Exception("URL {url} is not valid!".format(url=url))

    except Exception as e:
        raise e

    return True


def getSettings():
    """
    Gets the device settings

    Gets the device settings. 

    Parameters
    ----------


    Returns
    -------
    dict
        A dictionary of values. This includes:

        Brightness : int
            The screen brightness, between 0-100
        RotationFlag : int
            Whether images will rotate (cycle). Can be one 0 to not cycle between images, or 1 to cycle. This is different from physical screen rotation (e.g. rotate display by 180 degrees so you can hang it upside down)
        ClockTime : int
            How long to display each clockface before moving to the next one.
        GalleryTime : int
            How long to display each gallery for. I assume this means it'll display the Emoji gallery for 60 seconds, then move to the Photos gallery, and so on
        SingleGalleyTime : int
            How long to display a single GIF in a gallery.
        PowerOnChannelId : int
            The channel that will load when you first power up the device
        GalleryShowTimeFlag : int
            Whether to display the time in the top right-hand corner of the display. Can be 0 to hide, 1 to show
        CurClockId : int
            The current clockface ID
        Time24Flag : int
            The clock format. Can be one of the following:

            Time.TIME12HOUR : int
                Will show the time, in 12 hour format
            Time.TIME24HOUR : int
                Will show the time, in 24 hour format
        TemperatureMode : int
            The temperature mode to use. Can be one of the following:

            TemperatureMode.CELSIUS : int
                Metric units, Celsius
            TemperatureMode.FAHRENHEIT : int
                Imperial units, Fahrenheit 
        GyrateAngle : int
            The rotation of the display. This is the actual orientation of the picture, and not the same as RotationFlag above. Can be one of the following:

            Rotate.ROTATE0 : int
                Returns the screen to 0 degrees rotation
            Rotate.ROTATE90 : int
                Rotates the screen to 90 degrees
            Rotate.ROTATE180 : int
                Rotates the screen 180 degrees 
            Rotate.ROTATE270 : int
                Rotates the screen 270 degrees
        MirrorFlag : int
            Whether the image is mirrored or not. 0 = normal orientation, 1 = mirrored image
        LightSwitch : int
            Whether the screen is on or off. 0 = off, 1 = on
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        response = sendCommand(command="Channel/GetAllConf")

        # Delete the error code, as if we've reached this point, we haven't hit an error
        del response["error_code"]

    except Exception as e:
        raise e

    return response

def getBrightness():
    """
    Get the brightness of the device

    Gets the screen brightness of the device

    Parameters
    ----------


    Returns
    -------
    int
        The brightness of the screen, between 0 and 100
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        response = getSettings()
    except Exception as e:
        raise e

    return int(response["Brightness"])


def setBrightness(brightness: int):
    """
    Set the brightness of the device

    Sets the screen brightness of the device

    Parameters
    ----------

    brightness : int
        The brightness to set the display to. Between 0 and 100. Values higher than 100 get clamped to 100

    Returns
    -------
    int
        The brightness of the screen, between 0 and 100
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        sendCommand(command="Channel/SetBrightness",
                            parameters={"Brightness": brightness})
    except Exception as e:
        raise e

    # Get the actual display brightness from the API and return that to confirm the change was made.
    return getBrightness()


def setWhiteBalance(rgb: Colour | str | dict | list | tuple):
    """
    Set the white balance of the device.

    Adjusts the white balance of the device using an RGB format.

    Parameters
    ----------

    rgb : Colour | str | dict | list | tuple
        Can be one of the following:

        Colour
            An instance of the Colour NamedTuple that has red, green and blue
        str
            A hex string with or without the #
        dict 
            A dictionary that has red, green and blue keys 
        list
            A list with [red, green, blue]
        tuple
            A tuple with (red, green, blue)

        A named tuple that has red, green and blue values

    Returns
    -------
    NamedTuple
        A named tuple that has red, green and blue values
        TODO: See if there's a way to get the white balance from the API, instead of just returning the user-supplied value
    Exception
        Returns an exception if the API or the request returned an error        

    """

    rgbColour = Colour(0, 0, 0)

    try:

        if isinstance(rgb, str):
            rgbColour = tuple(int(rgb[i:i+2], 16) for i in (0, 2, 4))

        if isinstance(rgb, tuple) or isinstance(rgb, list):
            rgbColour = Colour(rgb[0], rgb[1], rgb[2])
        elif isinstance(rgb, dict):
            rgbColour = Colour(rgb.red, rgb.green, rgb.blue)

        sendCommand(command="Device/SetWhiteBalance",
                            parameters={"RValue": rgbColour.red, "GValue": rgbColour.green, "BValue": rgbColour.blue})
    except Exception as e:
        raise e

    return rgb


def getChannel():
    """
    Get the currently displayed channel

    Gets the currently displayed channel on the device.

    Parameters
    ----------


    Returns
    -------
    int
        The channel the device is set to. See the Channels enum for more information
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        response = sendCommand(command="Channel/GetIndex")
    except Exception as e:
        raise e

    return response["SelectIndex"]


def setTimezone(timezone: str):
    """
    Set the device timezone

    Sets the timezone on the device. 

    Parameters
    ----------

    timezone : str
        The timezone to set. Must be a string like "GMT-5" or "UTC"

    Returns
    -------

    str
        The timezone you just passed.
    Exception
        Returns an exception if the API or the request returned an error  
    
    """

    try:
        sendCommand(command="Sys/TimeZone", parameters={ "TimeZoneValue": timezone })
    except Exception as e:
        raise e
    
    return timezone

def getTime():
    """
    Get the device's current time

    Gets the currently set time on the device

    Parameters
    ----------

    Returns
    -------

    datetime.datetime
        The time as a datetime.datetime

    """

    try:
        response = sendCommand(command="Device/GetDeviceTime")
        time = datetime.datetime.fromtimestamp(response["UTCTime"])

    except Exception as e:
        raise e

    return time

def setTime(time: int | datetime.datetime):
    """
    Set the time on the device

    Sets the time on the device.

    Parameters
    ----------

    time : int | datetime.datetime | datetime.time
        The time to set. Can be a datetime or a Unix timestamp

    Returns
    -------

    datetime.datetime
        The time you passed as a datetime.datetime

    """

    try:

        if isinstance(time, datetime.datetime):
            time = time.timestamp()

        sendCommand(command="Device/SetUTC", parameters={ "Utc": time })
    except Exception as e:
        raise e

    return datetime.datetime.fromtimestamp(time)

def setHourMode(mode: TimeMode | int):
    """
    Set 12 or 24 mode

    Sets the clock to 12 or 24 hour mode

    Parameters
    ----------

    mode : TimeMode | int 
        The mode to set. If an integer, 0 = 12 hour mode, 1 = 24 mode
        TimeMode cna be one of the following:

        TimeMode.TIME12HOUR
        TimeMode.TIME24HOUR

    Returns
    -------

    int
        Returns the time mode. 0 for 12 hour mode, 1 for 24 hour mode

    """

    try:
        sendCommand(command="Device/SetTime24Flag", parameters={ "Mode": mode })
    except Exception as e:
        raise e

    return mode


def setEnhancedBrightnessMode(enabled: bool):
    """
    Set Enhanced Brightness Mode

    Sets enhanced brightness mode. To use this, the device must be
    plugged into a 5v, 3A or higher USB adapter.

    This setting doesn't persist between reboots, so you'll need to
    set it each time you want the brightness

    Parameters
    ----------

    enabled : bool
        True for enhanced brightness, False for regular brightness

    Returns
    -------

    bool
        True for enabled, False for disabled
    """

    try:
        sendOnlineCommand(command="Sys/SetConf", parameters={ "HighLight": mode })
    except Exception as e:
        raise e

    return mode


def setDateFormat(format: DateFormat):
    """
    Set Date Format

    Sets the date format

    Parameters
    ----------

    format : DateFormat
        The date format. Can be one of:

        DateFormat.YYYYMMDDHYPHEN
            YYYY-MM-DD
        DateFormat.DDMMYYYYHYPHEN
            DD-MM-YYYY
        DateFormat.MMDDYYYYHYPHEN
            MM-DD-YYYY
        DateFormat.YYYYMMDDPERIOD
            YYYY.MM.DD
        DateFormat.DDMMYYYYPERIOD
            DD.MM.YYYY
        DateFormat.MMDDYYYYPERIOD
            MM.DD.YYYY

    Returns
    -------

    int
        The format it's set to
    """

    try:
        sendOnlineCommand(command="Sys/SetConf", parameters={ "DateFormat": format })
    except Exception as e:
        raise e

    return format

def setRotationAngle(angle: Rotation):
    """
    Rotate the display

    Rotates the display. Useful if you're mounting your device in a strange way

    Parameters
    ----------

    angle : Rotation
        The angle to rotate the device. Can be one of the following:

        Rotation.ROTATE0
            No rotation
        Rotation.ROTATE90
            Rotated right
        Rotation.ROTATE180
            Rotated 180
        Rotation.ROTATE270
            Rotated left 

    Returns
    -------

    int
        The angle of the display

    """

    try:
        sendCommand(command="Device/SetScreenRotationAngle", parameters={ "Mode": angle })
    except Exception as e:
        raise e
    
    return angle

def setMirroredMode(mirrored: bool):
    """
    Set mirrored mode

    Mirrors the display. Useful if mounting to be viewed in a mirror
    (for example, in an infinity mirror setup or something?)

    Parameters
    ----------

    mirrored : bool
        If the display should be mirrored. True for mirrored, False for not

    Returns
    -------

    bool
        True for mirrored, False for not

    """

    try:
        sendCommand(command="Device/SetMirrorMode", parameters={ "Mode": int(mirrored) })
    except Exception as e:
        raise e
    
    return mirrored

def setChannel(channel: Channels):
    """
    Set the currently displayed channel

    Sets the currently displayed channel on the device.

    Parameters
    ----------

    channel: Channels
        The channel to switch to. Valid values include:

            Channels.CLOCK : int
                Also called faces in the Divoom documentation
            Channels.CLOUD : int
                Displays GIFs from the source you've picked, such as most liked animations, images you've liked etc.
            Channels.VISUALIZER : int
                Displays the audio visualizer
            Channels.CUSTOM : int
                Displays 1 of 3 groups of custom GIFs that you've added. These groups are called pages in the API
            Channels.BLANK : int
                Displays no image (i.e. a blank screen). To power down (turn off) the display instead, use setScreenState.

    Returns
    -------
    int
        The channel the device is set to.
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        sendCommand(command="Channel/SetIndex",
                            parameters={"SelectIndex": channel})
    except Exception as e:
        raise e

    return getChannel()


def screenOn():
    """
    Shortcut method for setScreenState

    Helper method for setScreenState

    Parameters
    ----------


    Returns
    -------
    bool
        The state of the screen. Will be True for on
    Exception
        Returns an exception if the API or the request returned an error

    """

    return setScreenState(state=True)


def screenOff():
    """
    Shortcut method for setScreenState

    Helper method for setScreenState

    Parameters
    ----------


    Returns
    -------
    bool
        The state of the screen. Will be False for off
    Exception
        Returns an exception if the API or the request returned an error

    """

    return setScreenState(state=False)


def setScreenState(state: Screen | bool):
    """
    Turn the screen on or off

    Turns the screen on or off

    Parameters
    ----------

    state : Screen | bool
        The state of the screen. Can be one of the following:

        Screen.ON | True : int | bool
            Turns the screen on
        Screen.OFF | False : int | bool
            Turns the screen off 

    Returns
    -------
    bool
        The state of the screen. False for off, True for on
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        sendCommand(command="Channel/OnOffScreen",
                            parameters={"OnOff": int(state)})
        state = getSettings()
    except Exception as e:
        raise e

    return bool(int(state["LightSwitch"]))


def setLatLong(latitude: float, longitude: float):
    """
    Sets the latitude and longitude

    Sets the latitude and longitude which is used to retrieve the weather

    Parameters
    ----------

    latitude : float
        The latitude, between -90 and 90
    longitude : float
        The longitude, between -180 and 180

    Returns
    -------
    dict
        The latitude and longitude as a dictionary (e.g. { "Latitude": -12, "Longitude": 34 })
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Sys/LogAndLat",
                            parameters={"Latitude": latitude, "Longitude": longitude})
    except Exception as e:
        raise e

    return {"Latitude": latitude, "Longitude": longitude}


def getWeather():
    """
    Retrieves the weather

    Gets the weather using the latitude and longitude that has previously been set.
    Weather is provided by OpenWeatherMap

    Parameters
    ----------


    Returns
    -------
    dict
        Returns a dictionary containing both the weather, plus the temperature mode (so you can add the appropriate suffix, like C or F)
        The dictionary will contain: 

        Weather : str
            The current conditions, as a string
        CurTemp : float
            The current temperature
        MinTemp : float
            The minimum temperature for the day
        MaxTemp : float
            The maximum temperature for the day
        Pressure : int
            The current pressure in kPa
        Humidity : int
            The current humidity, in percent
        Visibility : int
            The current visibility, in feet (?)
        WindSpeed : float
            The current wind speed in meters per second 
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        weather = sendCommand(command="Device/GetWeatherInfo")
        settings = getSettings()
    except Exception as e:
        raise e

    # Remove the error code, since we already know the call was successful
    del weather["error_code"]

    # The weather call doesn't include the temperature units, so we include it. Makes parsing the weather easier
    weather.update({
        "TemperatureMode": settings["TemperatureMode"]
    })

    return weather


def setTemperatureMode(mode: TemperatureMode = TemperatureMode.CELSIUS.value):
    """
    Sets the temperature units

    Sets the temperature units on the device to either metric (celsius) or imperial (fahrenheit). I don't think this 
    affects other units like visibility or wind speed. TODO: Confirm this

    Parameters
    ----------

    mode : TemperatureMode, optional
        The mode to set it to. Valid values include:

        TemperatureMode.CELSIUS : int
            Metric units, Celsius
        TemperatureMode.FAHRENHEIT : int
                Imperial units, Fahrenheit 

    Returns
    -------
    int
        The temperature units. 0 for celsius, 1 for fahrenheit
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Device/SetDisTempMode",
                            parameters={"Mode": mode})
        settings = getSettings()
    except Exception as e:
        raise e

    return settings["TemperatureMode"]


def setCustomPage(page: int):
    """
    Set the custom channel

    Changes to the the Custom channel, then sets the custom page.
    In the Divoom app, the custom channel has 3 available pages.
    Each page can display a set of GIFs (and possibly clockfaces?)

    Parameters
    ----------

    page : int
        The page to switch to, zero indexed, 0-2

    Returns
    -------
    int
        The custom page you've switched to
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Channel/SetCustomPageIndex",
                            parameters={"CustomPageIndex": page})

        # TODO: Find a way to get the custom page we're on and return that as confirmation

    except Exception as e:
        raise e

    return page


def setClockFace(clockFaceId: int):
    """
    Sets the active clockface

    Sets the active clockface, and switches to the "Faces" (clock face) channel

    Parameters
    ----------

    clockFaceId : int
        The ID of the clockface. You can get a list by calling getClockFaceList

    Returns
    -------
    int
        Returns the ID of the current clockface (i.e. the one you just set)
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Channel/SetClockSelectId",
                            parameters={"ClockId": clockFaceId})
    except Exception as e:
        raise e

    return clockFaceId


def setTimer(time: Timer | int | datetime.datetime | datetime.timedelta, start=True):
    """
    Set a timer

    Sets a timer. Accepts a few different duration types and converts them to the necessary format

    Parameters
    ----------

    time : Timer | int | datetime.datetime | datetime.timedelta
        The duration of the timer. Accepts a few different time formats:

        Timer: A named tuple with minutes and seconds properties
        int: The duration in seconds
        datetime: A datetime representing when the timer should end.
        timedelta: A datetime delta representing when the timer should end
    start : bool
        Whether to start or stop the timer. True = start, False = stop

    Returns
    -------
    timedelta
        Returns the timedelta of when the timer will finish
    Exception
        Returns an exception if the API or the request returned an error
    """

    # The current date
    timeNow = datetime.datetime.now()

    if isinstance(time, int):
        # Turns the integer into a timedelta
        timeObject = datetime.timedelta(seconds=time)
    elif isinstance(time, Timer):
        # Turns the named tuple into a timedelta
        timeObject = datetime.timedelta(
            minutes=time.minutes, seconds=time.seconds)
    elif isinstance(time, datetime):
        # Turns a datetime into a timedelta
        timeObject = time - timeNow
    elif isinstance(time, datetime.timedelta):
        timeObject = time

    try:
        sendCommand(command="Tools/SetTimer", parameters={
            "Minute": (timeObject.seconds % 3600) // 60, "Second": timeObject.seconds % 60, "Status": start})
    except Exception as e:
        raise e

    return timeObject


def setStopwatch(start: bool | Status, reset=False):
    """
    Start, stop or reset the stopwatch

    Starts, stops or resets the inbuilt stopwatch

    Parameters
    ----------

    start : bool
        If True, starts or resumes the stopwatch. If False, stops it.
    reset : bool
        If True, resets the stopwatch. If False, doesn't reset it. If start == True and reset == True, the stopwatch is reset, then it's started

    Returns
    -------
    bool
        Returns True to indicate the action was completed
    Exception
        Returns an exception if the API or the request returned an error
    """

    # The commands to send to the device. We're using batch mode to avoid having to make two calls to reset and / or start the stopwatch
    commands = []

    if reset:
        commands.append(sendCommand(
            command="Tools/SetStopWatch", parameters={"Status": 2}, batch=True))

    try:
        commands.append(sendCommand(command="Tools/SetStopWatch",
                                            parameters={"Status": int(start)}, batch=True))

        print(commands)
        sendBatchCommands(parameters=commands)

    except Exception as e:
        raise e

    return True


def setScoreboard(redScore: int, blueScore: int):
    """
    Update the scoreboard

    Updates the scoreboard. As far as I can tell, there's no way to read the values. 

    Parameters
    ----------

    redScore : int
        The score to set the red side to
    blueScore : int
        The score to set the blue side to.

    Returns
    -------
    dict
        Returns a dict with "Red" and "Blue"
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendOnlineCommand(command="Tools/SetScoreBoard",
                            parameters={"BlueScore": blueScore, "RedScore": redScore})
    except Exception as e:
        raise e

    return {"Red": redScore, "Blue": blueScore}

def getScoreboard():
    """
    Get the scoreboard scores

    Gets the scoreboard scores. Requires a Divoom account

    Parameters
    ----------

    Returns
    -------

    dict
        Dictionary with two keys, Red and Blue
    Exception 
        Returns an exception if the API or the request returned an error
        
    """

    try:
        response = sendCommand(command="Tools/GetScoreBoard")
    except Exception as e:
        raise e

    return response


def reboot():
    """
    Reboot the device

    Reboots the device immediately. 

    TODO: Stop this from waiting, because the app hangs otherwise.

    Parameters
    ----------


    Returns
    -------
    bool
        Returns True if the API doesn't return an error
    Exception
        Returns an exception if the API or the request returned an error
    """

    # NOTE: You don't need to actually specify the DeviceId like the API suggests.

    try:
        sendCommand(command="Device/SysReboot")
    except Exception as e:
        raise e

    return True


def setVisualizerEQPosition(position: int):
    """
    Set the EQ position of the visualizer

    Sets the EQ position on the visualizer channel

    Parameters
    ----------

    position : int
        The position, starting at 0

    Returns
    -------
    int
        The position you passed in. At this point there's no way to query the device for it's current position
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Channel/SetEqPosition",
                            parameters={"EqPosition": position})
    except Exception as e:
        raise e

    return True


def setCloudChannelCategory(category: CloudChannelCategory | int):
    """
    Set the cloud channel image category

    Sets the type of images to show on the Cloud channel, such as most popular, artists you've subscribed to, etc.

    Parameters
    ----------

    display : CloudChannelCategory | int
        The type of images to show. Can be one of:

        CloudChannelCategory.RECOMMENDED : 0
            The recommended gallery (i.e. popular images)        
        CloudChannelCategory.FAVOURITE : 1
            Images that you've favourited
        CloudChannelCategory.SUBSCRIBED : 2
            Artists that you've subscribed to
        CloudChannelCategory.ALBUM : 3
            Images grouped by category (e.g. Valentine's Day, Christmas, Birds etc.)

    Returns
    -------
    int
        The category you set. 0-3, as shown above
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Channel/CloudIndex",
                            parameters={"Index": category})
    except Exception as e:
        raise e

    return True


def setNoiseMeter(enabled: Status | bool | int):
    """
    Start or stop the noise meter

    Starts or stops the noise meter that shows the noise level in dB

    Parameters
    ----------

    enabled : Status | int | bool
        The status of the noise meter. Can be one of:

        Status.STOP : 0
            Stop the noise meter
        Status.START : 1
            Start the noise meter

    Returns
    -------
    int
        Returns the status you passed
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Tools/SetNoiseStatus",
                            parameters={"NoiseStatus": int(status)})
    except Exception as e:
        raise e

    return status


def _fileToFrames(filename: str, url=False, id=0, resample: Image.Resampling | int = Image.Resampling.BICUBIC.value, size=64, maxFrames = 60):
    """
    Convert a file to base64 frames

    Converts a local file a set of base64 frames intended to be sent to the device

    Parameters
    ----------

    filename : str
        The file or URL to download and convert.
        IMPORTANT: If the GIF has more than 60 frames, it'll be capped to 60 frames.
        This is because of a limitation with the Pixoo API.
    url : bool, optional
        If True, downloads the file from a URL, then runs it. Defaults to False
    id : int, optional
        The ID of this animation. Used with sendGIF. Defaults to 0
    resample : Image.Resampling | int, optional
        If the image is larger than 64px on either side, it's resized. This is 
        the resampling mode that is used. Defaults to bicubic 

    Returns
    -------
    list
        A list, containing RGB values in this format:
        [R, G, B, R, G, B, R, G, B, R, G, B, ...]
    Exception
        Returns an exception if this fails.
    """

    frames = []

    if url:
        file = request(method="get", url=filename)
        img = Image.open(BytesIO(file.content))
    else:
        img = Image.open(filename)

    # Non-animated images don't have frames, so we need to check if the attribute exists and if it doesn't, just set totalFrames to 1
    if not hasattr(img, "n_frames"):
        totalFrames = 1
    elif img.n_frames > maxFrames:
        totalFrames = maxFrames
    else:
        totalFrames = img.n_frames

    # Loop through all the frames in the animation
    for frame in range(0, totalFrames):
        # Go the frame in question
        img.seek(frame)

        # Convert it to RGB because the device expects a list of red, green and blue pixels
        imgrgb = img.convert(mode="RGB")

        if imgrgb.size[0] > size or imgrgb.size[1] > size:
            imgrgb.thumbnail(size=(size, size), resample=resample)
            imgrgb = ImageOps.pad(image=imgrgb, size=(size, size))

        if "duration" in img.info:
            duration = int(img.info["duration"])
        else:
            duration = 1000

        # Pillow has a nice feature to get all the RGB values for an image.
        # We just need to flatten it from a list of tuples to a list, which we do below
        pixels = [item for p in list(
            imgrgb.getdata()) for item in p]

        # Base64 encode the pixels we grabbed from the frame
        b64 = base64.b64encode(bytearray(pixels))

        # Build up our frame data command. We can get the frame duration from the GIF.
        frames.append(GIFData(
            totalFrames=totalFrames, size=imgrgb.size[0], offset=frame, id=id, speed=duration, data=b64.decode("utf-8")))

    return frames


def sendGIF(type: GIFType | int, filename: str | GIFData):
    """
    Play a GIF on the device

    Plays a GIF on the device. Can be from a range of sources, including the SD card,
    a URL, a local file, or even base64 data you send directly.

    Parameters
    ----------

    type : GIFType
        The type of GIF to play. Possible options include:

        GIFType.SDFILE
            Plays a single GIF from the SD card
        GIFType.SDFOLDER
            Plays a folder of GIFs from the SD card
        GIFType.URL
            Tells the device to play the GIF from the specified URL. Must already be 64x64 RGB
        GIFType.URLDATA
            Downloads the GIF and plays it, much like GIFType.LOCALFILE, but supporting a URL instead
        GIFType.DATA
            Plays a data URI that you send it
        GIFType.LOCALFILE
            Indicates that you want to play a GIF from a local file
    filename : str | GIFData | list
        The filename, folder or URL to play, or if you're sending data URI, extra data about the GIF

        If filename is a list, and GIFType is GIFType.LOCALFILE, each file will be sent with a
        different ID. The first ID will loop a few times, then the next file will play, and so on
        until the final GIF, where it'll loop indefinitely. 

        If using a type that uses GIFData (i.e. DATA and LOCALFILE), the available options are:

        GIFData.data : str
            The base64 encoded string that represents the GIF
        GIFData.size : int
            The size of the GIF. Can be 16, 32, 64. Defaults to 64
        GIFData.offset : int
            The frame offset. So if you want to start on frame 4, set this to 4. Defaults to 0
        GIFData.id : int
            A unique ID for the GIF. So if you send a new GIF, you need to give it a different ID.
            TODO: See what happens if you don't, or what happens if you give it a random number
        GIFData.speed : int
            How fast to play this particular frame. Just like animated GIFs, some frames can play
            longer than other frames. You can use `img.info["duration"]` to get the duration of a frame
        GIFData.totalFrames : int
            The amount of frames you have in your GIF. If set to 1, each frame will play as it arrives, and won't loop

    Returns
    -------
    bool
        Returns True to indicate that the frame(s) were sent without issue
    Exception
        Returns an exception if the API or the request returned an error
    """

    match type:
        case GIFType.DATA.value:
            return sendCommand(command="Draw/SendHttpGif", parameters={
                "PicNum": filename.totalFrames,
                "PicWidth": filename.size,
                "PicOffset": filename.offset,
                "PicID": filename.id,
                "PicSpeed": filename.speed,
                "PicData": filename.data
            })

        case GIFType.LOCALFILE.value | GIFType.URLDATA.value:

            # Reset the GIF IDs so we can just send an ID of 1 and it'll work.
            resetGIFID()

            # If we've just given a filename, instead of a list of filenames,
            # wrap it in a list.
            if isinstance(filename, str):
                filename = [filename]

            # Loop through all the files that have been passed in
            for file in range(0, len(filename)):
                # Convert each file into a set of Pixoo compatible frames
                # Also check if we're calling a URL.
                frames = _fileToFrames(
                    filename=filename[file], id=file, url=(type == GIFType.URLDATA.value))

                # Loop through all the framedata we received back from the conversaion
                for frame in range(0, len(frames)):
                    # Send each frame
                    sendGIF(type=GIFType.DATA.value,
                            filename=frames[frame])

        case GIFType.SDFILE.value | GIFType.SDFOLDER.value | GIFType.URL.value:
            sendCommand(command="Device/PlayTFGif", parameters={
                "FileName": filename,
                "FileType": type
            })

    return True


def getGIFID():
    """
    Get the GIF ID

    Gets the ID of the GIF currently playing. When sending a GIF to the device using sendGIF(), it requires a unique ID,
    and if you try and send another GIF with the same ID, it won't do anything. This lets you work out the ID
    of the last GIF you sent so you can increment it by 1. Alternatively, you can reset the ID every time, unless you want
    to run a slideshow of GIFs

    TODO: Need to work out if sending a GIF with the same ID (without resetting) will overwrite or ignore

    Parameters
    ----------


    Returns
    -------
    int
        Returns the ID of the last GIF you sent
    Exception
        Returns an exception if the API or the request returned an error
    """
    try:
        id = sendCommand(command="Draw/GetHttpGifId")
    except Exception as e:
        raise e

    return id


def resetGIFID():
    """
    Reset the GIF ID

    Resets the device's GIF ID. When you send base64 data to the device, you need
    to send a sequential ID (PicId). In theory this could let you overwrite frames 
    mid-animation, but in practice I don't think you can. Sometimes you need to 
    reset this counter (see https://github.com/SomethingWithComputers/pixoo#after-updating-the-screen---300-times-the-display-stops-responding)
    but in this library we just do it every time we send a GIF, at least until I work out how this thing works. 

    Parameters
    ----------


    Returns
    -------
    int
        Returns 0 so you know which ID you can start from. 
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendCommand(command="Draw/ResetHttpGifId")
    except Exception as e:
        raise e

    return 0


def drawText(options: List[TextOptions]):
    """
    Send text to the device

    Sends text to the device. 

    Parameters
    ----------

    text : str, optional
        The text to display if using TextType.URL or TextType.TEXT

    options : List[TextOptions]
        A list of text options. TextOptions consists of:

        id : int
            A unique ID for this bit of text. Can be used to update the text later
        x : int
            The text's X position
        y : int
            The text's Y position
        direction : TextDirection
            The direction to draw the text. Can be one of:

            TextDirection.LEFT
                Draws the text from left to right
            TextDirection.RIGHT
                Draws the text from right to left
        font : int
            Which font to use. TODO: Get this font stuff sorted out
        width : int
            The width of the textbox. If the text is longer than the textbox, it'll scroll
        text : str
            The text to send, if using TextType.TEXT. If using TextType.URL, the text from the URL will be displayed
        colour : str | Colour
            What colour to make the text. Can be a Colour named tuple, or a hex string (e.g. FFFFFF)
        update : int
            How often to update the text, in seconds (NOT milliseconds!)
        align : TextAlignment
            How to align the text. Can be one of:

            TextAlignment.LEFT
                Left align the text
            TextAlignment.RIGHT
                Right align the text
            TextAlignment.CENTER
                Center align the text
        type : TextType | int
            You can send pre-written text to the display, such as 
            the current time, or the weather, or you can tell it to 
            retrieve the text from a URL.

            Possible values are:

            TextType.SECOND
                Seconds
            TextType.MINUTE 
                Minutes
            TextType.HOUR 
                Hours
            TextType.AMPM 
                AM / PM text
            TextType.HOURMINUTE 
                Hours and minutes (e.g. H:M)
            TextType.HOURMINUTESECOND 
                Hour, minutes and seconds (e.g. H:M:S)
            TextType.YEAR 
                Year
            TextType.DAY 
                Day number
            TextType.MONTHNUMBER 
                Month number (e.g. January = 1)
            TextType.MONTHNUMBERYEAR 
                Month and year, separated by a middle dot (e.g. 1·2023)
            TextType.MONTHNUMBERDAY 
                Month and day, separated by a dot (e.g. 1·31)
            TextType.DATEMONTHYEAR 
                Date, month and year, separated by a dog (e.g. 5·MAR·2023)
            TextType.WEEKDAY2LETTER 
                Weekday, two letters (e.g. MO, TU)
            TextType.WEEKDAYSHORT 
                Weekday, short (e.g. MON, TUE, WED)
            TextType.WEEKDAY 
                Weekday, long format (e.g. MONDAY)
            TextType.MONTH 
                Month, short name (e.g. JAN)
            TextType.TEMPERATURE 
                The temperature (e.g. 23c)
            TextType.MAXTEMPERATURE 
                The maximum temperature
            TextType.MINTEMPERATURE 
                The minimum temperature
            TextType.WEATHER 
                The weather conditions, as text (e.g. Sunny)
            TextType.NOISELEVEL 
                The noise level. I think the noise level needs to be activated first (?)
            TextType.TEXT 
                Custom text. This is the default type
            TextType.URLTEXT 
                Pass it a URL and it'll display the contents.     

    Returns
    -------
    list
        Returns a list of text IDs (e.g. [1, 2, 3] if you send 3 bits of text)
    Exception
        Returns an exception if the API or the request returned an error
    """

    if not isinstance(options, List):
        options = [options]

    textPackets = []
    print(options)
    for option in options:
        print(option)
        # option = defaultdict(lambda:None, option)
        textPackets.append({
            "TextId": option["id"],
            "type": option["type"] or TextType.TEXT.value,
            "x": option["x"],
            "y": option["y"],
            "dir": option["direction"] or TextDirection.LEFT.value,
            "font": option["font"] or 2,
            "TextWidth": option["width"],
            "TextString": option["text"],
            "Textheight": 16,
            "speed": 10,
            "align": option["align"] or TextAlignment.LEFT.value,
            "color": option["colour"]
        })

    try:
        sendCommand(command="Draw/SendHttpItemList",
                            parameters={"ItemList": textPackets})
    except Exception as e:
        raise e

    return [option["id"] for option in options]


def divoomLogin(email: str, password: str, alreadyHashed: bool = False):
    """
    Login to the Divoom API

    The Pixoo uses two APIs, the local one, and one offered through appin.divoom-gz.com. This method
    logs in to the Divoom website. You can only log in using a regular account, and not an account
    created using Facebook or Twitter.

    Parameters
    ----------
    email : str
        The email address you signed up with
    password : str
        Your password. Will be MD5 hashed before sending
    alreadyHashed : bool
        If true, then your password will NOT be MD5 hashed before sending, as it assumes
        that you've already hashed it prior to calling this method. 

    Returns
    -------
    User | dict
        Returns a dict which has your Token and your UserId in it
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        # Hash our password if it wasn't supplied to us as a hash already
        if not alreadyHashed:
            password = hashlib.md5(bytes(password, "utf-8")).hexdigest()

        response = sendOnlineCommand(command="UserLogin", parameters={
            "Email": email,
            "Password": password
        })

        global user

        user = DivoomUser(Token=response["Token"], UserId=response["UserId"])

        return user

    except Exception as e:
        raise e


def divoomLogout(userID: int, token: int):
    """
    Logout of the Divoom API

    Logs out of the Divoom API

    Parameters
    ----------
    userID : int
        The user ID to log out
    token : int
        The login token you retrieved via divoomLogin

    Returns
    -------
    bool
        Returns True on success
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        sendOnlineCommand(command="UserLogout")

        user = None

        return True

    except Exception as e:
        raise e


def getAlarms():
    """
    Get alarms

    Gets a list of alarms from the device. 
    Requires you to have logged in to Divoom API using divoomLogin()

    Parameters
    ----------

    Returns
    -------
    list[Alarm]
        Returns a list of alarms
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        response = sendOnlineCommand(command="Alarm/Get")
        alarms = []
        for alarm in response["AlarmList"]:
            alarms.append({
                "AlarmId": alarm["AlarmId"],
                "AlarmName": alarm["AlarmName"],
                "AlarmTime": alarm["AlarmTime"],
                "DeviceId": alarm["DeviceId"],
                "EnableFlag": alarm["EnableFlag"],
                "ImageFileId": alarm["ImageFileId"],
                "RepeatArray": alarm["RepeatArray"]
            })

        alarms = alarms

        return alarms

    except Exception as e:
        raise e


def setAlarm(time: datetime.time | datetime.timedelta | int | Timer, repeatDays=[0, 0, 0, 0, 0, 0, 0], enabled: bool = True, name="Alarm"):
    """
    Set alarm

    Sets an alarm

    Parameters
    ----------
    name : str, optional
        The name of the alarm. Defaults to "Alarm" if not specified
    time : datetime.time | datetime.datetime | datetime.timedelta | int | Timer
        The time for the alarm. Can be a datetime.time, a timedelta, an 
        integer (Unix timestamp), or a Timer (minutes & seconds)
    repeatDays : list
        A list of booleans or ints of days to repeat. 
        For example, [1, 0, 0, 0, 0, 0, 0] = Repeat every Monday
    enabled : bool
        Whether or not this alarm is enabled. 

    Returns
    -------
    int
        Returns the ID of the newly created alarm
    Exception
        Returns an exception if the API or the request returned an error
    """
    try:

        # If it's an integer, assume it's a timestamp and return that
        if isinstance(time, int):
            timeObject = time
        # If it's a Timer NamedTuple, make it into a timedelta, then into a datetime, then timestamp
        elif isinstance(time, Timer):
            timeObject = floor((datetime.datetime.now(
            ) + datetime.timedelta(minutes=time.minutes, seconds=time.seconds)).timestamp())
        # If it's a datetime, get the timestamp
        elif isinstance(time, datetime.datetime):
            timeObject = floor(time.timestamp())
        # If this is a time, make up a date, combine it with the time, then get the timestamp
        elif isinstance(time, datetime.time):
            timeObject = floor(datetime.datetime.combine(
                datetime.datetime.now(), time).timestamp())
        # If it's a timedelta, add it to datetime.now(), then get the timestamp
        elif isinstance(time, datetime.timedelta):
            timeObject = floor(
                (datetime.datetime.now() + time).timestamp())

        alarm = {
            "AlarmId": name,
            "AlarmName": name,
            "DeviceId": device["DeviceId"],
            "EnableFlag": int(enabled),
            "AlarmTime": timeObject,
            "ImageFileId": "",
            "RepeatArray": repeatDays
        }

        response = sendOnlineCommand(
            command="Alarm/Set", parameters=alarm)

        return response["AlarmId"]

    except Exception as e:
        raise e


def deleteAlarm(id: int | str):
    """
    Delete Alarm

    Deletes an alarm, given it's ID

    Parameters
    ----------
    id : int | str
        The ID of the alarm to delete. If id is "all", 
        then ALL the alarms are deleted.

    Returns
    -------
    int
        Returns the list of alarms left
    Exception
        Returns an exception if the API or the request returned an error
    """

    try:
        if id == "all":
            response = sendOnlineCommand(command="Alarm/DelAll")
        else:
            response = sendOnlineCommand(command="Alarm/Del", parameters={
                "AlarmId": id
            })

        return response

    except Exception as e:
        raise e

def loadScreenFromFile(file: str):
    """
    Display a screen using a JSON file

    Display a custom screen using a JSON file. This is a convenient
    way of playing a GIF and drawing text over the top instead of having 
    to call everything separately. Kind of like a custom clock

    Parameters
    ----------

    file : str
        The JSON file you wish to load. See examples/screen.json for details

    Returns
    -------

    bool
        Returns True for now
    Exception
        Returns an exception if the API or the request returned an error

    """

    with open(file) as json_file:
        data = json.load(json_file)

        try:
            # First, send the GIF
            sendGIF(type=data["type"], filename=data["image"])

            # Then send the text
            drawText(data["text"])        

        except Exception as e:
            raise e 

def getNightMode():
    """
    Gets the Night Mode Schedule

    Gets the night mode schedule. This is when the screen
    will dim or brighten

    Parameters
    ----------

    Returns
    -------

    dict
        Returns a dictionary with a few properties:

        start : datetime.time
            The time the night mode will start
        end : datetime.time
            The time that the night mode will end
        state : bool
            Whether the night mode is on or off
        brightness : int 
            The brightness of the screen during night mode

    """

    try:

        response = sendOnlineCommand(command="Channel/GetNightView")

        startTime = response["StartTime"]
        endTime = response["EndTime"]

        startTimeParts = divmod(startTime, 60)
        endTimeParts = divmod(endTime, 60)

        return {
            "start": datetime.time(startTimeParts[0], startTimeParts[1], 0),
            "end": datetime.time(endTimeParts[0], endTimeParts[1], 0),
            "state": bool(response["OnOff"]),
            "brightness": int(response["Brightness"])
        }

    except Exception as e:
        raise e


def setNightMode(state: bool | int, start: int | datetime.time | None, end: int | datetime.time | None, brightness: int = 50):
    """
    Sets Night Mode

    Sets night mode, which dims the display during certain hours

    Parameters
    ----------

    state : bool | int
        Whether night mode is enabled or not
    start : int | datetime.time | None
        What time to start night mode. If it's an int,
        then it's the number of minutes since midnight. For
        example, to start at 11pm, you'd enter 1380.
        If start is None, then state is set to False
    end : int | datetime.time | None
        Similar to start, what time to end night mode.
    brightness : int, optional
        What brightness to set the screen to during night mode. Defaults to 50%

    Returns
    -------

    bool
        Returns True for now.
        TODO: Make this return the schedule

    """

    try:

        if isinstance(start, int) and start > 1440:
            raise Exception("Start time is greater than 1440 minutes!")
        elif isinstance(end, int) and end > 1440:
            raise Exception("End time is greater than 1440 minutes!")        

        if(start == end):
            state = False

        if isinstance(start, datetime.time):
            startTime = (start.hour * 60) + start.minute
        
        if isinstance(end, datetime.time):
            endTime = (end.hour * 60) + end.minute 

        sendOnlineCommand(command="Channel/SetNightView", parameters={
            "StartTime": startTime,
            "EndTime": endTime,
            "OnOff": int(state),
            "Brightness": brightness
        })

        return {
            "start": startTime,
            "end": endTime,
            "state": int(state),
            "brightness": brightness
        }

    except Exception as e:
        raise e

# from pixoo64api import pixoo; pixoo.sendGIF(ipAddress="192.168.1.92", type=pixoo.GIFType.LOCALFILE.value, filename="e:\\downloads\\Frankenstein_icon.gif"); exit()
