#  Copyright © 2024 Kalynovsky Valentin. All rights reserved.
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

# https://www.youtube.com/playlist?list=PL2MbnZfZV5Ksz3V1TABFnBiEXDjK4RqKM

import sys
from os import listdir, getcwd, rename, path, getenv
from subprocess import run, CalledProcessError

import yt_dlp.utils.networking
from requests import get
from datetime import datetime
import logging
import re
import pickle
import yaml
from copy import deepcopy

from concurrent.futures import ThreadPoolExecutor

from yt_dlp import YoutubeDL

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit, QCheckBox, QProgressBar, QComboBox, QPushButton, QPlainTextEdit, QTextBrowser, QTabWidget, QSpacerItem, QMessageBox, QStatusBar, QFileDialog, QColorDialog
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon

from qdarktheme import setup_theme, get_themes

description = """Author: Kalynovsky Valentin<br>
Nickname: Nakama 【仲間】<br>
Source: <a href='https://github.com/Nakama3942/NYT'>NYT</a> GitHub repository<br>
<br>
License: <a href='http://www.apache.org/licenses/LICENSE-2.0'>Apache License 2.0</a><br>
Copyright © 2024 Kalynovsky Valentin. All rights reserved.<br>
<br>
This program is written to download videos from YouTube, download audio from youtube videos, and extract audio from existing videos.<br>
<br>
The program is a graphical wrapper over the <a href='https://pypi.org/project/yt-dlp/'><i>YT-DLP</i></a> program.<br>
<br>
I will be glad if my program helps someone."""

def custom_but_qss_preparing(rgb_color):
	return f"""
		/* Обычное состояние */
		QPushButton {{
			background-color: rgba({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}, 0.4);
			color: #fff;
			border: 0px;
			border-radius: 10px;
			font-size: 16px;
		}}

		/* Состояние при наведении */
		QPushButton:hover {{
			background-color: rgba({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}, 0.9);
			color: #000;
		}}

		/* Состояние при нажатии */
		QPushButton:pressed {{
			background-color: rgba({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}, 0.8);
			color: #000;
		}}
	"""


def convert_http_header_to_dict(obj):
	if isinstance(obj, yt_dlp.utils.networking.HTTPHeaderDict):
		return dict(obj)
	elif isinstance(obj, dict):
		return {key: convert_http_header_to_dict(value) for key, value in obj.items()}
	elif isinstance(obj, list):
		return [convert_http_header_to_dict(item) for item in obj]
	else:
		return obj

# Кастомный обработчик логов для передачи сигналов
class LogSignalEmitter(logging.Handler, QObject):
	log_signal = pyqtSignal(str)  # Сигнал для передачи лог-сообщений

	def __init__(self):
		logging.Handler.__init__(self)  # Инициализация логгера
		QObject.__init__(self)  # Инициализация QObject

	def emit(self, record):
		self.log_signal.emit(self.format(record))  # Излучаем сигнал с текстом лога

# Настройка логирования

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.DEBUG)

