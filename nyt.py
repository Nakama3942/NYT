#  Copyright © 2023 Kalynovsky Valentin. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from argparse import ArgumentParser
from readchar import readkey
from yt_dlp import YoutubeDL
from os import listdir, rename
from subprocess import run, CalledProcessError

def download_audio_from_playlist(youtube_playlist_url, logging):
	ydl_opts = {
		"format": "bestaudio/best",
		"quiet": not logging,
		"extract_audio": True,
		"audio-format": "mp3",
		"output": "%(title)s.%(ext)s",
		"write-thumbnail": True,
		"postprocessors": [{
			"key": "FFmpegExtractAudio",
			"preferredcodec": "mp3",
			"preferredquality": "192",
		}],
	}
	try:
		with YoutubeDL(ydl_opts) as ydl:
			ydl.download([youtube_playlist_url])
			print("\033[32m[+] Audio from playlist has been downloaded\033[0m")
	except Exception as err:
		print(f"\033[31m[✗] ERROR: Downloading error\033[0m\n\033[3m{err}\033[0m")

def download_playlist(youtube_playlist_url, quality, logging):
	ydl_opts = {
		"format": f"best[height<={quality}]",
		"quiet": not logging,
		"output": "%(title)s.%(ext)s",
	}
	try:
		with YoutubeDL(ydl_opts) as ydl:
			ydl.download([youtube_playlist_url])
			print("\033[32m[+] Video from playlist has been downloaded\033[0m")
	except Exception as err:
		print(f"\033[31m[✗] ERROR: Downloading error\033[0m\n\033[3m{err}\033[0m")

def create_list():
	with open("list.txt", "w", encoding="utf-8") as file:
		file.write("\n".join(listdir()))
		print("\033[32m[+] Created the files list 'list.txt'\033[0m")

def rename_files(separator):
	with open("list.txt", "r", encoding="utf-8") as file:
		for line in file.readlines():
			parts = line.split(separator)
			if len(parts) == 2:
				try:
					rename(parts[0], parts[1].strip())
					print(f"\033[32m[✓] File \033[3m{parts[0]}\033[23m renamed to \033[3m{parts[1].strip()}\033[23m\033[0m")
				except FileNotFoundError as err:
					print(f"\033[31m[✗] ERROR: Either the name of a non-existent file is specified, or the new name is empty\033[0m\n\033[3m{err}\033[0m")
			else:
				print(f"[-] Ignored the '{line.strip()}'")

def extract_audio(logging):
	for file in listdir():
		if file.endswith(".mp4"):
			command = [
				"ffmpeg",						# Путь к ffmpeg (если он не в PATH)
				"-i", file,						# Входное видео
				"-vn",							# Опция для указания, что нужно только аудио
				"-acodec", "libmp3lame",		# Копирование аудио без перекодирования
				"-ab", "192k",					# Установка битрейта аудио
				file.replace(".mp4", ".mp3")	# Выходное аудио
			]
			try:
				if logging:
					run(command, check=True)
				else:
					run(command, capture_output=True, check=True)
				print(f"\033[32m[✓] File \033[3m{file}\033[23m converted successfully\033[0m")
			except CalledProcessError as err:
				print(f"\033[31m[✗] ERROR: File \033[3m{file}\033[23m could not be converted\033[0m\n\033[3m{err}\033[0m")
		else:
			print(f"[-] Ignored the '\033[3m{file}\033[23m'")

