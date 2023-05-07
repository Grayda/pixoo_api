from requests import request
from typing import List
from urllib.parse import urlparse  # For validating URLs
from PIL import Image, ImageOps
import datetime
import base64
import hashlib
from io import BytesIO
import math 
import json
from Crypto.Cipher import AES
from struct import unpack # For reading multiple bytes, and unpacking them into variables
import lzo

# Import our enums and such so that you can easily use them in the same class
from pixooapi.types import *

# The device that we're communicating with.
device: dict | DivoomDevice = None

# Your user details, if logging in to the Divoom API (instead of the local one)
user: dict | DivoomUser = None

# A list of alarms set on the device
alarms: list[Alarm] = []

# If true, no calls are actually made, but are printed instead.
debug = False


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
        raise Exception("No devices found!")

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

    return isinstance(device, DivoomDevice)


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

    return isinstance(user, DivoomUser)


def sendOnlineCommand(command: str, parameters={}, requireLogin=True, requireDevice=True):
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

    data = {}

    if requireLogin:
        if not _isLoggedIn():
            raise Exception("Command requies you to be logged in")
        else:
            data.update({
                "DeviceId": device["DeviceId"],
                "Token": user["Token"],
                "UserId": user["UserId"]
            })
    if requireDevice:
        if not _checkForDevice():
            raise Exception("Command requies a device to be set")
        else:
            data.update({
                "Token": user["Token"],
                "UserId": user["UserId"]
            })

    # Then tack on any parameters (which are a dictionary)
    data.update(parameters)

    # Just call the API
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
        if debug:
            print("Sending data to {url}: {data}".format(url=url, data=data))
        else:
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
        response = sendOnlineCommand(command="Device/ReturnSameLANDevice", requireDevice=False, requireLogin=False)
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
        sendCommand(command="Sys/TimeZone",
                    parameters={"TimeZoneValue": timezone})
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

        sendCommand(command="Device/SetUTC", parameters={"Utc": time})
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
        sendCommand(command="Device/SetTime24Flag", parameters={"Mode": mode})
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
        sendOnlineCommand(command="Sys/SetConf",
                          parameters={"HighLight": enabled}, requireDevice=True, requireLogin=True)
    except Exception as e:
        raise e

    return enabled


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
        sendOnlineCommand(command="Sys/SetConf",
                          parameters={"DateFormat": format}, requireDevice=True, requireLogin=True)
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
        sendCommand(command="Device/SetScreenRotationAngle",
                    parameters={"Mode": angle})
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
        sendCommand(command="Device/SetMirrorMode",
                    parameters={"Mode": int(mirrored)})
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
                          parameters={"BlueScore": blueScore, "RedScore": redScore}, requireDevice=True, requireLogin=True)
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
                            parameters={"NoiseStatus": int(enabled)})
    except Exception as e:
        raise e

    return enabled


def _fileToFrames(filename: str, url=False, id=0, resample: Image.Resampling | int = Image.Resampling.BICUBIC.value, size=64, maxFrames=60):
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
    for option in options:
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
        }, requireDevice=False, requireLogin=False)

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
        sendOnlineCommand(command="UserLogout", requireDevice=False, requireLogin=True)

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
        response = sendOnlineCommand(command="Alarm/Get", requireDevice=True, requireLogin=True)
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
            timeObject = math.floor((datetime.datetime.now(
            ) + datetime.timedelta(minutes=time.minutes, seconds=time.seconds)).timestamp())
        # If it's a datetime, get the timestamp
        elif isinstance(time, datetime.datetime):
            timeObject = math.floor(time.timestamp())
        # If this is a time, make up a date, combine it with the time, then get the timestamp
        elif isinstance(time, datetime.time):
            timeObject = math.floor(datetime.datetime.combine(
                datetime.datetime.now(), time).timestamp())
        # If it's a timedelta, add it to datetime.now(), then get the timestamp
        elif isinstance(time, datetime.timedelta):
            timeObject = math.floor(
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
            command="Alarm/Set", parameters=alarm, requireDevice=True, requireLogin=True)

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
            response = sendOnlineCommand(command="Alarm/DelAll", requireDevice=True, requireLogin=True)
        else:
            response = sendOnlineCommand(command="Alarm/Del", parameters={
                "AlarmId": id
            }, requireDevice=True, requireLogin=True)

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
    Exception
        Returns an exception if the API or the request returned an error
    
    """

    try:

        response = sendOnlineCommand(command="Channel/GetNightView", requireDevice=True, requireLogin=True)

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
        What brightness to set the screen to during night mode. Defaults to 50

    Returns
    -------

    dict
        Returns the night mode schedule as a dictionary

        Has the fields:
            start : datetime.time
                When the schedule will start, as a Python datetime.time
            end : datetime.time
                When the schedule will end, as a Python datetime.time
            state : bool
                If the schedule is active or not.
            brightness : int
                The brightness, expressed as an integer between 1 and 100
    Exception
        Returns an exception if the API or the request returned an error

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
        }, requireDevice=True, requireLogin=True)

        return getNightMode()

    except Exception as e:
        raise e

def getUserImages(userId: int, results = 2000):
    """
    Get a user's images

    Gets a list of a user's images

    Parameters
    ----------

    userId : int
        The ID of the user. 
    results : int, optional
        The number of results to return. Defaults to 2000

    Returns
    -------

    list[dict]
        A list that contains dictionaries with image info. Each dict will contain:

        FileId : str
            The ID of the file. You can download it by going to f.divoom-gz.com/<FileId>,
            or you can pass it to downloadOnlineGIF to make a GIF out of it. 
        FileName : str
            The name of the image
        Date : int
            The time the image was uploaded as a Unix timestamp
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        results = sendOnlineCommand("GetSomeoneListV2", {
            "SomeOneUserId": userId,
            "StartNum": 1,
            "EndNum": 2000,
        }, requireDevice=False, requireLogin=False)

        return {key: results["FileList"][key] for key in ("FileName", "FileId")}

    except Exception as e:
        raise e
    