# Обработчик для записи в файл
file_handler = logging.FileHandler('nyt.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.INFO)

# Обработчик для вывода в статус-бар
status_handler = LogSignalEmitter()
status_handler.setFormatter(logging.Formatter('%(message)s'))
status_handler.setLevel(logging.INFO)

# Настройка основного логгера программы (nyt)
log = logging.getLogger("nyt")
log.setLevel(logging.DEBUG)
log.addHandler(console_handler)
log.addHandler(file_handler)
log.addHandler(status_handler)

# Настройка логгера для yt_dlp
yt_dlp_log = logging.getLogger("yt_dlp")
yt_dlp_log.setLevel(logging.DEBUG)
yt_dlp_log.addHandler(console_handler)
yt_dlp_log.addHandler(file_handler)
yt_dlp_log.addHandler(status_handler)

# todo
#  1. Реализовать центрирование окна
#  2. Обновить логирование ffmpeg
#  3. Реализовать кнопки сворачивания окна
#  4. Проверить загрузку из других источников (например, твиттера)
#  5. Провести рефакторинг кода

class ProgramData:
	settings = {
		"theme": {
			"title bar": 0,
			"theme": 0,
			"accent color": "#34C759"
		},
		"logging": {
			"enable logging": True,
			"enable yt-dlp logs": True,
			"enable ffmpeg logs": True,
			"enable debug logs": False
		},
		"folders": {
			"download folder": "",
			"ffmpeg folder": ""
		},
		"other video data settings": {
			"data format": 0
		},
		"advanced naming": {
			"advanced naming": False,
			"advanced naming uploader": False,
			"advanced naming resolution": False,
			"advanced naming playlist": False,
			"advanced naming playlist index": False
		}
	}

	cache = {}

	def load_settings(self):
		try:
			with open("nyt.settings.yaml", "r") as settings_file:
				self.settings = yaml.safe_load(settings_file)
		except FileNotFoundError:
			with open("nyt.settings.yaml", "w") as settings_file:
				yaml.dump(self.settings, settings_file, sort_keys=False)

	def save_settings(self):
		with open("nyt.settings.yaml", "w") as settings_file:
			yaml.dump(self.settings, settings_file, sort_keys=False)

	def load_cache(self):
		try:
			with open("nyt.cache", "rb") as cache_file:
				self.cache = pickle.load(cache_file)
		except FileNotFoundError:
			with open("nyt.cache", "wb") as cache_file:
				pickle.dump(self.cache, cache_file)

	def save_cache(self):
		with open("nyt.cache", "wb") as cache_file:
			pickle.dump(self.cache, cache_file)

program_data = ProgramData()

class Loader(QObject):
	founded = pyqtSignal(dict)
	updated = pyqtSignal(int, int)
	extracted = pyqtSignal()
	start_download = pyqtSignal()
	finish_download = pyqtSignal()
	submit_done = pyqtSignal()

	def __init__(self):
		super(Loader, self).__init__()
		self.__executor = ThreadPoolExecutor(max_workers=10)

	def submit_find_playlist(self, playlist_url):
		future = self.__executor.submit(self.__get_playlist_metadata, playlist_url)
		future.add_done_callback(self.__internal_done_callback)

	def submit_find_video(self, video_url):
		future = self.__executor.submit(self.__get_video_metadata, video_url)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_video(self, video_url, video_title, video_format, audio_quality):
		future = self.__executor.submit(self.__download_video_wrapper, video_url, video_title, video_format, audio_quality)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_audio(self, video_url, video_title, audio_quality):
		future = self.__executor.submit(self.__download_audio_wrapper, video_url, video_title, audio_quality)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_va(self, video_url, video_title, video_format, audio_quality):
		future = self.__executor.submit(self.__download_va_wrapper, video_url, video_title, video_format, audio_quality)
		future.add_done_callback(self.__internal_done_callback)

	def submit_extract_audio(self, filenames, ffmpeg_folder, enable_logging):
		future = self.__executor.submit(self.__extract_audio_wrapper, filenames, ffmpeg_folder, enable_logging)
		future.add_done_callback(self.__internal_done_callback)

	def __get_playlist_metadata(self, playlist_url):
		ydl_opts = {
			"quiet": False,			# Включает логирование
			"logger": yt_dlp_log,
			"extract_flat": "in_playlist"
		}
		with YoutubeDL(ydl_opts) as ydl:
			self.__found_emitter(ydl.extract_info(playlist_url, download=False))  # Только извлекает информацию

	def __get_video_metadata(self, video_url):
		ydl_opts = {
			"quiet": False,			# Включает логирование
			"logger": yt_dlp_log
		}
		with YoutubeDL(ydl_opts) as ydl:
			self.__found_emitter(ydl.extract_info(video_url, download=False))  # Только извлекает информацию

	def __download_video_wrapper(self, video_url, video_title, video_format, audio_quality):
		self.__start_download_emitter()
		try:
			log.info("Starting download")
			self.__download_video(video_url, video_title, video_format, audio_quality)
			log.info("[+] Video from playlist has been downloaded")
			self.__finish_download_emitter()
		except Exception as err:
			log.error(f"[✗] ERROR: Downloading error {err}")

	def __download_audio_wrapper(self, video_url, video_title, audio_quality):
		self.__start_download_emitter()
		try:
			log.info("Starting download")
			self.__download_audio(video_url, video_title, audio_quality)
			log.info("[+] Video from playlist has been downloaded")
			self.__finish_download_emitter()
		except Exception as err:
			log.error(f"[✗] ERROR: Downloading error {err}")

	def __download_va_wrapper(self, video_url, video_title, video_format, audio_quality):
		self.__start_download_emitter()
		try:
			log.info("Starting download")
			self.__download_video(video_url, video_title, video_format, audio_quality)
			self.__download_audio(video_url, video_title, audio_quality)
			log.info("[+] Video from playlist has been downloaded")
			self.__finish_download_emitter()
		except Exception as err:
			log.error(f"[✗] ERROR: Downloading error {err}")

	def __extract_audio_wrapper(self, filenames, ffmpeg_folder, enable_logging):
		for file in filenames:
			self.__ffmpeg_extract_audio(ffmpeg_folder, file, enable_logging)
		log.info(f"[✓] Extraction complete")

	def __download_video(self, video_url, video_title, video_format, audio_quality):
		ydl_opts = {
			"format": f"{video_format}+ba[ext=m4a][tbr<={audio_quality}]",
			"quiet": False,
			"outtmpl": video_title,
			"progress_hooks": [self.__update_emitter],
			"logger": yt_dlp_log
		}
		with YoutubeDL(ydl_opts) as ydl:
			ydl.download([video_url])

	def __download_audio(self, video_url, video_title, audio_quality):
		ydl_opts = {
			"format": f"ba[ext=m4a][tbr<={audio_quality}]",
			"quiet": False,
			"outtmpl": video_title,
			"progress_hooks": [self.__update_emitter],
			"logger": yt_dlp_log,
			"postprocessors": [{
				"key": "FFmpegExtractAudio",
				"preferredcodec": "mp3",
				"preferredquality": str(audio_quality)
			}]
		}
		with YoutubeDL(ydl_opts) as ydl:
			ydl.download([video_url])

	def __ffmpeg_extract_audio(self, ffmpeg, filename, enable_logging):
		command = [
			ffmpeg,								# Путь к ffmpeg (если он не в PATH)
			"-loglevel", "info",				# Уровень логирования для ffmpeg
			"-hide_banner",						# Скрытие баннера ffmpeg при запуске
			"-i", filename,						# Входное видео
			"-vn",								# Опция для указания, что нужно только аудио (без видео)
			"-acodec", "libmp3lame",			# Кодек для выходного аудио (здесь используется MP3-кодек LAME)
			"-ab", "192k",						# Установка битрейта аудио
			filename.replace(".mp4", ".mp3")	# Выходное аудио (с заменой расширения на .mp3)
		]
		try:
			result = run(command, check=True, capture_output=True, text=True, encoding="utf-8")
			if enable_logging:
				# Отправляем stdout и stderr в логгер
				log.info(result.stdout)
				if result.stderr:
					log.error(result.stderr)
			self.__extract_emitter(f"[✓] File {filename} converted successfully")
		except CalledProcessError as err:
			log.error(f"[✗] ERROR: File {filename} could not be converted {err}")

	def __found_emitter(self, data):
		self.founded.emit(data)
		log.info(f"Data found... Video title is {data['title']}")

	def __update_emitter(self, updated_data):
		if updated_data['status'] == 'downloading':
			self.updated.emit(updated_data['total_bytes'], updated_data['downloaded_bytes'])
			log.info(updated_data['_default_template'])

	def __extract_emitter(self, message=""):
		self.extracted.emit()
		log.info(message)

	def __start_download_emitter(self, message=""):
		self.start_download.emit()
		log.info(message)

	def __finish_download_emitter(self, message=""):
		self.finish_download.emit()
		log.info(message)

	def __internal_done_callback(self, future):
		self.submit_done.emit()
		log.debug(future)

class SettingsWidget(QWidget):
	title_bar_signal = pyqtSignal()
	appearance_signal = pyqtSignal()
	accent_color_signal = pyqtSignal(str)
	enable_logging_signal = pyqtSignal(bool)
	enable_yt_dlp_logger_signal = pyqtSignal(bool)
	enable_ffmpeg_logger_signal = pyqtSignal(bool)
	enable_debug_logs_signal = pyqtSignal(bool)
	choose_download_folder_signal = pyqtSignal()
	choose_ffmpeg_folder_signal = pyqtSignal()

	def __init__(self):
		super(SettingsWidget, self).__init__()

		self.theme_group_box = QGroupBox("Theme")
		self.title_bar_combo_box = QComboBox()
		self.appearance_combo_box = QComboBox()
		self.color_dialog_butt = QPushButton()
		self.blue_color_butt = QPushButton()
		self.purple_color_butt = QPushButton()
		self.pink_color_butt = QPushButton()
		self.red_color_butt = QPushButton()
		self.orange_color_butt = QPushButton()
		self.yellow_color_butt = QPushButton()
		self.green_color_butt = QPushButton()
		self.graphite_color_butt = QPushButton()
		self.enable_logging_group_box = QGroupBox("Logging")
		self.enable_yt_dlp_logs_check_box = QCheckBox("Enable YT-DLP logs")
		self.enable_ffmpeg_logs_check_box = QCheckBox("Enable FFmpeg logs")
		self.enable_debug_logs_check_box = QCheckBox("Enable DEBUG logs")
		self.folders_group_box = QGroupBox("Folders")
		self.download_folder_label = QLineEdit()
		self.ffmpeg_folder_label = QLineEdit()
		self.choose_download_folder_butt = QPushButton("Choose download folder")
		self.choose_ffmpeg_folder_butt = QPushButton("Choose FFmpeg exe")
		self.extra_download_group_box = QGroupBox("Extra-mode")
		self.extra_download_video_check_box = QCheckBox("Run extra download video")
		self.extra_download_audio_check_box = QCheckBox("Run extra download audio")
		self.extra_download_va_check_box = QCheckBox("Run extra download video and audio")
		self.other_data_display_group_box = QGroupBox("Other video data settings")
		self.date_format_label = QLabel("Choose the data format:")
		self.date_format_combo_box = QComboBox()
		self.date_format_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		self.advanced_naming_group_box = QGroupBox("Add the additional data to name video?")
		self.advanced_naming_uploader_check_box = QCheckBox("Uploader")
		self.advanced_naming_resolution_check_box = QCheckBox("Resolution")
		self.advanced_naming_playlist_check_box = QCheckBox("Playlist")
		self.advanced_naming_playlist_index_check_box = QCheckBox("Playlist index")
		self.quality_group_box = QGroupBox("Quality")
		self.video_quality_label = QLabel("Video:")
		self.video_quality_combo_box = QComboBox()
		self.video_quality_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		self.audio_quality_label = QLabel("Audio:")
		self.audio_quality_combo_box = QComboBox()
		self.audio_quality_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

		response = get("https://raw.githubusercontent.com/Nakama3942/NYT/3448ba0653bfeabfadfd8a7d9ce7b2836df36e91/icons/colorize_24dp.svg")
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio)
			self.color_dialog_butt.setIcon(QIcon(pixmap))
		else:
			log.warning("Image loading failed")

		self.title_bar_combo_box.addItems(["Custom title bar", "System title bar"])
		self.appearance_combo_box.addItems(tuple(theme.capitalize() for theme in get_themes()))
		self.color_dialog_butt.setMaximumHeight(25)
		self.blue_color_butt.setMaximumHeight(25)
		self.purple_color_butt.setMaximumHeight(25)
		self.pink_color_butt.setMaximumHeight(25)
		self.red_color_butt.setMaximumHeight(25)
		self.orange_color_butt.setMaximumHeight(25)
		self.yellow_color_butt.setMaximumHeight(25)
		self.green_color_butt.setMaximumHeight(25)
		self.graphite_color_butt.setMaximumHeight(25)
		self.color_dialog_butt.setStyleSheet(custom_but_qss_preparing([200, 200, 200]))
		self.blue_color_butt.setStyleSheet(custom_but_qss_preparing([0, 123, 255]))
		self.purple_color_butt.setStyleSheet(custom_but_qss_preparing([88, 86, 214]))
		self.pink_color_butt.setStyleSheet(custom_but_qss_preparing([255, 45, 85]))
		self.red_color_butt.setStyleSheet(custom_but_qss_preparing([255, 59, 48]))
		self.orange_color_butt.setStyleSheet(custom_but_qss_preparing([255, 149, 0]))
		self.yellow_color_butt.setStyleSheet(custom_but_qss_preparing([255, 204, 0]))
		self.green_color_butt.setStyleSheet(custom_but_qss_preparing([52, 199, 89]))
		self.graphite_color_butt.setStyleSheet(custom_but_qss_preparing([128, 128, 128]))
		self.enable_logging_group_box.setCheckable(True)
		self.enable_logging_group_box.setChecked(True)
		self.enable_yt_dlp_logs_check_box.setChecked(True)
		self.enable_ffmpeg_logs_check_box.setChecked(True)
		self.download_folder_label.setReadOnly(True)
		self.download_folder_label.setText(getcwd())
		self.ffmpeg_folder_label.setReadOnly(True)
		self.ffmpeg_folder_label.setText(next((path.join(system_path, "ffmpeg.exe") for system_path in getenv("PATH").split(";") if "ffmpeg" in system_path.lower()), None))
		self.choose_download_folder_butt.setMaximumWidth(150)
		self.advanced_naming_group_box.setCheckable(True)
		self.advanced_naming_group_box.setChecked(False)
		self.video_quality_combo_box.addItems(["unknown"])
		self.audio_quality_combo_box.addItems(["unknown"])
		self.audio_quality_combo_box.setFixedWidth(100)
		self.date_format_combo_box.addItems([
			"DD.MM.YYYY",  # Standard
			"MM.DD.YYYY",  # Stupid
			"YYYY.MM.DD",  # American
			"YYYY-MM-DD"  # American alternative
		])

		self.title_bar_combo_box.currentTextChanged.connect(self.title_bar_combo_box_text_changed)
		self.appearance_combo_box.currentTextChanged.connect(self.appearance_combo_box_text_changed)
		self.color_dialog_butt.clicked.connect(self.color_dialog_butt_clicked)
		self.blue_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#007BFF"))
		self.purple_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#5856D6"))
		self.pink_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#FF2D55"))
		self.red_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#FF3B30"))
		self.orange_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#FF9500"))
		self.yellow_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#FFCC00"))
		self.green_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#34C759"))
		self.graphite_color_butt.clicked.connect(lambda: self.accent_color_butt_clicked("#808080"))
		self.enable_logging_group_box.toggled.connect(self.enable_logging_check_box_toggled)
		self.enable_yt_dlp_logs_check_box.stateChanged.connect(self.enable_yt_dlp_logs_check_box_state_changed)
		self.enable_ffmpeg_logs_check_box.stateChanged.connect(self.enable_ffmpeg_logs_check_box_state_changed)
		self.enable_debug_logs_check_box.stateChanged.connect(self.enable_debug_logs_check_box_state_changed)
		self.choose_download_folder_butt.clicked.connect(self.choose_download_folder_butt_clicked)
		self.choose_ffmpeg_folder_butt.clicked.connect(self.choose_ffmpeg_folder_butt_clicked)

		self.color_butt_layout = QHBoxLayout()
		self.color_butt_layout.addWidget(self.color_dialog_butt)
		self.color_butt_layout.addWidget(self.blue_color_butt)
		self.color_butt_layout.addWidget(self.purple_color_butt)
		self.color_butt_layout.addWidget(self.pink_color_butt)
		self.color_butt_layout.addWidget(self.red_color_butt)
		self.color_butt_layout.addWidget(self.orange_color_butt)
		self.color_butt_layout.addWidget(self.yellow_color_butt)
		self.color_butt_layout.addWidget(self.green_color_butt)
		self.color_butt_layout.addWidget(self.graphite_color_butt)

		self.theme_layout = QVBoxLayout()
		self.theme_layout.addWidget(self.title_bar_combo_box)
		self.theme_layout.addWidget(self.appearance_combo_box)
		self.theme_layout.addLayout(self.color_butt_layout)
		self.theme_group_box.setLayout(self.theme_layout)

		self.logging_layout = QHBoxLayout()
		self.logging_layout.addWidget(self.enable_yt_dlp_logs_check_box)
		self.logging_layout.addWidget(self.enable_ffmpeg_logs_check_box)
		self.logging_layout.addWidget(self.enable_debug_logs_check_box)
		self.enable_logging_group_box.setLayout(self.logging_layout)

		self.folders_layout = QGridLayout()
		self.folders_layout.addWidget(self.download_folder_label, 0, 0)
		self.folders_layout.addWidget(self.choose_download_folder_butt, 0, 1)
		self.folders_layout.addWidget(self.ffmpeg_folder_label, 1, 0)
		self.folders_layout.addWidget(self.choose_ffmpeg_folder_butt, 1, 1)
		self.folders_group_box.setLayout(self.folders_layout)

		self.extra_download_layout = QVBoxLayout()
		self.extra_download_layout.addWidget(self.extra_download_video_check_box)
		self.extra_download_layout.addWidget(self.extra_download_audio_check_box)
		self.extra_download_layout.addWidget(self.extra_download_va_check_box)
		self.extra_download_group_box.setLayout(self.extra_download_layout)

		self.other_data_display_layout = QHBoxLayout()
		self.other_data_display_layout.addWidget(self.date_format_label)
		self.other_data_display_layout.addWidget(self.date_format_combo_box)
		self.other_data_display_layout.addSpacerItem(self.date_format_spacer)
		self.other_data_display_group_box.setLayout(self.other_data_display_layout)

		self.advanced_naming_layout = QVBoxLayout()
		self.advanced_naming_layout.addWidget(self.advanced_naming_uploader_check_box)
		self.advanced_naming_layout.addWidget(self.advanced_naming_resolution_check_box)
		self.advanced_naming_layout.addWidget(self.advanced_naming_playlist_check_box)
		self.advanced_naming_layout.addWidget(self.advanced_naming_playlist_index_check_box)
		self.advanced_naming_group_box.setLayout(self.advanced_naming_layout)

		self.quality_layout = QGridLayout()
		self.quality_layout.addWidget(self.video_quality_label, 0, 0)
		self.quality_layout.addWidget(self.video_quality_combo_box, 0, 1)
		self.quality_layout.addItem(self.video_quality_spacer, 0, 2)
		self.quality_layout.addWidget(self.audio_quality_label, 1, 0)
		self.quality_layout.addWidget(self.audio_quality_combo_box, 1, 1)
		self.quality_layout.addItem(self.audio_quality_spacer, 1, 2)
		self.quality_group_box.setLayout(self.quality_layout)

		self.video_finder_layout = QVBoxLayout()
		self.video_finder_layout.setContentsMargins(0, 0, 0, 0)
		self.video_finder_layout.addWidget(self.theme_group_box)
		self.video_finder_layout.addWidget(self.enable_logging_group_box)
		self.video_finder_layout.addWidget(self.folders_group_box)
		self.video_finder_layout.addWidget(self.extra_download_group_box)
		self.video_finder_layout.addWidget(self.other_data_display_group_box)
		self.video_finder_layout.addWidget(self.advanced_naming_group_box)
		self.video_finder_layout.addWidget(self.quality_group_box)

		###

		self.setLayout(self.video_finder_layout)

	def title_bar_combo_box_text_changed(self):
		log.debug(f"Changed type title bar to {self.title_bar_combo_box.currentText()}")
		self.title_bar_signal.emit()

	def appearance_combo_box_text_changed(self):
		setup_theme(theme=self.appearance_combo_box.currentText().lower(), custom_colors={"primary": program_data.settings["theme"]["color"]})
		log.debug(f"Changed theme to {self.appearance_combo_box.currentText()}")
		self.appearance_signal.emit()

	def color_dialog_butt_clicked(self):
		q_color = QColorDialog.getColor()
		if q_color.isValid():
			program_data.settings["theme"]["accent color"] = q_color.name()
			setup_theme(theme=self.appearance_combo_box.currentText().lower(), custom_colors={"primary": q_color.name()})
			log.debug(f"Changed accent color to {q_color.name()}")
			self.accent_color_signal.emit(q_color.name())

	def accent_color_butt_clicked(self, color):
		program_data.settings["theme"]["accent color"] = color
		setup_theme(theme=self.appearance_combo_box.currentText().lower(), custom_colors={"primary": color})
		log.debug(f"Changed accent color to {color}")
		self.accent_color_signal.emit(color)

	def enable_logging_check_box_toggled(self, state):
		if state:
			# Включаем обработчики
			log.warning("Logs is enabled")
			log.addHandler(file_handler)
			yt_dlp_log.addHandler(file_handler)
		else:
			# Отключаем обработчики
			log.warning("Logs is disabled")
			log.removeHandler(file_handler)
			yt_dlp_log.removeHandler(file_handler)

		self.enable_logging_signal.emit(state)

	def enable_yt_dlp_logs_check_box_state_changed(self, state):
		if state:
			# Включаем логирование yt_dlp
			log.warning("YT-DLP logger is enabled")
			yt_dlp_log.addHandler(file_handler)
		else:
			# Отключаем логирование yt_dlp
			log.warning("YT-DLP logger is disabled")
			yt_dlp_log.removeHandler(file_handler)

		self.enable_yt_dlp_logger_signal.emit(state)

	def enable_ffmpeg_logs_check_box_state_changed(self, state):
		# if state:
		# 	# Включаем логирование yt_dlp
		# 	log.warning("YT-DLP logger is enabled")
		# 	yt_dlp_log.addHandler(file_handler)
		# else:
		# 	# Отключаем логирование yt_dlp
		# 	log.warning("YT-DLP logger is disabled")
		# 	yt_dlp_log.removeHandler(file_handler)

		self.enable_ffmpeg_logger_signal.emit(state)

	def enable_debug_logs_check_box_state_changed(self, state):
		if state:
			# Устанавливаем уровень DEBUG для файлового обработчика
			log.warning("Logs levels set up to DEBUG")
			file_handler.setLevel(logging.DEBUG)
			status_handler.setLevel(logging.DEBUG)
		else:
			# Устанавливаем уровень INFO для файлового обработчика
			log.warning("Logs levels set up to INFO")
			file_handler.setLevel(logging.INFO)
			status_handler.setLevel(logging.INFO)

		self.enable_debug_logs_signal.emit(state)

	def choose_download_folder_butt_clicked(self):
		self.download_folder_label.setText(QFileDialog.getExistingDirectory(self, "Select download directory"))
		self.choose_download_folder_signal.emit()
		log.debug("Download directory is changed")

	def choose_ffmpeg_folder_butt_clicked(self):
		ffmpeg_path, _ = QFileDialog.getOpenFileName(self, "Select ffmpeg executable", ".", "App (*.exe)")
		if ffmpeg_path.split("/")[-1] == "ffmpeg.exe":
			self.ffmpeg_folder_label.setText(ffmpeg_path)
			self.choose_ffmpeg_folder_signal.emit()
			log.debug("FFmpeg directory is changed")
		else:
			log.error("This program is not FFmpeg")

