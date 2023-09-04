usage: Nakama’s Youtube Tools [-h] [-l]
                              (-d PLAYLIST_URL QUALITY | -c | -r SEPARATOR | -e | -dc PLAYLIST_URL QUALITY | -re SEPARATOR | -de PLAYLIST_URL QUALITY | -dee PLAYLIST_URL | -dce PLAYLIST_URL | -a PLAYLIST_URL QUALITY SEPARATOR | -ae PLAYLIST_URL SEPARATOR)

This a program that automates the work with YouTube, which the author (Nakama) often did manually and it took a lot of time. For example, downloading a video from YouTube. It is not always possible to download a video through y2mate: either the link is not found, or the video is not being converted, or the download window is just not displayed, sometimes it takes a long time to wait, often the resource changes the name of the video or even spoils it. Everything is bad. This script allows: 1) Quickly download videos from YouTube without problems and changing the name; 2) Rename any files in the directory; 3) Extract audio from video; 4) Download immediately audio from YouTube. Use whoever needs it. Hint: as a separator, choose those characters that cannot be used in the title of the file, in case you have to enter this character in the file title, so that there would be no problems later.

options:
  -h, --help            Show this help message and exit

  -l, --logging         Enables logging

  -d PLAYLIST_URL QUALITY, --download-playlist PLAYLIST_URL QUALITY
                        Download all video from a playlist; You must provide a playlist URL and him quality as the arguments

  -c, --create-filelist
                        Create list of all files names in this directory

  -r SEPARATOR, --rename-files SEPARATOR
                        Rename all files on names from the list; You must provide a separator as the argument, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored

  -e, --extract-audio
                        Extract audio tracks from all videos in this directory; Requires ffmpeg installed

  -dc PLAYLIST_URL QUALITY, --download-create PLAYLIST_URL QUALITY
                        Download video from a playlist and create list of all files names in this directory; You must provide a playlist URL and him quality as the arguments

  -re SEPARATOR, --rename-extract SEPARATOR
                        Rename the all files on names from list and extract the audio tracks from all videos in this directory; You must provide a separator as the arguments, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored; Requires ffmpeg installed

  -de PLAYLIST_URL QUALITY, --download-extract PLAYLIST_URL QUALITY
                        Download all video from a playlist and extract the audio tracks from all downloaded videos in this directory; You must provide a playlist URL and him quality as the arguments; Requires ffmpeg installed

  -dee PLAYLIST_URL, --download-extract-extension PLAYLIST_URL
                        Download directly all audios from the playlist to replace the video download, which takes more traffic, time to download it and disk space with additional waste of time extracting audio; You must provide a playlist URL as the argument

  -dce PLAYLIST_URL, --download-create-extension PLAYLIST_URL
                        Similarly, --download-create downloads a playlist and creates a list of files, but differs in that it makes the download not of video, but of audio using the extended --download-extract-extension algorithm (in other words, it executes both -dee and -c); You must provide a playlist URL as the argument

  -a PLAYLIST_URL QUALITY SEPARATOR, --all PLAYLIST_URL QUALITY SEPARATOR
                        Expanding the --download-extract argument to include file renaming: the program will download videos, create a list of files and wait for the user to specify new file names and press Enter, then rename the files and extract the audio from the video; You must provide a playlist URL and him quality as the arguments; Also you must provide a separator, through which old and new file names are entered; If the separator is not
                        specified in the file, the string is ignored; Requires ffmpeg installed

  -ae PLAYLIST_URL SEPARATOR, --all-extension PLAYLIST_URL SEPARATOR
                        Extension of the --download-create-extension argument to include file renaming: the program will download audio tracks, create a list of files, and wait until the user specifies new filenames and press Enter, then rename the files; You must provide a playlist URL and a separator as the argument, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored

Hope this helps someone else besides me...