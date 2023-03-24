# Notes about the Divoom Pixoo 64

This document contains various notes about the Divoom Pixoo. 

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

## Sending images

Sending animations to the device is weird. There's a few caveats:

 - `Draw/CommandList` **can't** be used to batch-send frames. You need to make several `Draw/SendHttpGif` commands in succession. Unless you do the work on another thread, this will block your app for a bit, depending on how big your animation is (tested on animations up to 2mb in size)
 - There is a maximum of about 40 frames, so if your animation has more frames than this, your Pixoo may crash. This module limits the number of frames for you.
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

There's some interesting commands that I grabbed from the decompiled APK. These are for the Divoom Online API, though some of them might overlap with the local API:

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