class ProgressBarsWidget(QWidget):
	def __init__(self):
		super(ProgressBarsWidget, self).__init__()

		self.total_progress_bar = QProgressBar()
		self.unit_progress_bar = QProgressBar()

		self.progress_bars_layout = QVBoxLayout()
		self.progress_bars_layout.setContentsMargins(0, 0, 0, 0)
		self.progress_bars_layout.addWidget(self.total_progress_bar)
		self.progress_bars_layout.addWidget(self.unit_progress_bar)

		###

		self.setLayout(self.progress_bars_layout)

class VideoDataWidget(QWidget):
	pixmap_setted = pyqtSignal()

	def __init__(self):
		super(VideoDataWidget, self).__init__()

		self.thumbnail_label = QLabel()
		self.title_label = QLineEdit()
		self.description_label = QTextBrowser()
		self.duration_string_icon = QLabel()
		self.duration_string_label = QLabel()
		self.upload_date_icon = QLabel()
		self.upload_date_label = QLabel()
		self.view_count_icon = QLabel()
		self.view_count_label = QLabel()
		self.like_count_icon = QLabel()
		self.like_count_label = QLabel()
		self.uploader_icon = QLabel()
		self.uploader_label = QLabel()
		self.other_data_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

		self.thumbnail_label.setFixedSize(480, 270)
		self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.title_label.setMinimumWidth(400)
		self.description_label.setOpenExternalLinks(True)
		self.uploader_label.setOpenExternalLinks(True)  # Открытие ссылок в браузере
		self.uploader_label.setTextFormat(Qt.TextFormat.RichText)  # Поддержка HTML
		self.uploader_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)  # Включаем интерактивность

		self.__set_pixmap_content(self.duration_string_icon, "https://raw.githubusercontent.com/Nakama3942/NYT/706cc58797fae2b6869df4da31b054b1cd230fcd/icons/schedule_24dp.svg")
		self.__set_pixmap_content(self.upload_date_icon, "https://raw.githubusercontent.com/Nakama3942/NYT/706cc58797fae2b6869df4da31b054b1cd230fcd/icons/event_24dp.svg")
		self.__set_pixmap_content(self.view_count_icon, "https://raw.githubusercontent.com/Nakama3942/NYT/706cc58797fae2b6869df4da31b054b1cd230fcd/icons/visibility_24dp.svg")
		self.__set_pixmap_content(self.like_count_icon, "https://raw.githubusercontent.com/Nakama3942/NYT/706cc58797fae2b6869df4da31b054b1cd230fcd/icons/thumb_up_24dp.svg")
		self.__set_pixmap_content(self.uploader_icon, "https://raw.githubusercontent.com/Nakama3942/NYT/706cc58797fae2b6869df4da31b054b1cd230fcd/icons/video_camera_front_24dp.svg")

		self.video_description_layout = QVBoxLayout()
		self.video_description_layout.setContentsMargins(0, 0, 0, 0)
		self.video_description_layout.addWidget(self.description_label)
		self.video_description_widget = QWidget()
		self.video_description_widget.setLayout(self.video_description_layout)

		self.video_other_data_layout = QGridLayout()
		self.video_other_data_layout.addWidget(self.duration_string_icon, 0, 0)
		self.video_other_data_layout.addWidget(self.duration_string_label, 0, 1)
		self.video_other_data_layout.addWidget(self.upload_date_icon, 1, 0)
		self.video_other_data_layout.addWidget(self.upload_date_label, 1, 1)
		self.video_other_data_layout.addWidget(self.view_count_icon, 2, 0)
		self.video_other_data_layout.addWidget(self.view_count_label, 2, 1)
		self.video_other_data_layout.addWidget(self.like_count_icon, 2, 2)
		self.video_other_data_layout.addWidget(self.like_count_label, 2, 3)
		self.video_other_data_layout.addWidget(self.uploader_icon, 3, 0)
		self.video_other_data_layout.addWidget(self.uploader_label, 3, 1)
		self.video_other_data_layout.addItem(self.other_data_spacer, 4, 0)
		self.video_other_data_widget = QWidget()
		self.video_other_data_widget.setLayout(self.video_other_data_layout)

		self.video_data_tab_widget = QTabWidget()
		self.video_data_tab_widget.addTab(self.video_description_widget, "Description")
		self.video_data_tab_widget.addTab(self.video_other_data_widget, "Other data")

		self.video_data_layout = QVBoxLayout()
		self.video_data_layout.setContentsMargins(0, 0, 0, 0)
		self.video_data_layout.addWidget(self.thumbnail_label)
		self.video_data_layout.addWidget(self.title_label)
		self.video_data_layout.addWidget(self.video_data_tab_widget)

		###

		self.setLayout(self.video_data_layout)

	def __set_pixmap_content(self, pixmap_container: QLabel, link):
		response = get(link)
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio)
			pixmap_container.setPixmap(pixmap)
			pixmap_container.setFixedWidth(26)
			self.pixmap_setted.emit()
		else:
			log.warning("Image loading failed")

