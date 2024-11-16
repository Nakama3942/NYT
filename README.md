<div align="center">

[![GitHub license](https://img.shields.io/github/license/Nakama3942/WiretappingScanner?color=gold&style=for-the-badge)](https://github.com/Nakama3942/NYT/blob/master/LICENSE)

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Nakama3942/NYT?label=latest%20release&logo=github&style=for-the-badge)

![GitHub last commit](https://img.shields.io/github/last-commit/Nakama3942/NYT?style=for-the-badge)
![GitHub Release Date](https://img.shields.io/github/release-date/Nakama3942/NYT?style=for-the-badge)

![GitHub repo size](https://img.shields.io/github/repo-size/Nakama3942/NYT?color=darkgreen&style=for-the-badge)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/Nakama3942/NYT?color=darkgreen&style=for-the-badge)
![Lines of code](https://img.shields.io/tokei/lines/github/Nakama3942/NYT?style=for-the-badge)

</div>

# NYT
### Content
- [NYT](#nyt)
	- [Content](#content)
	- [Overview](#overview)
	- [LICENSE](#license)
	- [Installation](#installation)
	<!-- - [Troubleshooting](#troubleshooting) -->
	- [Authors](#authors)

## Overview
This a program that automates the work with YouTube, which the author (nicknamed Nakama) often did manually, and it took a lot of time. For example, downloading a video from YouTube.

It is not always possible to download videos through various resources such as y2mate:
> Either the link is not found, or the video is not being converted, or the download window is just not displayed, sometimes it takes a long time to wait, often the resource changes the name of the video or even spoils it.

Everything is bad. And the savefrom.net resource does not allow you to download videos higher than 360p at all... (╥﹏╥)

> [!WARNING]
> **Old text referring to the console version**
>
> This script allows:
> 1. Quickly download videos from YouTube without problems and changing the name;
> 2. Rename any files in the directory;
> 3. Extract audio from video;
> 4. Download immediately audio from YouTube.
>
> Use whoever needs it.

The new program can:
1. Download video and audio from YouTube and other resources that support YT-DLP (important: first of all, the program was developed and emphasizes on those downloading from YouTube) with the possibility of specifying your own name for the downloaded file (well, you can not change it)
2. Extract audio from video
3. You can set the quality of the video and audio to be downloaded
4. Has many settings
5. Provides a good (in the author's opinion) interface that is easy to use

Hope this helps someone else besides me...

- [Content](#content)

## LICENSE

The full text of the license can be found at the following [link](https://github.com/Nakama3942/NYT/blob/main/LICENSE).

> Copyright © 2024 Kalynovsky Valentin. All rights reserved.
>
> Licensed under the Apache License, Version 2.0 (the "License");
> you may not use this file except in compliance with the License.
> You may obtain a copy of the License at
>
> http://www.apache.org/licenses/LICENSE-2.0
>
> Unless required by applicable law or agreed to in writing, software
> distributed under the License is distributed on an "AS IS" BASIS,
> WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
> See the License for the specific language governing permissions and
> limitations under the License.

## Installation
The program does not require installation. Just unzip the archive wherever you want and save the shortcut to the executable file.

## System Requirements
.py:
- python		v3.11 or higher
- argparse		(built-in)
- os			(built-in)
- subprocess	(built-in)
- readchar		(pip install readchar)
- yt_dlp		(pip install yt_dlp)

.pyw:
- python        v3.11 or higher
- sys           (built-in)
- os            (built-in)
- subprocess    (built-in)
- datetime      (built-in)
- logging       (built-in)
- re            (built-in)
- pickle        (built-in)
- copy          (built-in)
- concurrent    (built-in)
- requests      (pip install requests)
- yaml          (pip install pyyaml)
- yt_dlp        (pip install yt-dlp)
- PyQt6         (pip install pyqt6)
- qdarktheme    (pip install qdarktheme)

.exe
- windows		v10 or higher

<!--## Troubleshooting
All functionality has been tested by Author, but if you have problems using it, the code does not work, have suggestions for optimization or advice for improving the style of the code and the name - I invite you [here](https://github.com/Nakama3942/WiretappingScanner/blob/master/CONTRIBUTING.md) and [here](https://github.com/Nakama3942/WiretappingScanner/blob/master/CODE_OF_CONDUCT.md).

- [Content](#content)-->

## Authors

<table align="center" style="border-width: 10; border-style: ridge">
	<tr>
		<td align="center" width="200"><a href="https://github.com/Nakama3942"><img src="https://avatars.githubusercontent.com/u/73797846?s=400&u=a9b7688ac521d739825d7003a5bd599aab74cb76&v=4" width="150px;" alt=""/><br /><sub><b>Kalynovsky Valentin</b></sub></a><sub><br />"Ideological inspirer and Author"</sub></td>
	    <!--<td></td>-->
	</tr>
<!--
	<tr>
		<td></td>
		<td></td>
	</tr>
-->
</table>
