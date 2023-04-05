import datetime 
from typing import NamedTuple
from enum import Enum

# The channels you can switch the device to.
class Channels(Enum):
    CLOCK = 0 # Shows a clockface
    CLOUD = 1 # Shows animations from the cloud
    VISUALIZER = 2 # Shows an audio visualizer
    CUSTOM = 3 # Shows a custom collection of animations you pick from the app
    BLANK = 4 # Shows a blank screen. I think this turns the screen completely off

# How to display the temperature, Celsius or Fahrenheit
class TemperatureMode(Enum):
    CELSIUS = 0
    FAHRENHEIT = 1

class TimeMode(Enum):
    TIME12HOUR = 0
    TIME24HOUR = 1

# Screen rotation
class Rotation(Enum):
    ROTATE0 = 0 # Not rotated
    ROTATE90 = 1 # Rotated right
    ROTATE180 = 2 # Upside down
    ROTATE270 = 3 # Rotated left

# The state of the screen
class Screen(Enum):
    OFF = 0
    ON = 1

# Timer for the countdown
class Timer(NamedTuple):
    minutes: int
    seconds: int

# For setting white balance, drawing elements, etc.
class Colour(NamedTuple):
    red: int
    green: int
    blue: int

# The date format. 
# Formats ending in "HYPHEN" are separated by dashes
# e.g. YYYY-MM-DD, while "PERIOD" are seperated by
# periods, e.g. YYYY.MM.DD
class DateFormat(Enum):
    YYYYMMDDHYPHEN: 0
    DDMMYYYYHYPHEN: 1
    MMDDYYYYHYPHEN: 2
    YYYYMMDDPERIOD: 3
    DDMMYYYYPERIOD: 4
    MMDDYYYYPERIOD: 5

# When on the cloud channel, what category of images to show
class CloudChannelCategory(Enum):
    RECOMMENDED = 0 # Shows a Divoom curated list of animations
    FAVOURITE = 1 # Shows images you've favourited
    SUBSCRIBED = 2 # Shows artists that you've subscribed to
    ALBUM = 3 # Shows a specific category (e.g. Christmas)

# A generic status, used for Countdown and noise meter
class Status(Enum):
    STOP = 0
    START = 1
    RESET = 2        

# What type of GIF to play
class GIFType(Enum):
    SDFILE = 0 # Play a specific GIF from the SD card
    SDFOLDER = 1 # Plays a folder of GIFs from the SD card
    URL = 2 # Loads the GIF via a URL
    DATA = 3 # Plays a base64 encoded animation that you send it
    LOCALFILE = 4 # Same as GIFType.DATA, but used by this library to signify that the GIF will be loaded from your computer
    URLDATA = 5 # Same as GIFType.LOCALFILE, but instead retrieves the GIF from a URL. Used so you can draw over the top of it

# How to align the text when drawing it to the screen
class TextAlignment(Enum):
    LEFT = 1
    CENTER = 2
    RIGHT = 3

# Information about the GIF frame you're sending to the screen
class GIFData(NamedTuple):
    size: int # The size of the GIF. Can be 16, 32 or 64
    offset: int # What frame of the animation this is
    id: int # You can send more than animation to the device, this ID lets you tell them apart
    speed: int # The duration of this frame, in milliseconds
    totalFrames: int # How many total frames there are
    data: str # The base64 encoded data

# The direction of the text (e.g. LTR or RTL)
class TextDirection(Enum):
    LEFT = 0
    RIGHT = 0

# Dynamic text you can draw to the screen
class TextType(Enum):
    SECOND = 1  # Seconds
    MINUTE = 2  # Minutes
    HOUR = 3  # Hours
    AMPM = 4  # AM / PM text
    HOURMINUTE = 5  # Hours and minutes (e.g. H:M)
    HOURMINUTESECOND = 6  # Hour, minutes and seconds (e.g. H:M:S)
    YEAR = 7  # Year
    DAY = 8  # Day number
    MONTHNUMBER = 9  # Month number (e.g. January = 1)
    MONTHNUMBERYEAR = 10 # Month and year, separated by a middle dot (e.g. 1·2023)
    MONTHNUMBERDAY = 11  # Month and day, separated by a dot (e.g. 1·31)
    DATEMONTHYEAR = 12 # Date, month and year, separated by a dot (e.g. 5·MAR·2023)
    WEEKDAY2LETTER = 13  # Weekday, two letters (e.g. MO, TU)
    WEEKDAYSHORT = 14  # Weekday, short (e.g. MON, TUE, WED)
    WEEKDAY = 15  # Weekday, long format (e.g. MONDAY)
    MONTH = 16  # Month, short name (e.g. JAN)
    TEMPERATURE = 17  # The temperature (e.g. 23c)
    MAXTEMPERATURE = 18  # The maximum temperature
    MINTEMPERATURE = 19  # The minimum temperature
    WEATHER = 20  # The weather conditions, as text (e.g. Sunny)
    NOISELEVEL = 21 # The noise level. I think the noise level needs to be activated first (?)
    TEXT = 22  # Custom text
    URL = 23  # Pass it a URL and it'll display the contents.

# Options you can use when drawing text to the screen
class TextOptions(NamedTuple):
    id: int # You can send more than one lot of text to the screen, and can update them individually with this ID
    x: int # The X position to display the text
    y: int # The Y position to display the text
    direction: TextDirection # What direction (e.g. LTR or RTL) to display the text
    font: int  # Which font to use. See fontlist.py for more information
    width: int # The width of the whole textbox
    # size: int # The font size. Not sure how this works with fonts: TODO: Test this
    text: str # If you're sending custom text or a URL, you can specify it here
    # speed: int # How fast to scroll the text
    colour: str | Colour # What colour to make the text
    update: int # How often to update the text
    align: TextAlignment # How to align the text
    type: TextType | int # The type of text to send

# Represents a Pixoo device
class DivoomDevice(dict):
    DeviceName: str # The name of your Pixoo device
    DeviceId: str | int # The ID of your device
    DevicePrivateIP: str # The local IP address of your device
    DeviceMac: str # The MAC address of your device

class DivoomUser(dict):
    Token: int # A timestamp showing when you logged in. This must be sent with all online API calls
    UserId: int # Your Divoom user account number. Also used with Divoom online API calls

# An individual plan item (e.g. in the plan called "Daily", an item called "Wake Up" or "Do Dishes")
class PlanItem(NamedTuple):
    clockFileID: str
    clockID: int
    clockName: str 
    repeat: list[dict] # [{'Week': 0}, {'Week': 0}, {'Week': 0}, {'Week': 0}, {'Week': 0}, {'Week': 0}, {'Week': 0}], 
    endTime: int
    fileID: int
    name: str 
    playMode: int
    startTime: int 
    type: int
    playSound: bool

class Plan(NamedTuple):
    lastUpdated: datetime.datetime | int
    id: int
    name: str
    enabled: bool | int
    items: list[PlanItem]

# For setting / getting alarms
class Alarm(dict):
    id: int
    name: str
    time: datetime.time | int 
    deviceId: int 
    enabled: bool | int
    imageFileId: str 
    repeat: list[int]