class DownloadButtWidget(QWidget):
	def __init__(self):
		super(DownloadButtWidget, self).__init__()

		self.download_metadata_butt = QPushButton("Save metadata (JSON)")
		self.download_video_butt = QPushButton("Download MP4")
		self.download_audio_butt = QPushButton("Download MP3")
		self.download_all_butt = QPushButton("Download MP4+MP3")
		self.skip_butt = QPushButton("Skip video")
		self.finish_butt = QPushButton("Finish playlist")

		self.finish_butt.setEnabled(False)

		self.download_butt_layout = QHBoxLayout()
		self.download_butt_layout.addWidget(self.download_video_butt)
		self.download_butt_layout.addWidget(self.download_audio_butt)
		self.download_butt_layout.addWidget(self.download_all_butt)

		self.skip_butt_layout = QHBoxLayout()
		self.skip_butt_layout.addWidget(self.skip_butt)
		self.skip_butt_layout.addWidget(self.finish_butt)

		self.main_layout = QVBoxLayout()
		self.main_layout.setContentsMargins(0, 0, 0, 0)
		self.main_layout.addWidget(self.download_metadata_butt)
		self.main_layout.addLayout(self.download_butt_layout)
		self.main_layout.addLayout(self.skip_butt_layout)

		###

		self.setLayout(self.main_layout)

