# Notes about the Divoom Pixoo 64

This document contains various notes about the Divoom Pixoo. As I find out more about the Pixoo 64 I'll update this 

## Logging in to the Divoom API

The Pixoo can use two different APIs, a local one, which is viewable here: `http://doc.divoom-gz.com/web/#/12`, and the other, which is undocumented, and is used by the app, using `https://appin.divoom-gz.com/`

You don't need to log in to the local API, but you do to access the remote API. The remote API has a ton more features, such as setting / retrieving alarms.

To log in to the Divoom API, you need to call `https://appin.divoom-gz.com/UserLogin` with the following parameters:

```json
{
   "Email":"divoom@example.com",
   "Password":"<your password, MD5 hashed>"
}
```

You'll get some JSON in response. You'll need to take note of `Token` and `UserId`, as these are used, along with `DeviceId` (obtained from the Pixoo using the `pixoo.findDevices()` method in this library), to do stuff like set / get alarms. `Token` is just a Unix timestamp, but is a way for Divoom to verify when you logged in

## Initial setup of device

I think the Pixoo 64 seems to connect via bluetooth to do the initial setup, as I don't think it exposed a hotspot to connect to like other devices? Haven't had time to check this out though

## Misc. Notes

- The app makes a lot of calls to `rongcfg.com` and `rongnav.com`. I think they're just logging / data collection stuff, so they might be worth blocking on your local network, in case it's phoning home a bunch of info?
- Divoom runs an MQTT server on appin.divoom-gz.com. You can connect without authentication, but it doesn't really do much. I can't get any data in or out of it.
  - I think there might also be an MQTT server on the Pixoo 64 itself? You can't connect to it, but it can connect to you somehow? 
  - Conversely, the device might connect to Divoom's MQTT server, so if you want a purely offline device (after geting it set up?) then you might need to do some DNS redirecting

## Sending images

Sending animations to the device is weird. There's a few caveats:

 - `Draw/CommandList` **can't** be used to batch-send frames. You need to make several `Draw/SendHttpGif` commands in succession. Unless you do the work on another thread, this will block your app for a bit, depending on how big your animation is (tested on animations up to 2mb in size)
 - There is a maximum of about 40 frames, so if your animation has more frames than this, your Pixoo may crash. This module limits the number of frames for you unless overwritten
 - If you send an animation, the `Loading..` animation will always play first, so it's kinda ugly if you want to use it as a notification display (e.g. if you want to show an animation for the doorbell, expect a 5+ second delay while your GIF is sent). Your best bet is to just display one frame (which is instant), or just use a GIF stored on the SD card, but just know that if you do that, you won't be able to draw your own text over the top. 
 - You can only draw text over the top of frames you've sent via `Draw/SendHttpGif`, so you can't just slap text over a GIF on the SD card, or a GIF from the gallery. There might be a way around this, but I haven't found it yet. 

### How to send images

To send animations to the device, do this:

- Load the image. Using Pillow makes it much easier
   - `img = Image.load("yourfile")`
- Work out how many frames it has
   - `frames = img.n_frames`
- Loop through each frame and then seek to each frame
   - `for frame in range(0, frames):`
   - `  img.seek(frame)`
- Convert the frame to RGB format
   - `img.convert("RGB")`
- Get the Red, Green and Blue values for every pixel. You can use `getdata()`, which returns a list of tuples:
   - `pixels = [item for p in list(imgrgb.getdata()) for item in p] # This flattens the tuples to a list`
   - The data will look like this: `[R, G, B, R, G, B, R, G, B, ...]` and will have `64*64*3` elements per frame on the Pixoo 64
- Convert the list of pixels to a bytearray, then base64 encode that bytearray
   - `b64 = base64.b64encode(bytearray(pixels))`
   - `frameData = b64.decode("utf-8")`