def argument_parser():
	parser = ArgumentParser(
		prog="Nakama's Youtube Tools",
		description="This a program that automates the work with YouTube, which the author (Nakama) often did manually and it took a lot of time. For example, downloading a video from YouTube. It is not always possible to download a video through y2mate: either the link is not found, or the video is not being converted, or the download window is just not displayed, sometimes it takes a long time to wait, often the resource changes the name of the video or even spoils it. Everything is bad. This script allows: 1) Quickly download videos from YouTube without problems and changing the name; 2) Rename any files in the directory; 3) Extract audio from video; 4) Download immediately audio from YouTube. Use whoever needs it. Hint: as a separator, choose those characters that cannot be used in the title of the file, in case you have to enter this character in the file title, so that there would be no problems later.",
		epilog="Hope this helps someone else besides me..."
	)
	parser.add_argument(
		"-l",
		"--logging",
		action="store_true",
		help="Enables logging"
	)
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument(
		"-d",
		"--download-playlist",
		nargs=2,
		metavar=("PLAYLIST_URL", "QUALITY"),
		help="Download all video from a playlist; You must provide a playlist URL and him quality as the arguments"
	)
	group.add_argument(
		"-c",
		"--create-filelist",
		action="store_true",
		help="Create list of all files names in this directory"
	)
	group.add_argument(
		"-r",
		"--rename-files",
		nargs=1,
		metavar="SEPARATOR",
		help="Rename all files on names from the list; You must provide a separator as the argument, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored"
	)
	group.add_argument(
		"-e",
		"--extract-audio",
		action="store_true",
		help="Extract audio tracks from all videos in this directory; Requires ffmpeg installed"
	)
	group.add_argument(
		"-dc",
		"--download-create",
		nargs=2,
		metavar=("PLAYLIST_URL", "QUALITY"),
		help="Download video from a playlist and create list of all files names in this directory; You must provide a playlist URL and him quality as the arguments"
	)
	group.add_argument(
		"-re",
		"--rename-extract",
		nargs=1,
		metavar="SEPARATOR",
		help="Rename the all files on names from list and extract the audio tracks from all videos in this directory; You must provide a separator as the arguments, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored; Requires ffmpeg installed"
	)
	group.add_argument(
		"-de",
		"--download-extract",
		nargs=2,
		metavar=("PLAYLIST_URL", "QUALITY"),
		help="Download all video from a playlist and extract the audio tracks from all downloaded videos in this directory; You must provide a playlist URL and him quality as the arguments; Requires ffmpeg installed"
	)
	group.add_argument(
		"-dee",
		"--download-extract-extension",
		nargs=1,
		metavar="PLAYLIST_URL",
		help="Download directly all audios from the playlist to replace the video download, which takes more traffic, time to download it and disk space with additional waste of time extracting audio; You must provide a playlist URL as the argument"
	)
	group.add_argument(
		"-dce",
		"--download-create-extension",
		nargs=1,
		metavar="PLAYLIST_URL",
		help="Similarly, --download-create downloads a playlist and creates a list of files, but differs in that it makes the download not of video, but of audio using the extended --download-extract-extension algorithm (in other words, it executes both -dee and -c); You must provide a playlist URL as the argument"
	)
	group.add_argument(
		"-a",
		"--all",
		nargs=3,
		metavar=("PLAYLIST_URL", "QUALITY", "SEPARATOR"),
		help="Expanding the --download-extract argument to include file renaming: the program will download videos, create a list of files and wait for the user to specify new file names and press Enter, then rename the files and extract the audio from the video; You must provide a playlist URL and him quality as the arguments; Also you must provide a separator, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored; Requires ffmpeg installed"
	)
	group.add_argument(
		"-ae",
		"--all-extension",
		nargs=2,
		metavar=("PLAYLIST_URL", "SEPARATOR"),
		help="Extension of the --download-create-extension argument to include file renaming: the program will download audio tracks, create a list of files, and wait until the user specifies new filenames and press Enter, then rename the files; You must provide a playlist URL and a separator as the argument, through which old and new file names are entered; If the separator is not specified in the file, the string is ignored"
	)

	args = parser.parse_args()

	if args.download_playlist:
		download_playlist(args.download_playlist[0], args.download_playlist[1], args.logging)
	if args.create_filelist:
		create_list()
	if args.rename_files:
		rename_files(args.rename_files[0])
	if args.extract_audio:
		extract_audio(args.logging)
	if args.download_create:
		download_playlist(args.download_create[0], args.download_create[1], args.logging)
		create_list()
	if args.rename_extract:
		rename_files(args.rename_extract[0])
		extract_audio(args.logging)
	if args.download_extract:
		download_playlist(args.download_extract[0], args.download_extract[1], args.logging)
		extract_audio(args.logging)
	if args.download_extract_extension:
		download_audio_from_playlist(args.download_extract_extension[0], args.logging)
	if args.download_create_extension:
		download_audio_from_playlist(args.download_create_extension[0], args.logging)
		create_list()
	if args.all:
		download_playlist(args.all_go[0], args.all_go[1], args.logging)
		create_list()
		print("\033[33m[↵] Press Enter to continue or Esc to exit...\033[0m")
		while True:
			key = readkey()
			if key == "\r":  # Enter
				print("\033[32m[►] Continuing...\033[0m")
				break
			elif key == "\x1b":  # Esc
				print("\033[34m[■] Exiting...\033[0m")
				return
		rename_files(args.all_go[2])
		extract_audio(args.logging)
	if args.all_extension:
		download_audio_from_playlist(args.all_go_extension[0], args.logging)
		create_list()
		print("\033[33m[↵] Press Enter to continue or Esc to exit...\033[0m")
		while True:
			key = readkey()
			if key == "\r":  # Enter
				print("\033[32m[►] Continuing...\033[0m")
				break
			elif key == "\x1b":  # Esc
				print("\033[34m[■] Exiting...\033[0m")
				return
		rename_files(args.all_go_extension[1])

if __name__ == "__main__":
	argument_parser()