class ExtractAudioButtWidget(QWidget):
	def __init__(self):
		super(ExtractAudioButtWidget, self).__init__()

		self.extract_specified_audio_butt = QPushButton("From specified .mp4 files")
		self.extract_all_audio_in_specified_dir_butt = QPushButton("From all .mp4 files in specified directory")
		self.extract_all_audio_butt = QPushButton("From all .mp4 files in this directory")
		self.extract_progress_bar = QProgressBar()

		self.extract_audio_butt_widget_layout = QVBoxLayout()
		self.extract_audio_butt_widget_layout.setContentsMargins(0, 0, 0, 0)
		self.extract_audio_butt_widget_layout.addWidget(self.extract_specified_audio_butt)
		self.extract_audio_butt_widget_layout.addWidget(self.extract_all_audio_in_specified_dir_butt)
		self.extract_audio_butt_widget_layout.addWidget(self.extract_all_audio_butt)
		self.extract_audio_butt_widget_layout.addWidget(self.extract_progress_bar)

		###

		self.setLayout(self.extract_audio_butt_widget_layout)

class VideoSearcherWidget(QWidget):
	def __init__(self):
		super(VideoSearcherWidget, self).__init__()

		self.url_line_edit = QLineEdit()
		self.find_video_butt = QPushButton("Find video")

		self.url_line_edit.setPlaceholderText("Enter the video or playlist URL/ID")
		self.url_line_edit.setText("https://www.youtube.com/watch?v=nSFfpEznkF8")
		# self.url_line_edit.setText("https://www.youtube.com/playlist?list=PL2MbnZfZV5Ksz3V1TABFnBiEXDjK4RqKM")
		# self.url_line_edit.setText("https://www.youtube.com/watch?v=nSFfpEznkF8&list=PL2MbnZfZV5Ksz3V1TABFnBiEXDjK4RqKM&index=3")

		self.video_searcher_layout = QVBoxLayout()
		self.video_searcher_layout.setContentsMargins(0, 0, 0, 0)
		self.video_searcher_layout.addWidget(self.url_line_edit)
		self.video_searcher_layout.addWidget(self.find_video_butt)

		###

		self.setLayout(self.video_searcher_layout)

class TitleBarWidget(QWidget):
	is_moving = False
	mouse_start = None
	window_start = None

	def __init__(self, parent):
		super(TitleBarWidget, self).__init__(parent)

		self.parent = parent

		self.program_name = QLineEdit("NYT: © 2024 Kalynovsky Valentin")
		self.exit_butt = QPushButton("✗")

		self.program_name.setEnabled(False)
		self.program_name.setStyleSheet("""
			QLineEdit {
				background-color: rgba(63, 64, 66, 0.4);
				color: #fff;
				border: 0px;
				border-radius: 10px;
				font-size: 16px;
			}
		""")
		self.program_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		self.exit_butt.setFixedSize(40, 30)
		self.exit_butt.setStyleSheet(custom_but_qss_preparing([255, 59, 48]))
		self.exit_butt.clicked.connect(self.exit_butt_clicked)

		# Перенаправление событий мыши с вложенного виджета в заголовок
		self.program_name.mousePressEvent = self.mousePressEvent
		self.program_name.mouseMoveEvent = self.mouseMoveEvent
		self.program_name.mouseReleaseEvent = self.mouseReleaseEvent

		self.title_bar_layout = QHBoxLayout()
		self.title_bar_layout.setContentsMargins(0, 0, 0, 0)
		self.title_bar_layout.addWidget(self.program_name)
		self.title_bar_layout.addWidget(self.exit_butt)

		###

		self.setLayout(self.title_bar_layout)

	def exit_butt_clicked(self):
		self.parent.close()

	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self.is_moving = True
			self.mouse_start = event.globalPosition().toPoint()  # Начальная позиция курсора
			self.window_start = self.parent.frameGeometry().topLeft()  # Начальная позиция окна

	def mouseMoveEvent(self, event):
		if self.is_moving:
			# Вычисляем смещение и перемещаем окно
			delta = event.globalPosition().toPoint() - self.mouse_start
			self.parent.move(self.window_start + delta)

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self.is_moving = False  # Прекращаем перемещение