def downloadOnlineGIF(fileId: str, outFile = None):
    """
    Create a GIF from a Divoom file URL

    Retrieves data about a Divoom file and creates a file out of it. This can
    only be done on public images, and not private images.

    Parameters
    ----------

    fileId : str
        The file ID of the image. For example, this Among Us image: group1/M00/0F/65/eEwpPWKMBumEPHcwAAAAAPueyb01234421
    outFile : str | None
        Where to save this image on disk. If not specified, will attempt to use the filename from Divoom, otherwise will default to image.gif

    Returns
    -------

    str
        Returns the full path to the file
    Exception
        Returns an exception if the API or the request returned an error

    """

    try:
        # Call the Pixoo API to get the file
        data = sendOnlineCommand("Cloud/GetFileData", { "FileId": fileId }, requireDevice=False, requireLogin=False)

        # If there's no data, then the FileId is valid, but the image is private
        # or has had the flag set so nobody can edit / remix it.
        if len(data["FileData"]) == 0:
            raise Exception("No file data! Image may be set to private")
        
        if outFile == None:
            if data["FileName"]:
                outFile = data["FileName"]
            else:
                outFile = "image.gif"

        _imageDataToGIF(data, data["Filename"])

    except Exception as e:
        raise e

def _imageDataToGIF(data: dict, outFile = "image.gif"):
    """
    Convert image data to a GIF


    """

    try:
        # What will the size of the chunks be?
        # This is the length of the data, divided by the number of frames
        chunkSize = int((len(data["FileData"]) / int(data["PicCount"])))
        
        # This holds our constructed frames
        images = []

        # Work out the frame size. This is just the square root of our chunkSize
        # For example if a chunk has 4096 items in it, the square root of that is 64, so our size is 64x64
        frameSize = int(math.sqrt(chunkSize / 3))

        # Now we split the data into lists of chunkSize
        chunkData =  [data["FileData"][i:i + chunkSize] for i in range(0, len(data["FileData"]), chunkSize)]

        # Loop through all the chunks
        for chunk in chunkData:
            # This holds the RGB into as tuples
            pixelData = []

            # Split the chunk into groups of three (R, G and B)
            pixelChunks =  [chunk[i:i + 3] for i in range(0, len(chunk) - 1, 3)]

            # Then loop though all the RGB values..
            for pc in pixelChunks:
                # ..and make a tuple out of each third
                pixelData.append((pc[0], pc[1], pc[2]))

            # Make a new image and put the pixel data in there.
            img = Image.new("RGB", (frameSize, frameSize))
            
            img.putdata(pixelData)

            # Add this newly created image to our list of images
            images.append(img)

        # And now use the first frame to save all of the subsequent frames as a GIF
        firstImage = images[0]
        firstImage.save(outFile, format="GIF", append_images=images,
               save_all=True, duration=data["Speed"], loop=0)

    except Exception as e:
        raise e