- [Send the data](http://doc.divoom-gz.com/web/#/12?page_id=93) with the `Draw/SendHttpGif` command
- Repeat for each frame

There are much easier ways to play a GIF (e.g. sending a URL that points to a GIF, or loading a GIF from the SD card), but you can't draw text over the top because of limitations that I can't seem to work around yet

## Divoom Image Files

You can download various images from the Divoom website if you know the file ID. For example, to download a font file, go to this website: `https://appin.divoom-gz.com/Device/GetTimeDialFont` and find the font you want to download. Then grab the ID (e.g. `group1/M00/D6/80/eEwpPWC4tX6EaCuWAAAAAE69aF8710.bin`) and then go to `https://f.divoom-gz.com/<file id>`. The file will be downloaded.

I don't know what file format Divoom uses, but here's some notes:

- The data in the file is not the same as the data you send to the device. 
  - The data you send to the device is a base64 encoded list of RGB values (e.g. `base64.encode([255, 255, 255, 0, 0, 0, 255, 255, 255 ...])` to send a checkerboard pattern)
  - But the files you download from Divoom aren't base64 encoded?
  - The font files have the string `UNICODE` inside them, but the images don't. In fact, a 32x32 solid red image is 21 bytes, while the font file is 2mb in size.
- The images may possibly be encrypted or encoded. See [this Reddit thread](https://www.reddit.com/r/AskReverseEngineering/comments/12ryahe/) for thoughts and processes
- The Divoom APK lets you record audio to include with an image. The audio file is stored separately and is just a regular MP3 file.
- The files are possibly big-endian? The third byte in 64x64 images

I've made extremely basic images for reverse engineering purposes, they can be found here: https://github.com/Grayda/pixoo64_example_images

- Animations seem to start with `1A`, followed by the number of frames in the animation. For example [this file](https://f.divoom-gz.com/group1/M00/07/C3/L1ghbmHcJUKESjyQAAAAAG2IqbA7174570), which is an animation of a character from Hotline Miami, has 20 frames of animation when you download the GIF to your computer.
- Images without animations seem to be handled differently:
  - My basic 64x64 and 32x32 images start with hex `11`. `11` is followed by `02` for 32x32, and `04` for 64x64. 16x16 images start with `08`. 128x128 images start with `1A`, like the animations do.
    - I suspect that between hardware revisions, Divoom updated the file format. In the APK, there's a few references to `PixelDecode64New`, `PixelDecodeSixteen`, `PixelEncode64`, `PixelEncodeSixteen` and `PixelEncodePlanet`. `PixelEncodeSixteen` is marked as deprecated in the source code, and I wonder if `PixelDecode64New` handles 32x32 and 64x64 images. ~~I don't know what `PixelEncodePlanet` does, however.~~ `PixelEncodePlanet` is for the [Divoom Planet 9](https://divoom-gz.com/product/planet.html)
- Durations set in Photoshop (or whatever GIF creation tool you're using) are discarded when they get uploaded to Divoom. Instead, a global duration (?) is stored in the file.

### Uploading files to the Divoom gallery

I think this is done using this endpoint: `Cloud/GalleryUploadV3` and a quick test suggests it contains this data:

```python
 data = {
   "Classify":1, # The category, perhaps?
   "Content":"Image Description Here", # Description
   "CopyrightFlag":1, # Used to prevent other users from remixing / downloading the file, I think?
   "DeviceId":300000000, # Your Pixoo's device ID 
   "FileMD5":"<file MD5 hash>", # THe MD5 hash of the file you're uploading
   "FileName":"Filename here", # The title of the file 
   "FileSize":4, # The size of the image. 1 = 16x16, 2 = 32x32, 4 = 64x64, 8 = 25x25 (possibly for the Planet 9?), 16 = 128x128
   "FileType":2, # Possibly an indicator of whether it's a static image or an animation?
   "HideFlag":0, # Hide this image from other users? Not sure what the difference between PrivateFlag and HideFlag is
   "IsAndroid":1, # Whether this was created on Android or not?
   "OriginalGalleryId":0, # What gallery ID this belongs to?
   "PacketFlag":0, # Not needed, but could be used to tell Divoom "this packet is related to the packet I sent before with the same ID"
   "PhotoFlag":0, # If the thing you're uploaded was digitized from your camera (?)
   "PrivateFlag":1, # If this should be a private upload (i.e. only visible to you)
   "Token":1681104111, # Retrieved when you called pixoo.divoomLogin(email="email@example.com", password="yourpasswordhere")
   "UserId":402694556, # Your user ID, retrieved from the same divoomLogin call as above
   "Version":12 # Dunno?
}`
```

TODO: Expand on this

## Fonts

Fonts on the Pixoo 64 are a bit all over the place, so here's some notes:

- There's a visual guide to the fonts here: http://dial.divoom-gz.com/dial.php/index.html
   - You'll need to sign in with a Divoom account. There's no way to sign in with Facebook or Twitter, so I suggest making a dummy using something like mailinator.com if you signed up with Facebook
- The list of fonts as JSON are available here: https://app.divoom-gz.com/Device/GetTimeDialFontList
- There's 115 total fonts at time of writing.
- Some fonts substitute characters with symbols. 
   - The character set for font `18` lists `u` and `d`, but typing those will display an up and down arrow instead. 
   - The character set for font `20` will replace `c` and `f` with `°C` and `°F` respectively
- Some fonts have drop shadows, backgrounds or outlines.
   - In the visual guide, these are indicated by a red background.
- Other fonts have a glow. The glow colour can't be changed -- they're more like bitmaps than fonts
- The list of fonts is all over the place.
  - Many fonts don't have a name, some don't list a character set, many don't have a preview.
  - The height / width listed for many fonts doesn't match sometimes
    - A font may be listed as 16 pixels wide, but no character is ever 16 pixels wide, and the whole bounding box is not 16 pixels wide
    - This makes writing a script that loops through all the available characters difficult
  - Some font / character combinations crash the Pixoo 64, so it may be near impossible to get a full list of fonts.

## Interesting commands

There's some interesting commands that I grabbed from the decompiled APK and a firmware file. The APK commands are for the Divoom Online API, though some of them might overlap with the local API:

In `com\divoom\Divoom\http\HttpCommand.java`:

```json
[
   "AddDownloads",
   "AddWatch",
   "Alarm/Change",
   "Alarm/Del",
   "Alarm/DelAll",
   "Alarm/Get",
   "Alarm/Set",
   "App/DelUser",
   "App/FirstOpen",
   "App/GetHttps",
   "App/GetOtherUserList",
   "App/SetIP",
   "Application/RealTimeInfo",
   "ApplyBuddy",
   "ChangPassword",
   "Channel/AddEqData",
   "Channel/AddHistory",
   "Channel/CleanCustom",
   "Channel/ClockCommentLike",
   "Channel/CustomChange",
   "Channel/DelHistory",
   "Channel/DeleteCustom",
   "Channel/DeleteEq",
   "Channel/EqDataChange",
   "Channel/GetAll",
   "Channel/GetAllCustomTime",
   "Channel/GetClockCommentList",
   "Channel/GetClockConfig",
   "Channel/GetClockInfo",
   "Channel/GetClockList",
   "Channel/GetConfig",
   "Channel/GetCurrent",
   "Channel/GetCustomList",
   "Channel/GetCustomPageIndex",
   "Channel/GetEqDataList",
   "Channel/GetEqPosition",
   "Channel/GetEqTime",
   "Channel/GetIndex",
   "Channel/GetNightView",
   "Channel/GetSongInfo",
   "Channel/GetStartupChannel",
   "Channel/GetSubscribe",
   "Channel/GetSubscribeTime",
   "Channel/ItemSearch",
   "Channel/LoginThird",
   "Channel/OnOffScreen",
   "Channel/ReportClockComment",
   "Channel/ResetClock",
   "Channel/SetAllCustomTime",
   "Channel/SetBrightness",
   "Channel/SetClockConfig",
   "Channel/SetClockSelectId",
   "Channel/SetConfig",
   "Channel/SetCurrent",
   "Channel/SetCustom",
   "Channel/SetCustomId",
   "Channel/SetCustomPageIndex",
   "Channel/SetEqPosition",
   "Channel/SetEqTime",
   "Channel/SetIndex",
   "Channel/SetNightView",
   "Channel/SetProduceTime",
   "Channel/SetStartupChannel",
   "Channel/SetSubscribe",
   "Channel/SetSubscribeTime",
   "CheckIdentifyCode",
   "Cloud/GalleryInfo",
   "Cloud/GalleryUpload11",
   "Cloud/GalleryUploadV3",
   "Cloud/GetExpertGallery",
   "Cloud/GetHotExpert",
   "Cloud/GetHotTag",
   "Cloud/GetLikeUserList",
   "Cloud/GetMatchInfo",
   "Cloud/GetSubscribeAndFollow",
   "Cloud/ReportUser",
   "Cloud/SetGalleryCopyright",
   "Cloud/SetGalleryPrivate",
   "Cloud/ToDevice",
   "Cloud/UploadLocal",
   "Cloud/WeakWatchGallery",
   "Comment/GetCommentListV3",
   "CommentLikeV2",
   "Community/DeleteComment",
   "Community/ReportComment",
   "ConfirmBuddy",
   "ConfirmGetNewLetterV2",
   "DeleteFile",
   "DeleteGalleryV2",
   "Device/AppRestartMqtt",
   "Device/BindUser",
   "Device/Connect",
   "Device/ConnectApp",
   "Device/DeleteResetAll",
   "Device/Disconnect",
   "Device/DisconnectMqtt",
   "Device/GetDeviceId",
   "Device/GetFileByApp",
   "Device/GetList",
   "Device/GetNewBind",
   "Device/GetUpdateFileList",
   "Device/GetUpdateInfo",
   "Device/Hearbeat",
   "Device/NotifyUpdate",
   "Device/ResetAll",
   "Device/SetLog",
   "Device/SetName",
   "Device/SetPlace",
   "Device/SetUTC",
   "Device/ShareDevice",
   "Device/TestNotify",
   "Device/Unbind",
   "Dialog/GetInfo",
   "Dialog/GetMatchInfo",
   "Discount/Delete",
   "Discount/GetMyList",
   "Discount/GetNewDiscount",
   "Discover/GetAlbumImageList",
   "Discover/GetAlbumImageListV2",
   "Discover/GetAlbumInfo",
   "Discover/GetAlbumList",
   "Discover/GetAlbumListV2",
   "Discover/GetRadioList",
   "Discover/GetStoreList",
   "Discover/GetTheme",
   "Discover/GetTopNew",
   "DiscoverBanner",
   "Draw/ExitSync",
   "Draw/GetPaletteColorList",
   "Draw/NeedEqData",
   "Draw/NeedLocalData",
   "Draw/NeedSendDraw",
   "Draw/SendLocal",
   "Draw/SendRemote",
   "Draw/SetInfo",
   "Draw/SetPaletteColor",
   "Draw/SetScroll",
   "Draw/SetSpeedMode",
   "Draw/UpLoadAndSend",
   "Draw/UpLoadEqAndSend",
   "EveryDayMission",
   "FillGame/FinishGameV2",
   "FindPassword",
   "FollowExpertV2",
   "Forum/CommentLike",
   "Forum/GetCommentListV2",
   "Forum/GetForumUrl",
   "Forum/GetList",
   "Forum/GetTag",
   "Forum/Like",
   "Forum/ReportComment",
   "GalleryLikeV2",
   "GalleryUpload",
   "GalleryUploadV2",
   "Game/Enter",
   "Game/Exit",
   "Game/Play",
   "GetBuddyInfo",
   "GetCategoryFileList",
   "GetCategoryFileListV2",
   "GetCommentListV2",
   "GetExpertListV2",
   "GetExpertListV3",
   "GetFansListV2",
   "GetFollowListV2",
   "GetGalleryAdvert",
   "GetMyLikeListV2",
   "GetMyUploadListV2",
   "GetNewAppVersion",
   "GetNewLetterListV2",
   "GetSomeoneInfoV2",
   "GetSomeoneListV2",
   "GetStartLogo",
   "GetStoreV2",
   "GetUpdateFileV3",
   "GetUserAllInfo",
   "HideGalleryV2",
   "Hot/GetHotFiles32",
   "Led/SendData",
   "Led/SetText",
   "Led/SetTextSpeed",
   "Led/Stop",
   "Log/SendLog",
   "LookScore",
   "Lottery/Announce",
   "Lottery/GetLotteryCnt",
   "Lottery/GetPrizeInfo",
   "Lottery/MyList",
   "Lottery/Start",
   "Lottery/WriteAddress",
   "Mall/Buy",
   "Mall/GetListV2",
   "Manager/AddGood",
   "Manager/AddPixelAmb",
   "Manager/AddRemoveRecommend",
   "Manager/ChangeClassify",
   "Manager/ChangeRecommend",
   "Manager/GetReportCommentList",
   "Manager/GetReportGallery",
   "Manager/GetReportUserList",
   "Manager/LimitComment",
   "Manager/LimitUpload",
   "Manager/PassGallery",
   "Manager/PassGalleryV2",
   "Manager/PassReport",
   "Manager/PassReportComment",
   "Manager/PassReportUser",
   "Manager/SetFillGameScore",
   "Medal/GetList",
   "Medal/GetNewValidList",
   "Memorial/Del",
   "Memorial/Get",
   "Memorial/Set",
   "Message/DeleteConversation",
   "Message/GetCommentList",
   "Message/GetConversationList",
   "Message/GetCustomInfo",
   "Message/GetFansList",
   "Message/GetLikeList",
   "Message/GetNotifyConfig",
   "Message/GetUnReadCnt",
   "Message/SetConversation",
   "Message/SetNotifyConfig",
   "MissionShare",
   "Mixer/Start",
   "NoDevice/GetDialogInfo",
   "NoDevice/GetGalleryAdvert",
   "PhoneGetRegisterCode",
   "PhoneRegister",
   "PhotoFrame/GetList",
   "PostRegionId",
   "PostTrack",
   "PostTrack",
   "PostUserRegionId",
   "QQLogin",
   "QingTing/GetFavorites",
   "QingTing/SetFavorite",
   "Radio/GetFavorites",
   "Radio/GetHistories",
   "Radio/SetFavorite",
   "Radio/SetHistory",
   "ReduceDownloads",
   "RefuseBuddy",
   "RemoveBuddy",
   "ReportCommentV2",
   "ReportGalleryV2",
   "SearchGalleryV2",
   "SearchUser",
   "SendIdentifyCode",
   "SendLetterV2",
   "SetRename",
   "SetUserInfo",
   "SetUserSign",
   "Shop/GetShopAuthLink",
   "Sleep/ExitTest",
   "Sleep/Get",
   "Sleep/Set",
   "Sleep/Test",
   "Sys/GetConf",
   "Sys/PlayTFGif",
   "Sys/SetAPO",
   "Sys/SetConf",
   "Sys/SetLightBack",
   "Sys/SetLightColor",
   "Sys/SetLightFront",
   "Sys/SetLogo",
   "Sys/SetNotifySound",
   "Sys/SetText",
   "Sys/SetTextDirection",
   "Sys/TimeZoneSearch",
   "Tag/Follow",
   "Tag/GetTagGalleryListV2",
   "Tag/GetTagInfo",
   "Tag/GetUserList",
   "Tag/SearchTagMore",
   "Tag/SearchTagSimple",
   "Test/SetUrl",
   "ThirdLogin",
   "TimePlan/Change",
   "TimePlan/Close",
   "TimePlan/Del",
   "TimePlan/GetList",
   "TimePlan/GetPlan",
   "TimePlan/Set",
   "Tools/GetNoiseStatus",
   "Tools/GetScoreBoard",
   "Tools/GetStopWatch",
   "Tools/GetTimer",
   "Tools/SetNoiseStatus",
   "Tools/SetScoreBoard",
   "Tools/SetStopWatch",
   "Tools/SetTimer",
   "TwitterLogin",
   "UpdateSuccessV2",
   "Upload/TempFile",
   "User/BindEmail",
   "User/BindPhone",
   "User/BindPhoneGetCode",
   "User/BlackList",
   "User/ClickAdvert",
   "User/CollectionDevice",
   "User/CollectionMusic",
   "User/CollectionRecord",
   "User/CollectionWIFI",
   "User/DefaultLocation",
   "User/DeleteUser",
   "User/GetBindInfo",
   "User/GetPersonalInfo",
   "User/GetPersonalInfoCnt",
   "User/ModifyCountryISOCode",
   "User/PersonalInfoExport",
   "User/PostCountryISOCode",
   "User/ReportUser",
   "User/SetAppVersion",
   "User/SetBackgroundImageV2",
   "User/SetUserHeadV2",
   "User/SetUserHeadV3",
   "User/SetUserNewSign",
   "User/UnBindThird",
   "UserLogin",
   "UserLogout",
   "UserProduct",
   "UserRegister",
   "Voice/GetList",
   "Voice/GetPixel",
   "Voice/Marked",
   "Voice/SendText",
   "Voice/SetPixel",
   "Voice/Upload",
   "Weather/SearchCity",
   "Weather/Send5Days",
   "Weather/SendCurrent"
]
```

Many (most?) of these would require JSON to be sent in a format similar to:

```json
{
   "UserId": 123456789,
   "Token": 123456789,
   "DeviceId": 123456789
}
```

Replacing the fields with your own values (see the section on logging in above). Each one would also have their own parameters, but these are command-specific

And here's a list of items from the firmware file divoom-92.bin (which is an ESP binary firmware file I think). Some of these relate to the MQTT server mentioned before:

```json
[
    "Alarm/Del",
    "Alarm/Listen",
    "App/DelUser",
    "Channel/AddEqData",
    "Channel/CleanCustom",
    "Channel/CloudIndex",
    "Channel/DeleteCustom",
    "Channel/DeleteEq",
    "Channel/GetAllConf",
    "Channel/GetAllCustomTime",
    "Channel/GetClockInfo",
    "Channel/GetConfig",
    "Channel/GetCustomPageIndex",
    "Channel/GetCustomTime",
    "Channel/GetEqPosition",
    "Channel/GetEqTime",
    "Channel/GetIndex",
    "Channel/GetNightView",
    "Channel/GetStartupChannel",
    "Channel/GetSubscribeTime",
    "Channel/OnOffScreen",
    "Channel/SetAllCustomTime",
    "Channel/SetBrightness",
    "Channel/SetClockConfig",
    "Channel/SetClockSelectId",
    "Channel/SetConfig",
    "Channel/SetCustom",
    "Channel/SetCustomId",
    "Channel/SetCustomPageIndex",
    "Channel/SetEqPosition",
    "Channel/SetEqTime",
    "Channel/SetIndex",
    "Channel/SetNightView",
    "Channel/SetProduceTime",
    "Channel/SetStartupChannel",
    "Channel/SetSubscribe",
    "Channel/SetSubscribeTime",
    "Device/AppRestartMqtt",
    "Device/AutoUpgradePush",
    "Device/BindUser",
    "Device/ClearResetFlag",
    "Device/CloseClockTimer",
    "Device/Connect",
    "Device/ConnectApp",
    "Device/DeleteResetAll",
    "Device/Disconnect",
    "Device/DisconnectMqtt",
    "Device/ExitSubscribeDisp",
    "Device/GetAlarm",
    "Device/GetAppIP",
    "Device/GetBlueName",
    "Device/GetClockInfo",
    "Device/GetClockList",
    "Device/GetCustomList",
    "Device/GetDailyLunarInfo",
    "Device/GetDeviceId",
    "Device/GetDeviceTime",
    "Device/GetEqDataList",
    "Device/GetExpertLast",
    "Device/GetFavoriteList",
    "Device/GetFileByApp",
    "Device/GetHistoryClockList",
    "Device/GetHotList",
    "Device/GetMemorial",
    "Device/GetSomeAlbum",
    "Device/GetSomeFontInfo",
    "Device/GetTimeDialAppPic",
    "Device/GetTimeDialFont",
    "Device/GetTimePlan",
    "Device/GetUserDefineList",
    "Device/GetWeatherInfo",
    "Device/Hearbeat",
    "Device/Init",
    "Device/OpenHttpRecord",
    "Device/PlayBuzzer",
    "Device/PlayTFGif",
    "Device/PushAppIP",
    "Device/ResetAll",
    "Device/SetAlarm",
    "Device/SetBlueName",
    "Device/SetDisTempMode",
    "Device/SetHighLightMode",
    "Device/SetMemorial",
    "Device/SetMirrorMode",
    "Device/SetScreenRotationAngle",
    "Device/SetUTC",
    "Device/SetWhiteBalance",
    "Device/ShareDevice",
    "Device/Unbind",
    "Device/UpLoadExpertLast",
    "Device/UpdateDevicePublicIP",
    "Device/UpdateLogLevel",
    "Device/UpgradeRecord",
    "DivoomIfft/AlarmSnoozeAction",
    "DivoomIfft/AlarmStartActive",
    "DivoomIfft/AlarmStopActive",
    "DivoomIfft/ClockAction",
    "DivoomIfft/DisplayAmazonMusicAction",
    "DivoomIfft/DisplayMessageAction",
    "DivoomIfft/DownClockFinishedActive",
    "DivoomIfft/DownClockStartActive",
    "DivoomIfft/HotPlayAction",
    "DivoomIfft/MemorialStartActive",
    "DivoomIfft/MemorialStopActive",
    "DivoomIfft/PlayNetGifAction",
    "DivoomIfft/ScreenCloseAction",
    "DivoomIfft/ScreenCtrlAction",
    "DivoomIfft/ScreenOpenAction",
    "DivoomIfft/StartCountDownAction",
    "DivoomIfft/SwitchClockAction",
    "DivoomIfft/TimeScheduleStartActive",
    "DivoomIfft/TimeScheduleStopedActive",
    "DivoomIfft/TimerAction",
    "DivoomIfft/UserDefineAction",
    "Draw/ClearHttpText",
    "Draw/CommandList",
    "Draw/DeleteTempFile",
    "Draw/ExitSync",
    "Draw/GetHttpGifId",
    "Draw/NeedLocalData",
    "Draw/NeedSendDraw",
    "Draw/ResetHttpGifId",
    "Draw/Send",
    "Draw/SendHttpGif",
    "Draw/SendHttpItemList",
    "Draw/SendHttpText",
    "Draw/SendLocal",
    "Draw/SendRealTimeEQ",
    "Draw/SendRemote",
    "Draw/SetInfo",
    "Draw/SetSpeedMode",
    "Draw/Sync",
    "Draw/UpLoadAndSend",
    "Draw/UpLoadEqAndSend",
    "Draw/UseHTTPCommandSource",
    "Game/GetFIFAWorldCupToken",
    "IJK/LMNOPQ",
    "Lamda/DivoomDisplayPic",
    "Lamda/DivoomFavoritePic",
    "Lamda/DivoomLightCtrl",
    "Lamda/DivoomRecommendPic",
    "Lamda/DivoomScreenCtrl",
    "Lamda/DivoomSubscribePic",
    "Lamda/DivoomSwitchClock",
    "Memorial/Del",
    "SDHC/SDXC",
    "Sand/Send",
    "Sleep/ExitTest",
    "Sleep/Get",
    "Sleep/Set",
    "Sleep/Test",
    "Spotify/RefreshToken",
    "Sys/FormatTF",
    "Sys/GetBrightness",
    "Sys/GetConf",
    "Sys/LogAndLat",
    "Sys/PlayTFGif",
    "Sys/PoweronMode",
    "Sys/PushUpdate",
    "Sys/SetConf",
    "Sys/TimeZone",
    "Test/SetUrl",
    "TimePlan/Close",
    "Tools/GetNoiseStatus",
    "Tools/GetScoreBoard",
    "Tools/GetStopWatch",
    "Tools/GetTimer",
    "Tools/SetNoiseStatus",
    "Tools/SetScoreBoard",
    "Tools/SetStopWatch",
    "Tools/SetTimer",
    "Weather/GetForecastWeatherInfo",
    "Weather/GetRealWeatherInfo"
]
```