class NYTDialogWindow(QMainWindow):
	def __init__(self):
		super(NYTDialogWindow, self).__init__()

		log.debug("Initialization started")

		self.video_metadata = None
		self.playlist_metadata = None
		self.playlist_flag = False
		self.standard_quality = 144
		status_handler.log_signal.connect(self.__set_status)

		program_data.load_settings()
		program_data.load_cache()

		#####

		self.settings_widget = SettingsWidget()
		self.settings_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

		self.settings_widget.date_format_combo_box.setCurrentIndex(program_data.settings["other video data settings"]["data format"])
		self.settings_widget.enable_logging_group_box.setChecked(program_data.settings["logging"]["enable logging"])
		self.settings_widget.enable_yt_dlp_logs_check_box.setChecked(program_data.settings["logging"]["enable yt-dlp logs"])
		self.settings_widget.enable_ffmpeg_logs_check_box.setChecked(program_data.settings["logging"]["enable ffmpeg logs"])
		self.settings_widget.enable_debug_logs_check_box.setChecked(program_data.settings["logging"]["enable debug logs"])
		self.settings_widget.advanced_naming_group_box.setChecked(program_data.settings["advanced naming"]["advanced naming"])
		self.settings_widget.advanced_naming_uploader_check_box.setChecked(program_data.settings["advanced naming"]["advanced naming uploader"])
		self.settings_widget.advanced_naming_resolution_check_box.setChecked(program_data.settings["advanced naming"]["advanced naming resolution"])
		self.settings_widget.advanced_naming_playlist_check_box.setChecked(program_data.settings["advanced naming"]["advanced naming playlist"])
		self.settings_widget.advanced_naming_playlist_index_check_box.setChecked(program_data.settings["advanced naming"]["advanced naming playlist index"])

		if program_data.settings["folders"]["download folder"]:
			self.settings_widget.download_folder_label.setText(program_data.settings["folders"]["download folder"])
			self.settings_widget.ffmpeg_folder_label.setText(program_data.settings["folders"]["ffmpeg folder"])

		self.settings_widget.title_bar_combo_box.currentTextChanged.connect(self.title_bar_combo_box_current_text_changed)
		self.settings_widget.date_format_combo_box.currentTextChanged.connect(self.date_format_combo_box_current_text_changed)

		self.settings_group_box_layout = QVBoxLayout()
		self.settings_group_box_layout.addWidget(self.settings_widget)
		self.settings_group_box_layout.addSpacerItem(self.settings_spacer)

		self.settings_group_box = QGroupBox("Settings")
		self.settings_group_box.setFixedWidth(500)
		self.settings_group_box.setLayout(self.settings_group_box_layout)

		###

		self.extract_audio_butt_widget = ExtractAudioButtWidget()

		self.extract_audio_butt_widget.extract_specified_audio_butt.clicked.connect(self.extract_specified_audio_butt_clicked)
		self.extract_audio_butt_widget.extract_all_audio_in_specified_dir_butt.clicked.connect(self.extract_all_audio_in_specified_dir_butt_clicked)
		self.extract_audio_butt_widget.extract_all_audio_butt.clicked.connect(lambda: self.extract_all_audio_butt_clicked())

		self.extract_layout = QVBoxLayout()
		self.extract_layout.addWidget(self.extract_audio_butt_widget)

		self.extract_group_box = QGroupBox("Extract audio")
		self.extract_group_box.setFixedWidth(500)
		self.extract_group_box.setLayout(self.extract_layout)

		###

		self.video_searcher_widget = VideoSearcherWidget()
		self.video_metadata_widget = VideoDataWidget()

		self.video_searcher_widget.find_video_butt.clicked.connect(self.find_video_butt_clicked)
		self.video_metadata_widget.title_label.textChanged.connect(self.title_label_text_changed)

		self.video_metadata_layout = QVBoxLayout()
		self.video_metadata_layout.addWidget(self.video_searcher_widget)
		self.video_metadata_layout.addWidget(self.video_metadata_widget)

		self.video_metadata_group_box = QGroupBox("Video")
		self.video_metadata_group_box.setLayout(self.video_metadata_layout)
		self.video_metadata_group_box.setFixedWidth(500)

		###

		self.download_butt_widget = DownloadButtWidget()
		self.download_progress_bars_widget = ProgressBarsWidget()

		self.download_butt_widget.download_metadata_butt.clicked.connect(self.download_metadata_butt_clicked)
		self.download_butt_widget.download_video_butt.clicked.connect(self.download_video_butt_clicked)
		self.download_butt_widget.download_audio_butt.clicked.connect(self.download_audio_butt_clicked)
		self.download_butt_widget.download_all_butt.clicked.connect(self.download_all_butt_clicked)
		self.download_butt_widget.skip_butt.clicked.connect(self.skip_butt_clicked)
		self.download_butt_widget.finish_butt.clicked.connect(self.finish_butt_clicked)

		self.download_layout = QVBoxLayout()
		self.download_layout.addWidget(self.download_butt_widget)
		self.download_layout.addWidget(self.download_progress_bars_widget)

		self.download_group_box = QGroupBox("Download")
		self.download_group_box.setFixedWidth(500)
		self.download_group_box.setLayout(self.download_layout)

		#####

		# Dialog window customization

		self.title_bar = TitleBarWidget(self)

		self.status_bar = QStatusBar()

		self.left_half_main_layout = QVBoxLayout()
		self.left_half_main_layout.addWidget(self.settings_group_box)
		self.left_half_main_layout.addWidget(self.extract_group_box)

		self.right_half_main_layout = QVBoxLayout()
		self.right_half_main_layout.addWidget(self.video_metadata_group_box)
		self.right_half_main_layout.addWidget(self.download_group_box)

		self.main_layout = QHBoxLayout()
		self.main_layout.addLayout(self.left_half_main_layout)
		self.main_layout.addLayout(self.right_half_main_layout)

		self.central_layout = QVBoxLayout()
		self.central_layout.addWidget(self.title_bar)
		self.central_layout.addLayout(self.main_layout)

		self.central_widget = QWidget()
		self.central_widget.setLayout(self.central_layout)

		self.__init_about_screen()

		self.__set_title_bar_name("© 2024 Kalynovsky Valentin")
		self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
		self.setCentralWidget(self.central_widget)
		self.setStatusBar(self.status_bar)

		self.settings_widget.title_bar_combo_box.setCurrentIndex(program_data.settings["theme"]["title bar"])
		self.settings_widget.appearance_combo_box.setCurrentIndex(program_data.settings["theme"]["theme"])
		self.title_bar_combo_box_current_text_changed(self.settings_widget.title_bar_combo_box.currentText())
		setup_theme(theme=self.settings_widget.appearance_combo_box.currentText().lower(), custom_colors={"primary": program_data.settings["theme"]["accent color"]})

		log.debug("Interface was initialized")

		#####

		self.loader = Loader()
		self.loader.founded.connect(self.loader_founded)
		self.loader.updated.connect(self.loader_updated)
		self.loader.extracted.connect(self.loader_extracted)
		self.loader.start_download.connect(self.loader_start_download)
		self.loader.finish_download.connect(self.loader_finish_download)

		log.debug("Loader was initialized")

		log.debug("Initialization finished")
		log.info("The program has been launched")

	def loader_founded(self, metadata: dict):
		self.download_progress_bars_widget.unit_progress_bar.setRange(0, 100)
		if not metadata["id"] in program_data.cache.keys():
			metadata = convert_http_header_to_dict(metadata)
			program_data.cache[metadata["id"]] = metadata

		if "_type" in metadata and metadata["_type"] == "playlist":
			log.debug("Playlist metadata was intercepted")
			self.playlist_metadata = {"video": [entry['id'] for entry in metadata['entries']], "counter": 0}
			self.download_progress_bars_widget.total_progress_bar.setMaximum(len(self.playlist_metadata["video"]))
			self.download_progress_bars_widget.total_progress_bar.setValue(0)
			self.download_progress_bars_widget.unit_progress_bar.setValue(0)
			self.video_searcher_widget.url_line_edit.setText(self.playlist_metadata["video"][self.playlist_metadata["counter"]])
			self.download_butt_widget.finish_butt.setEnabled(True)
			self.find_video_butt_clicked()
		else:
			log.debug("Video metadata was intercepted")
			self.video_metadata = deepcopy(metadata)

			resolutions = sorted(
				set(
					fmt["format_note"] for fmt in self.video_metadata["formats"]
					if "format_note" in fmt
						and fmt["format_note"].endswith("p")
						and fmt["format_note"][:-1].isdigit()
						and fmt["ext"] == "mp4"
				),
				key=lambda r: int(r.replace("p", "")),
				reverse=True
			)
			self.settings_widget.video_quality_combo_box.clear()
			self.settings_widget.video_quality_combo_box.addItems(resolutions)
			self.settings_widget.video_quality_combo_box.setCurrentText(resolutions[0] if int(resolutions[0].replace("p", "")) <= self.standard_quality else f"{self.standard_quality}p")

			audio_quality = sorted(
				set(
					f"{fmt['tbr']} kbps" for fmt in self.video_metadata["formats"]
					if "tbr" in fmt and fmt["ext"] == "m4a"
				),
				key=lambda r: float(r.replace(" kbps", "")),
				reverse=True
			)
			log.debug(audio_quality)
			self.settings_widget.audio_quality_combo_box.clear()
			self.settings_widget.audio_quality_combo_box.addItems(audio_quality)

			self.__insert_video_metadata()
			self.__change_download_butt_enabling(True)

			if not self.video_metadata_widget.video_data_tab_widget.isTabVisible(1):
				self.video_metadata_widget.video_data_tab_widget.setTabVisible(1, True)
			if self.settings_widget.extra_download_video_check_box.isChecked():
				self.download_video_butt_clicked()
			elif self.settings_widget.extra_download_audio_check_box.isChecked():
				self.download_audio_butt_clicked()
			elif self.settings_widget.extra_download_va_check_box.isChecked():
				self.download_all_butt_clicked()
			else:
				self.download_butt_widget.setEnabled(True)

	def loader_updated(self, max_percent, current_percent):
		self.download_progress_bars_widget.unit_progress_bar.setMaximum(max_percent)
		self.download_progress_bars_widget.unit_progress_bar.setValue(current_percent)

	def loader_extracted(self):
		self.extract_audio_butt_widget.extract_progress_bar.setValue(self.extract_audio_butt_widget.extract_progress_bar.value() + 1)

	def loader_start_download(self):
		self.download_butt_widget.setEnabled(False)

	def loader_finish_download(self):
		self.video_searcher_widget.setVisible(True)

		def clear_window():
			self.__set_title_bar_name("© 2024 Kalynovsky Valentin")
			self.settings_widget.extra_download_video_check_box.setChecked(False)
			self.settings_widget.extra_download_audio_check_box.setChecked(False)
			self.settings_widget.extra_download_va_check_box.setChecked(False)
			self.settings_widget.video_quality_combo_box.clear()
			self.settings_widget.audio_quality_combo_box.clear()
			self.settings_widget.video_quality_combo_box.addItem("unknown")
			self.settings_widget.audio_quality_combo_box.addItem("unknown")
			self.video_metadata_widget.video_data_tab_widget.setTabVisible(1, False)
			self.video_searcher_widget.url_line_edit.clear()
			self.__init_about_screen()

		if self.playlist_flag:
			self.playlist_metadata["counter"] += 1
			self.download_progress_bars_widget.total_progress_bar.setValue(self.playlist_metadata["counter"])
			if self.playlist_metadata["counter"] == len(self.playlist_metadata["video"]):
				self.playlist_flag = False
				self.download_butt_widget.finish_butt.setEnabled(False)
				clear_window()
			else:
				self.video_searcher_widget.url_line_edit.setText(self.playlist_metadata["video"][self.playlist_metadata["counter"]])
				self.find_video_butt_clicked()
		else:
			clear_window()

	def title_bar_combo_box_current_text_changed(self, new_text):
		if new_text == "Custom title bar":
			self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
			# self.central_widget.setStyleSheet("border: 1px solid #ccc; border-radius: 15px;")  # Funny Easter egg
			self.title_bar.setVisible(True)
		else:
			self.setWindowFlags(Qt.WindowType.Window)
			self.title_bar.setVisible(False)

		self.show()

	def date_format_combo_box_current_text_changed(self, new_text):
		if self.video_metadata_widget.upload_date_label.text():
			self.video_metadata_widget.upload_date_label.setText(self.video_metadata['upload_date'][new_text])

	def find_video_butt_clicked(self):
		self.download_progress_bars_widget.unit_progress_bar.setRange(0, 0)
		self.download_progress_bars_widget.unit_progress_bar.setValue(0)
		if self.__analyze_link():
			if self.video_searcher_widget.url_line_edit.text() in program_data.cache.keys():
				log.debug("Loaded cached data")
				self.loader_founded(program_data.cache[self.video_searcher_widget.url_line_edit.text()])
			else:
				if self.playlist_flag:
					log.debug(self.video_searcher_widget.url_line_edit.text())
					self.loader.submit_find_playlist(
						self.video_searcher_widget.url_line_edit.text()
					)
				else:
					log.debug(self.video_searcher_widget.url_line_edit.text())
					self.loader.submit_find_video(
						self.video_searcher_widget.url_line_edit.text()
					)

	def title_label_text_changed(self):
		self.__set_title_bar_name(self.video_metadata_widget.title_label.text())

	def download_metadata_butt_clicked(self):
		with open(f"{self.video_metadata_widget.title_label.text()}.json", "w", encoding="utf-8") as json_file:
			json.dump(self.video_metadata, json_file, indent=4)
			log.debug(f"Video metadata saved to '{self.video_metadata_widget.title_label.text()}.json'")

	def download_video_butt_clicked(self):
		self.__change_download_butt_enabling(False)
		self.video_searcher_widget.setVisible(False)
		formatted_name = self.__file_name_preparing()
		log.debug(f"Starting saved file '{formatted_name}'")
		self.loader.submit_download_video(
			self.video_metadata["id"],
			formatted_name,
			[fmt["format_id"] for fmt in self.video_metadata["formats"] if fmt.get("format_note") == self.settings_widget.video_quality_combo_box.currentText() and fmt.get("ext") == "mp4"][0],
			self.settings_widget.audio_quality_combo_box.currentText().replace(" kbps", "")
		)

	def download_audio_butt_clicked(self):
		self.__change_download_butt_enabling(False)
		self.video_searcher_widget.setVisible(False)
		formatted_name = self.__file_name_preparing()
		log.debug(f"Starting saved audio file '{formatted_name}'")
		self.loader.submit_download_audio(
			self.video_metadata["id"],
			formatted_name,
			self.settings_widget.audio_quality_combo_box.currentText().replace(" kbps", "")
		)

	def download_all_butt_clicked(self):
		self.__change_download_butt_enabling(False)
		self.video_searcher_widget.setVisible(False)
		formatted_name = self.__file_name_preparing()
		log.debug(f"Starting saved video and audio file '{formatted_name}'")
		self.loader.submit_download_va(
			self.video_metadata["id"],
			formatted_name,
			[fmt["format_id"] for fmt in self.video_metadata["formats"] if fmt.get("format_note") == self.settings_widget.video_quality_combo_box.currentText() and fmt.get("ext") == "mp4"][0],
			self.settings_widget.audio_quality_combo_box.currentText().replace(" kbps", "")
		)

	def skip_butt_clicked(self):
		self.loader_start_download()
		self.loader_updated(1, 1)
		self.loader_finish_download()

	def finish_butt_clicked(self):
		self.playlist_metadata["counter"] = len(self.playlist_metadata["video"]) - 1
		self.loader_finish_download()

	def extract_specified_audio_butt_clicked(self):
		# Открытие диалога выбора файла
		file_names, _ = QFileDialog.getOpenFileNames(self, "Choose the video", self.settings_widget.download_folder_label.text(), "Video (*.mp4)")
		if file_names:
			self.__run_extract_audio(file_names)
		else:
			log.warning("No files selected")

	def extract_all_audio_in_specified_dir_butt_clicked(self):
		# Открываем диалог для выбора директории
		selected_dir = QFileDialog.getExistingDirectory(self, "Choose the directory with video")
		if selected_dir:
			# Получаем список всех файлов в выбранной директории
			file_names = [path.join(selected_dir, video_file) for video_file in listdir(selected_dir) if video_file.endswith(".mp4")]
			if file_names:
				self.__run_extract_audio(file_names)
			else:
				log.warning("In chosen directory not video")

	def extract_all_audio_butt_clicked(self):
		# Получаем список всех файлов в выбранной директории
		file_names = [video_file for video_file in listdir() if video_file.endswith(".mp4")]
		if file_names:
			self.__run_extract_audio(file_names)
		else:
			log.warning("In current directory not video")

	def __file_name_preparing(self):
		formatted_file_name = f"{self.settings_widget.download_folder_label.text()}/"
		if self.settings_widget.advanced_naming_group_box.isChecked():
			formatted_file_name += f"[%(id)s] - {self.video_metadata_widget.title_label.text()}"
			if self.settings_widget.advanced_naming_uploader_check_box.isChecked():
				formatted_file_name += " - %(uploader)s"
			if self.settings_widget.advanced_naming_resolution_check_box.isChecked():
				formatted_file_name += " - %(resolution)s"
			if self.settings_widget.advanced_naming_playlist_check_box.isChecked():
				formatted_file_name += " - %(playlist)s"
			if self.settings_widget.advanced_naming_playlist_index_check_box.isChecked():
				formatted_file_name += " - %(playlist_index)s"
			formatted_file_name += ".%(ext)s"
		else:
			formatted_file_name += f"{self.video_metadata_widget.title_label.text()}.%(ext)s"

		return formatted_file_name

	def __run_extract_audio(self, file_names):
		self.extract_audio_butt_widget.extract_progress_bar.setMaximum(len(file_names))
		self.extract_audio_butt_widget.extract_progress_bar.setValue(0)
		if self.settings_widget.ffmpeg_folder_label.text() != "":
			self.loader.submit_extract_audio(
				file_names,
				self.settings_widget.ffmpeg_folder_label.text(),
				self.settings_widget.enable_ffmpeg_logs_check_box.isChecked()
			)
		else:
			log.error("FFmpeg not found")

	def __init_about_screen(self):
		response = get("https://gravatar.com/avatar/958ee1c4f59712e46351f051f86c9031?size=256")
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			pixmap = pixmap.scaled(270, 270, Qt.AspectRatioMode.KeepAspectRatio)
			self.video_metadata_widget.thumbnail_label.setPixmap(pixmap)
		else:
			log.warning("Image loading failed")

		self.video_metadata_widget.title_label.setText("Nakama's Youtube Tools")
		self.video_metadata_widget.description_label.setHtml(description)
		self.video_metadata_widget.video_data_tab_widget.setTabVisible(1, False)
		self.__change_download_butt_enabling(False)

	def __change_download_butt_enabling(self, state):
		self.download_butt_widget.setEnabled(state)
		self.video_metadata_widget.title_label.setReadOnly(not state)

	def __set_status(self, message):
		self.status_bar.showMessage(message)

	def __set_title_bar_name(self, title):
		self.setWindowTitle(f"NYT: {title}")
		self.title_bar.program_name.setText(f"NYT: {title}")

	def __analyze_link(self) -> bool:
		if "http" in self.video_searcher_widget.url_line_edit.text():

			if "www.youtube.com" in self.video_searcher_widget.url_line_edit.text():

				if self.video_searcher_widget.url_line_edit.text().split("?")[0].split("/")[-1] == "playlist":
					self.video_searcher_widget.url_line_edit.setText(self.video_searcher_widget.url_line_edit.text().split("?")[1].split("&")[0].split("=")[1])
					self.playlist_flag = True
					return True

				elif self.video_searcher_widget.url_line_edit.text().split("?")[0].split("/")[-1] == "watch":
					self.video_searcher_widget.url_line_edit.setText(self.video_searcher_widget.url_line_edit.text().split("?")[1].split("&")[0].split("=")[1])
					return True

				else:
					log.error("Entered the not correct youtube link")
					return False

			else:
				log.error("Entered the unknown link")
				return False

		else:
			log.info("Entered video/playlist ID")
			if len(self.video_searcher_widget.url_line_edit.text()) > 20:
				self.playlist_flag = True
			return True

	def __insert_video_metadata(self):
		response = get(self.video_metadata['thumbnail'])
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			pixmap = pixmap.scaled(480, 270, Qt.AspectRatioMode.KeepAspectRatio)  # 640*320, 480*270
			self.video_metadata_widget.thumbnail_label.setPixmap(pixmap)
		else:
			log.warning("Image loading failed")

		udload_video_date = datetime.strptime(self.video_metadata['upload_date'], "%Y%m%d")
		self.video_metadata['upload_date'] = {
			"DD.MM.YYYY": udload_video_date.strftime("%d.%m.%Y"),
			"MM.DD.YYYY": udload_video_date.strftime("%m.%d.%Y"),
			"YYYY.MM.DD": udload_video_date.strftime("%Y.%m.%d"),
			"YYYY-MM-DD": udload_video_date.strftime("%Y-%m-%d")
		}

		def unicode_safe(suspicious_line):
			# Карта замен символов
			char_map = {
				"|": "｜",  # U+FF5C FULLWIDTH VERTICAL LINE
				":": "꞉",  # U+A789 MODIFIER LETTER COLON
				"/": "／",  # U+FF0F FULLWIDTH SOLIDUS
				"\\": "＼",  # U+FF3C FULLWIDTH REVERSE SOLIDUS
				"?": "？",  # U+FF1F FULLWIDTH QUESTION MARK
				"*": "＊",  # U+FF0A FULLWIDTH ASTERISK
				"<": "＜",  # U+FF1C FULLWIDTH LESS-THAN SIGN
				">": "＞",  # U+FF1E FULLWIDTH GREATER-THAN SIGN
				'"': "＂",  # U+FF02 FULLWIDTH QUOTATION MARK
				"+": "＋",  # U+FF0B FULLWIDTH PLUS SIGN
				"#": "＃",  # U+FF03 FULLWIDTH NUMBER SIGN
			}

			# Создаём регулярное выражение на основе ключей char_map
			# Например: r"[|:/\\?*<>\"+#]"
			pattern = re.compile(f"[{''.join(map(re.escape, char_map.keys()))}]")

			# Проверяем, содержит ли suspicious_line недопустимые символы
			if pattern.search(suspicious_line):
				# Если содержит, производим замену
				for char, replacement in char_map.items():
					suspicious_line = suspicious_line.replace(char, replacement)
			return suspicious_line

		self.video_metadata['title'] = unicode_safe(self.video_metadata['title'])

		self.__set_title_bar_name(self.video_metadata['title'])

		self.video_metadata_widget.title_label.setText(self.video_metadata['title'])
		self.video_metadata_widget.description_label.setPlainText(self.video_metadata['description'])
		self.video_metadata_widget.duration_string_label.setText(self.video_metadata['duration_string'])
		self.video_metadata_widget.upload_date_label.setText(self.video_metadata['upload_date'][self.settings_widget.date_format_combo_box.currentText()])
		self.video_metadata_widget.view_count_label.setText(str(self.video_metadata['view_count']))
		self.video_metadata_widget.like_count_label.setText(str(self.video_metadata['like_count']))
		self.video_metadata_widget.uploader_label.setText(f"<a href='{self.video_metadata['channel_url']}'>{self.video_metadata['uploader']}</a> ({self.video_metadata['channel_follower_count']} subscribes)")

		log.debug("Video metadata was setted")

	# def show(self):
	# 	# Set window to center
	# 	qr = self.frameGeometry()
	# 	qr.moveCenter(self.screen().availableGeometry().center())
	# 	self.move(qr.topLeft())
	# 	# IMPORTANT_DATA.window_height = self.height()
	# 	# IMPORTANT_DATA.window_width = self.width()
	# 	super().show()

	def closeEvent(self, event):
		program_data.settings["theme"]["title bar"] = self.settings_widget.title_bar_combo_box.currentIndex()
		program_data.settings["theme"]["theme"] = self.settings_widget.appearance_combo_box.currentIndex()
		program_data.settings["logging"]["enable logging"] = self.settings_widget.enable_logging_group_box.isChecked()
		program_data.settings["logging"]["enable yt-dlp logs"] = self.settings_widget.enable_yt_dlp_logs_check_box.isChecked()
		program_data.settings["logging"]["enable ffmpeg logs"] = self.settings_widget.enable_ffmpeg_logs_check_box.isChecked()
		program_data.settings["logging"]["enable debug logs"] = self.settings_widget.enable_debug_logs_check_box.isChecked()
		program_data.settings["folders"]["download folder"] = self.settings_widget.download_folder_label.text()
		program_data.settings["folders"]["ffmpeg folder"] = self.settings_widget.ffmpeg_folder_label.text()
		program_data.settings["other video data settings"]["data format"] = self.settings_widget.date_format_combo_box.currentIndex()
		program_data.settings["advanced naming"]["advanced naming"] = self.settings_widget.advanced_naming_group_box.isChecked()
		program_data.settings["advanced naming"]["advanced naming uploader"] = self.settings_widget.advanced_naming_uploader_check_box.isChecked()
		program_data.settings["advanced naming"]["advanced naming resolution"] = self.settings_widget.advanced_naming_resolution_check_box.isChecked()
		program_data.settings["advanced naming"]["advanced naming playlist"] = self.settings_widget.advanced_naming_playlist_check_box.isChecked()
		program_data.settings["advanced naming"]["advanced naming playlist index"] = self.settings_widget.advanced_naming_playlist_index_check_box.isChecked()
		program_data.save_settings()
		program_data.save_cache()

		log.info("The program is closed")
		super().closeEvent(event)

if __name__ == '__main__':
	app = QApplication(sys.argv)
	ui = NYTDialogWindow()
	ui.show()
	sys.exit(app.exec())