def _binFileToGIF(file: str, key: str, iv: str, outFile: str):
    """
    Decrypt and make a GIF out of a Divoom file

    Retrieves data about a Divoom file and creates a file out of it. This can
    only be done on public images, and not private images.

    Parameters
    ----------

    file : str
        The path to a file.
    key : str
        The decryption key. Can be extracted from the decompiled Divoom APK in sources/com/divoom/Divoom/utils/cloudData/C4707a.java
    iv : str
        The initialisation vector, also extracted from the decompiled Divoom APK
    outFile : str
        Where to save this image on disk. If not specified, will attempt to use the filename from Divoom, otherwise will default to image.gif

    Returns
    -------

    str
        Returns the full path to the created GIF
    ValueError
        Returns a ValueError if there was a decryption error
    Exception
        Returns an exception if the API or the request returned an error
    
    """
    
    try:
        with open(file=file, mode="rb") as f:

            fileData = {
                "Width": 0,
                "Height": 0,
                "PicCount": 0,
                "Speed": 0,
                "FileData": []
            }

            # Set up a decryption cipher with our key an IV in CBC mode
            decrypt_cipher = AES.new(key, AES.MODE_CBC, IV=iv)

            # Read the whole file
            # Get the first byte. This'll be the type of file
            match f.read(1).hex():
                # 16x16 static image.
                # Data is AES CBC encrypted and starts at byte 2
                case "08":
                    fileData["Width"] = 16
                    fileData["Height"] = 16
                    fileData["PicCount"] = 1
                    fileData["Speed"] = 1
                    fileData["FileData"] = decrypt_cipher.decrypt(f.read())
                # 16x16 animated image. Number of frames is byte 2,
                # Speed is bytes 3 and 4, and the AES encrypted data starts at byte 6
                case "09":
                    fileData["Width"] = 16
                    fileData["Height"] = 16
                    # Get the number of frames in the file
                    fileData["PicCount"] = int(f.read(1).hex(), 16)
                    # Speed is the next two bytes, and is calculated like this:
                    # (byte 3, bitwise and'd with 255), bitwised or with (byte 2, shifted left by 8 bytes)
                    speed = f.read(2)
                    fileData["Speed"] = (speed[1] & 255) | (speed[0] << 8)
                    # And the rest of the data is AES CBC data
                    fileData["FileData"] = decrypt_cipher.decrypt(f.read())
                # Static image, 32x32 or 64x64.
                # Size is byte 2 * 16, multiplied by byte 3 * 16
                # Data starts at byte 4 and is AES CBC encrypted.
                # The resulting data is LZO compressed (with a length of width * height * 3)
                case "11":
                    # Static image
                    # Read six bytes, and unpack them into integers.
                    width, height, dataLength = unpack(">BBI", f.read(6))
                    fileData["Width"] = width * 16
                    fileData["Height"] = height * 16
                    fileData["PicCount"] = 1
                    data = fileData["FileData"] = decrypt_cipher.decrypt(f.read())
                    fileData["FileData"] = lzo.decompress(data, False, (width * 16) * (height * 16) * 3)
                # ??
                case "1E":
                    # TODO: find a file that has this type. 
                    # I think you can just loop over the whole file (except the first byte?), and just bitwise and each byte by 255?
                    pass
                case "0C":
                    # TODO: find a file that has this type
                    # This file has some kind of scroll mode. Byte 1 is what sort of scroll mode it is. I don't know scrolling means here.
                    # When you call Cloud/GetFileData, it can return an xScreenCount and yScreenCount, so perhaps that has something
                    # to do with it? Or, perhaps it's some kind of clock face file that has user defineable 
                    pass
                # Static 128x128?
                case "1a":
                    raise Exception("Filetype not yet supported")
                    # Get the number of frames in the file
                    fileData["PicCount"] = 1
                    fileData["Speed"] = 1
                    fileData["FileData"] = f.read()
                # Font file?
                case "00":
                    raise Exception("Filetype not yet supported")
                    fileData["PicCount"] = int(f.read(1).hex(), 16)
                    fileData["Speed"] = 1
                    fileData["FileData"] = f.read()
                # Other file types, as per the Pixoo APK
                case "1E" | "0C" | "12" | "OD" | "13" | "07" | "0F" | "16" | "17" | "11" | "00" | "1A": 
                    # Note: 0F seems to match with a 16x16 file
                    # Some types also take a string in the decompiled APK. Allows for text to be parsed, like a clock?
                    raise Exception("Filetype not yet supported")
                case _:
                    raise Exception("Unknown File Type")
            
            # And then save it as a GIF
            _imageDataToGIF(fileData, outFile)
                
    except ValueError as e:
        raise e
    except Exception as e:
        raise e