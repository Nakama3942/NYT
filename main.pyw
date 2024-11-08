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
from os import listdir, getcwd, rename, path
from subprocess import run, CalledProcessError
from requests import get
from datetime import datetime
import logging
import re

from concurrent.futures import ThreadPoolExecutor

from yt_dlp import YoutubeDL
import json

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QCheckBox, QProgressBar, QComboBox, QPushButton, QPlainTextEdit, QSpacerItem, QMessageBox, QStatusBar, QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QObject, pyqtSignal

class DownloadFilter(logging.Filter):
	def filter(self, record):
		# Проверяем наличие текста '[download]' в сообщении
		if any(substring in record.getMessage() for substring in ["[download]", "[ExtractAudio]"]):
			# Устанавливаем уровень на INFO для таких сообщений
			record.levelno = logging.INFO
			record.levelname = 'INFO'
		return True

# Настройка логирования

# Формат логов, который включает имя логгера
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)
console_handler.addFilter(DownloadFilter())

# Обработчик для записи в файл
file_handler = logging.FileHandler('NYT.log', encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
file_handler.addFilter(DownloadFilter())

# Настройка основного логгера программы (nyt)
log = logging.getLogger("nyt")
log.setLevel(logging.DEBUG)
log.addHandler(console_handler)
log.addHandler(file_handler)

# Настройка логгера для yt_dlp
yt_dlp_log = logging.getLogger("yt_dlp")
yt_dlp_log.setLevel(logging.DEBUG)
yt_dlp_log.addHandler(console_handler)
yt_dlp_log.addHandler(file_handler)

# todo
#  1. Реализовать остановку екстра-режима
#  2. Сделать больше логирования
#  3. Проверить загрузку из других источников (например, твиттера)
#  4. В настройках логирования добавить выключение логов ffmpeg и реализовать их запись в файл
#  5. Добавить настройку указания пути к ffmpeg
#  6. Поработать над интерфейсом программы
#  7. Провести рефакторинг кода
#  8. Добавить анимацию ожидания поиска
#  9. Добавить кнопку загрузки и видео, и аудио вместе

class Loader(QObject):
	founded = pyqtSignal(dict)
	updated = pyqtSignal(int, int, str)
	messaged = pyqtSignal(str)
	extracted = pyqtSignal()
	start_download = pyqtSignal()
	finish_download = pyqtSignal()

	def __init__(self):
		super(Loader, self).__init__()
		self.__executor = ThreadPoolExecutor(max_workers=10)

	def submit_find_playlist(self, playlist_url):
		future = self.__executor.submit(self.__get_playlist_metadata, playlist_url)
		future.add_done_callback(self.__internal_done_callback)

	def submit_find_video(self, video_url):
		future = self.__executor.submit(self.__get_video_metadata, video_url)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_video(self, video_url, video_title, video_format):
		future = self.__executor.submit(self.__download_video, video_url, video_title, video_format)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_audio(self, video_url, video_title):
		future = self.__executor.submit(self.__download_audio, video_url, video_title)
		future.add_done_callback(self.__internal_done_callback)

	def submit_extract_specified_audio(self, filenames, enable_logging):
		future = self.__executor.submit(self.__extract_specified_audio, filenames, enable_logging)
		future.add_done_callback(self.__internal_done_callback)

	def submit_extract_all_audio(self, enable_logging):
		future = self.__executor.submit(self.__extract_all_audio, enable_logging)
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

	def __download_video(self, video_url, video_title, video_format):
		self.start_download.emit()
		ydl_opts = {
			"format": f"{video_format}+ba[ext=m4a]",
			"quiet": False,
			"outtmpl": video_title,
			"progress_hooks": [self.__update_emitter],
			"logger": yt_dlp_log
		}
		try:
			with YoutubeDL(ydl_opts) as ydl:
				ydl.download([video_url])
				self.__message_emitter("[+] Video from playlist has been downloaded")
		except Exception as err:
			self.__message_emitter(f"[✗] ERROR: Downloading error {err}")
		self.finish_download.emit()

	def __download_audio(self, video_url, video_title):
		self.start_download.emit()
		ydl_opts = {
			"format": "bestaudio/best",
			"quiet": False,
			"outtmpl": video_title,
			"progress_hooks": [self.__update_emitter],
			"logger": yt_dlp_log,
			"extract_audio": True,
			"audio-format": "mp3",
			"write-thumbnail": True,
			"postprocessors": [{
				"key": "FFmpegExtractAudio",
				"preferredcodec": "mp3",
				"preferredquality": "192",
			}],
		}
		try:
			with YoutubeDL(ydl_opts) as ydl:
				ydl.download([video_url])
				self.__message_emitter("[+] Audio from playlist has been downloaded")
		except Exception as err:
			self.__message_emitter(f"[✗] ERROR: Downloading error {err}")
		self.finish_download.emit()

	def __extract_specified_audio(self, filenames, enable_logging):
		for file in filenames:
			self.__ffmpeg_extract_audio(file, enable_logging)
		self.__message_emitter(f"[✓] Extraction complete")

	def __extract_all_audio(self, enable_logging):
		for file in listdir():
			self.__ffmpeg_extract_audio(file, enable_logging)
		self.__message_emitter(f"[✓] Extraction complete")

	def __ffmpeg_extract_audio(self, filename, enable_logging):
		if filename.endswith(".mp4"):
			command = [
				"ffmpeg",							# Путь к ffmpeg (если он не в PATH)
				"-i", filename,						# Входное видео
				"-vn",								# Опция для указания, что нужно только аудио
				"-acodec", "libmp3lame",			# Копирование аудио без перекодирования
				"-ab", "192k",						# Установка битрейта аудио
				filename.replace(".mp4", ".mp3")	# Выходное аудио
			]
			try:
				if enable_logging:
					run(command, check=True)
				else:
					run(command, capture_output=True, check=True)
				self.__message_emitter(f"[✓] File {filename} converted successfully")
				self.extracted.emit()
			except CalledProcessError as err:
				self.__message_emitter(f"[✗] ERROR: File {filename} could not be converted {err}")
		else:
			self.__message_emitter(f"[-] Ignored the '{filename}'")

	def __found_emitter(self, data):
		self.founded.emit(data)
		log.debug(f"Data found... Video title is {data['title']}")

	def __update_emitter(self, updated_data):
		if updated_data['status'] == 'downloading':
			self.updated.emit(updated_data['total_bytes'], updated_data['downloaded_bytes'], updated_data['_percent_str'])

	def __message_emitter(self, message):
		self.messaged.emit(message)
		log.info(message)

	def __internal_done_callback(self, future):
		# self.__executor.shutdown(wait=False)
		log.debug(future)

class SettingsWidget(QWidget):
	def __init__(self):
		super(SettingsWidget, self).__init__()

		self.enable_logging_check_box = QGroupBox("Logging")
		self.enable_yt_dlp_logs_check_box = QCheckBox("Enable YT-DLP logs")
		self.enable_debug_logs_check_box = QCheckBox("Enable DEBUG logs")
		self.download_folder_group_box = QGroupBox("Download folder")
		self.download_folder_label = QLineEdit()
		self.choose_download_folder_butt = QPushButton("Choose download folder")
		self.advanced_naming_check_box = QCheckBox("Add the additional data to name video?")
		self.quality_label = QLabel("Choose the video quality:")
		self.quality_combo_box = QComboBox()
		self.quality_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		self.other_data_display_check_box = QCheckBox("Display other video data?")
		self.date_format_combo_box = QComboBox()

		self.enable_logging_check_box.setCheckable(True)
		self.enable_logging_check_box.setChecked(True)
		self.enable_yt_dlp_logs_check_box.setChecked(True)
		self.download_folder_label.setReadOnly(True)
		self.download_folder_label.setText(getcwd())
		self.choose_download_folder_butt.setMaximumWidth(150)
		self.quality_combo_box.addItems(["unknown"])
		self.other_data_display_check_box.setChecked(True)
		self.date_format_combo_box.addItems(["DD.MM.YYYY", "YYYY.MM.DD", "YYYY-MM-DD"])

		self.logging_layout = QHBoxLayout()
		self.logging_layout.addWidget(self.enable_yt_dlp_logs_check_box)
		self.logging_layout.addWidget(self.enable_debug_logs_check_box)
		self.enable_logging_check_box.setLayout(self.logging_layout)

		self.download_folder_layout = QHBoxLayout()
		self.download_folder_layout.addWidget(self.download_folder_label)
		self.download_folder_layout.addWidget(self.choose_download_folder_butt)
		self.download_folder_group_box.setLayout(self.download_folder_layout)

		self.quality_layout = QHBoxLayout()
		self.quality_layout.addWidget(self.quality_label)
		self.quality_layout.addWidget(self.quality_combo_box)
		self.quality_layout.addSpacerItem(self.quality_spacer)

		self.upload_date_layout = QHBoxLayout()
		self.upload_date_layout.addWidget(self.other_data_display_check_box)
		self.upload_date_layout.addWidget(self.date_format_combo_box)

		self.video_finder_layout = QVBoxLayout()
		self.video_finder_layout.addWidget(self.enable_logging_check_box)
		self.video_finder_layout.addWidget(self.download_folder_group_box)
		self.video_finder_layout.addLayout(self.upload_date_layout)
		self.video_finder_layout.addWidget(self.advanced_naming_check_box)
		self.video_finder_layout.addLayout(self.quality_layout)

		###

		self.setLayout(self.video_finder_layout)

class ProgressBarsWidget(QWidget):
	def __init__(self):
		super(ProgressBarsWidget, self).__init__()

		self.total_progress_bar = QProgressBar()
		self.unit_progress_bar = QProgressBar()

		self.progress_bars_layout = QVBoxLayout()
		self.progress_bars_layout.addWidget(self.total_progress_bar)
		self.progress_bars_layout.addWidget(self.unit_progress_bar)

		###

		self.setLayout(self.progress_bars_layout)

class VideoDataWidget(QWidget):
	visibility_changed = pyqtSignal(bool)

	def __init__(self):
		super(VideoDataWidget, self).__init__()

		self.thumbnail_label = QLabel()
		self.title_label = QLineEdit()
		self.description_label = QPlainTextEdit()
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

		self.thumbnail_label.setFixedSize(480, 270)
		self.title_label.setMinimumWidth(400)
		self.description_label.setReadOnly(True)
		self.uploader_label.setOpenExternalLinks(True)  # Открытие ссылок в браузере
		self.uploader_label.setTextFormat(Qt.TextFormat.RichText)  # Поддержка HTML
		self.uploader_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)  # Включаем интерактивность

		self.duration_string_icon.setFixedWidth(1)
		self.upload_date_icon.setFixedWidth(1)
		self.view_count_icon.setFixedWidth(1)
		self.like_count_icon.setFixedWidth(1)
		self.uploader_icon.setFixedWidth(1)

		self.main_info_layout = QVBoxLayout()
		self.main_info_layout.addWidget(self.thumbnail_label)
		self.main_info_layout.addWidget(self.title_label)
		self.main_info_layout.addWidget(self.description_label)

		self.duration_string_info_layout = QHBoxLayout()
		self.duration_string_info_layout.addWidget(self.duration_string_icon)
		self.duration_string_info_layout.addWidget(self.duration_string_label)

		self.upload_date_label_layout = QHBoxLayout()
		self.upload_date_label_layout.addWidget(self.upload_date_icon)
		self.upload_date_label_layout.addWidget(self.upload_date_label)

		self.video_count_data_layout = QHBoxLayout()
		self.video_count_data_layout.addWidget(self.view_count_icon)
		self.video_count_data_layout.addWidget(self.view_count_label)
		self.video_count_data_layout.addWidget(self.like_count_icon)
		self.video_count_data_layout.addWidget(self.like_count_label)

		self.uploader_label_layout = QHBoxLayout()
		self.uploader_label_layout.addWidget(self.uploader_icon)
		self.uploader_label_layout.addWidget(self.uploader_label)

		self.other_data_layout = QVBoxLayout()
		self.other_data_layout.addLayout(self.duration_string_info_layout)
		self.other_data_layout.addLayout(self.upload_date_label_layout)
		self.other_data_layout.addLayout(self.video_count_data_layout)
		self.other_data_layout.addLayout(self.uploader_label_layout)
		self.other_data_group_box = QGroupBox("Other data")
		self.other_data_group_box.setLayout(self.other_data_layout)

		self.banner_right_video_info_layout = QVBoxLayout()
		self.banner_right_video_info_layout.addLayout(self.main_info_layout)
		self.banner_right_video_info_layout.addWidget(self.other_data_group_box)

		###

		self.setLayout(self.banner_right_video_info_layout)

	def setVisible(self, visible):
		self.visibility_changed.emit(visible)
		super().setVisible(visible)

class DownloadButtWidget(QWidget):
	def __init__(self):
		super(DownloadButtWidget, self).__init__()

		self.download_metadata_butt = QPushButton("Save all metadata (JSON)")
		self.download_video_butt = QPushButton("Download in video format (MP4)")
		self.download_audio_butt = QPushButton("Download in audio format (MP3)")
		self.download_video_check_box = QCheckBox("Run in extra-mode")
		self.download_audio_check_box = QCheckBox("Run in extra-mode")

		self.download_video_check_box.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Ignored)
		self.download_audio_check_box.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Ignored)

		self.download_video_layout = QHBoxLayout()
		self.download_video_layout.addWidget(self.download_video_check_box)
		self.download_video_layout.addWidget(self.download_video_butt)

		self.download_audio_layout = QHBoxLayout()
		self.download_audio_layout.addWidget(self.download_audio_check_box)
		self.download_audio_layout.addWidget(self.download_audio_butt)

		self.download_butt_layout = QVBoxLayout()
		self.download_butt_layout.addWidget(self.download_metadata_butt)
		self.download_butt_layout.addLayout(self.download_video_layout)
		self.download_butt_layout.addLayout(self.download_audio_layout)

		###

		self.setLayout(self.download_butt_layout)
		# self.setEnabled(False)

class ExtractAudioButtWidget(QWidget):
	def __init__(self):
		super(ExtractAudioButtWidget, self).__init__()

		self.extract_specified_audio_butt = QPushButton("From specified .mp4 files")
		self.extract_all_audio_in_specified_dir_butt = QPushButton("From all .mp4 files in specified directory")
		self.extract_all_audio_butt = QPushButton("From all .mp4 files in this directory")
		self.extract_progress_bar = QProgressBar()

		self.extract_audio_butt_widget_layout = QVBoxLayout()
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
		self.video_searcher_layout.addWidget(self.url_line_edit)
		self.video_searcher_layout.addWidget(self.find_video_butt)

		###

		self.setLayout(self.video_searcher_layout)

class NYTDialogWindow(QMainWindow):
	def __init__(self):
		super(NYTDialogWindow, self).__init__()

		self.video_metadata = None
		self.playlist_metadata = None
		self.playlist_flag = False
		self.standard_quality = 144

		#####

		self.settings_widget = SettingsWidget()
		self.settings_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

		self.settings_widget.enable_logging_check_box.toggled.connect(self.enable_logging_check_box_toggled)
		self.settings_widget.enable_yt_dlp_logs_check_box.stateChanged.connect(self.enable_yt_dlp_logs_check_box_state_changed)
		self.settings_widget.enable_debug_logs_check_box.stateChanged.connect(self.enable_debug_logs_check_box_state_changed)
		self.settings_widget.choose_download_folder_butt.clicked.connect(self.choose_download_folder_butt_clicked)
		self.settings_widget.other_data_display_check_box.stateChanged.connect(self.other_data_display_check_box_state_changed)
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
		self.extract_audio_butt_widget.extract_all_audio_butt.clicked.connect(self.extract_all_audio_butt_clicked)

		self.extract_layout = QVBoxLayout()
		self.extract_layout.addWidget(self.extract_audio_butt_widget)

		self.extract_group_box = QGroupBox("Extract audio")
		self.extract_group_box.setFixedWidth(500)
		self.extract_group_box.setLayout(self.extract_layout)

		###

		self.video_searcher_widget = VideoSearcherWidget()
		self.video_metadata_widget = VideoDataWidget()
		self.video_metadata_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

		self.video_metadata_widget.visibility_changed.connect(self.video_metadata_widget_visibility_changed)
		self.video_searcher_widget.find_video_butt.clicked.connect(self.find_video_butt_clicked)

		self.video_metadata_layout = QVBoxLayout()
		self.video_metadata_layout.addWidget(self.video_searcher_widget)
		self.video_metadata_layout.addWidget(self.video_metadata_widget)
		self.video_metadata_layout.addSpacerItem(self.video_metadata_spacer)

		self.video_metadata_group_box = QGroupBox("Video")
		self.video_metadata_group_box.setLayout(self.video_metadata_layout)
		self.video_metadata_group_box.setFixedWidth(500)

		###

		self.download_butt_widget = DownloadButtWidget()
		self.download_progress_bars_widget = ProgressBarsWidget()

		self.download_butt_widget.download_metadata_butt.clicked.connect(self.download_metadata_butt_clicked)
		self.download_butt_widget.download_video_butt.clicked.connect(self.download_video_butt_clicked)
		self.download_butt_widget.download_audio_butt.clicked.connect(self.download_audio_butt_clicked)

		self.download_layout = QVBoxLayout()
		self.download_layout.addWidget(self.download_butt_widget)
		self.download_layout.addWidget(self.download_progress_bars_widget)

		self.download_group_box = QGroupBox("Download")
		self.download_group_box.setFixedWidth(500)
		self.download_group_box.setLayout(self.download_layout)

		#####

		# Dialog window customization

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

		self.central_widget = QWidget()
		self.central_widget.setLayout(self.main_layout)

		self.video_metadata_widget.setVisible(False)

		self.setWindowTitle("NYT Window")
		self.setCentralWidget(self.central_widget)
		self.setStatusBar(self.status_bar)
		# self.setMinimumSize(600, 480)

		#####

		self.loader = Loader()
		self.loader.founded.connect(self.loader_founded)
		self.loader.updated.connect(self.loader_updated)
		self.loader.messaged.connect(self.loader_messaged)
		self.loader.extracted.connect(self.loader_extracted)
		self.loader.start_download.connect(self.loader_start_download)
		self.loader.finish_download.connect(self.loader_finish_download)

	def loader_founded(self, metadata):
		if "_type" in metadata and metadata["_type"] == "playlist":
			self.playlist_metadata = {"video": [entry['id'] for entry in metadata['entries']], "counter": 0}
			self.download_progress_bars_widget.total_progress_bar.setMaximum(len(self.playlist_metadata["video"]))
			self.download_progress_bars_widget.total_progress_bar.setValue(0)
			self.download_progress_bars_widget.unit_progress_bar.setValue(0)
			self.loader.submit_find_video(self.playlist_metadata["video"][self.playlist_metadata["counter"]])
		else:
			self.video_metadata = metadata
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

			self.insert_video_metadata()
			self.settings_widget.quality_combo_box.clear()
			self.settings_widget.quality_combo_box.addItems(resolutions)
			self.settings_widget.quality_combo_box.setCurrentText(resolutions[0] if int(resolutions[0].replace("p", "")) <= self.standard_quality else f"{self.standard_quality}p")
			self.download_progress_bars_widget.unit_progress_bar.setValue(0)
			if not self.video_metadata_widget.isVisible():
				self.video_metadata_widget.setVisible(True)
			if self.download_butt_widget.download_video_check_box.isChecked():
				self.download_video_butt_clicked()
			elif self.download_butt_widget.download_audio_check_box.isChecked():
				self.download_audio_butt_clicked()
			if not self.playlist_flag:
				self.download_butt_widget.download_video_check_box.setEnabled(False)
				self.download_butt_widget.download_audio_check_box.setEnabled(False)

	def loader_updated(self, max_percent, current_percent, message):
		self.download_progress_bars_widget.unit_progress_bar.setMaximum(max_percent)
		self.download_progress_bars_widget.unit_progress_bar.setValue(current_percent)
		self.status_bar.showMessage(message)

	def loader_messaged(self, message):
		self.status_bar.showMessage(message)

	def loader_extracted(self):
		self.extract_audio_butt_widget.extract_progress_bar.setValue(self.extract_audio_butt_widget.extract_progress_bar.value() + 1)

	def loader_start_download(self):
		self.download_butt_widget.setEnabled(False)

	def loader_finish_download(self):
		if self.playlist_flag:
			self.playlist_metadata["counter"] += 1
			self.download_progress_bars_widget.total_progress_bar.setValue(self.playlist_metadata["counter"])
			if self.playlist_metadata["counter"] == len(self.playlist_metadata["video"]):
				self.playlist_flag = False
				self.download_butt_widget.download_video_check_box.setChecked(False)
				self.download_butt_widget.download_audio_check_box.setChecked(False)
				self.video_metadata_widget.setVisible(False)
				self.settings_widget.quality_combo_box.clear()
				self.settings_widget.quality_combo_box.addItem("unknown")
			else:
				self.loader.submit_find_video(self.playlist_metadata["video"][self.playlist_metadata["counter"]])
		else:
			self.download_progress_bars_widget.total_progress_bar.setMaximum(1)
			self.download_progress_bars_widget.total_progress_bar.setValue(1)
			self.download_butt_widget.download_video_check_box.setEnabled(True)
			self.download_butt_widget.download_audio_check_box.setEnabled(True)
			self.video_metadata_widget.setVisible(False)
			self.settings_widget.quality_combo_box.clear()
			self.settings_widget.quality_combo_box.addItem("unknown")

	def enable_logging_check_box_toggled(self, checked):
		if checked:
			# Включаем обработчики
			log.addHandler(console_handler)
			log.addHandler(file_handler)
			yt_dlp_log.addHandler(console_handler)
			yt_dlp_log.addHandler(file_handler)

			# Разблокируем QCheckBox
			self.settings_widget.enable_debug_logs_check_box.setEnabled(True)
			self.settings_widget.enable_yt_dlp_logs_check_box.setEnabled(True)
		else:
			# Отключаем обработчики
			log.removeHandler(console_handler)
			log.removeHandler(file_handler)
			yt_dlp_log.removeHandler(console_handler)
			yt_dlp_log.removeHandler(file_handler)

			# Блокируем QCheckBox
			self.settings_widget.enable_debug_logs_check_box.setEnabled(False)
			self.settings_widget.enable_yt_dlp_logs_check_box.setEnabled(False)

	def enable_yt_dlp_logs_check_box_state_changed(self, state):
		if state:
			# Включаем логирование yt_dlp
			yt_dlp_log.addHandler(console_handler)
			yt_dlp_log.addHandler(file_handler)
		else:
			# Отключаем логирование yt_dlp
			yt_dlp_log.removeHandler(console_handler)
			yt_dlp_log.removeHandler(file_handler)

	def enable_debug_logs_check_box_state_changed(self, state):
		if state:
			# Устанавливаем уровень DEBUG для файлового обработчика
			file_handler.setLevel(logging.DEBUG)
		else:
			# Устанавливаем уровень INFO для файлового обработчика
			file_handler.setLevel(logging.INFO)

	def choose_download_folder_butt_clicked(self):
		self.settings_widget.download_folder_label.setText(QFileDialog.getExistingDirectory(self, "Выберите директорию с видео"))

	def other_data_display_check_box_state_changed(self, state):
		self.video_metadata_widget.other_data_group_box.setVisible(state)
		self.settings_widget.date_format_combo_box.setVisible(state)

	def date_format_combo_box_current_text_changed(self, state):
		if self.video_metadata_widget.isVisible():
			self.video_metadata_widget.upload_date_label.setText(self.video_metadata['upload_date'][state])

	def video_metadata_widget_visibility_changed(self, visible):
		self.video_searcher_widget.url_line_edit.setReadOnly(visible)
		self.download_butt_widget.setEnabled(visible)

	def find_video_butt_clicked(self):
		if self.__analyze_link():
			if self.playlist_flag:
				self.loader.submit_find_playlist(
					self.video_searcher_widget.url_line_edit.text()
				)
			else:
				self.loader.submit_find_video(
					self.video_searcher_widget.url_line_edit.text()
				)

	def download_metadata_butt_clicked(self):
		with open(f"{self.video_metadata_widget.title_label.text()}.json", "w", encoding="utf-8") as json_file:
			json.dump(self.video_metadata, json_file, indent=4)

	def download_video_butt_clicked(self):
		name = f"{self.settings_widget.download_folder_label.text()}/"
		name += f"[%(id)s] - {self.video_metadata_widget.title_label.text()} - %(uploader)s - %(resolution)s - %(playlist)s - %(playlist_index)s.%(ext)s" if self.settings_widget.advanced_naming_check_box.isChecked() else f"{self.video_metadata_widget.title_label.text()}.%(ext)s"
		self.loader.submit_download_video(
			self.video_metadata["id"],
			name,
			[fmt["format_id"] for fmt in self.video_metadata["formats"] if fmt.get("format_note") == self.settings_widget.quality_combo_box.currentText() and fmt.get("ext") == "mp4"][0]
		)

	def download_audio_butt_clicked(self):
		name = f"{self.settings_widget.download_folder_label.text()}/"
		name += f"[%(id)s] - {self.video_metadata_widget.title_label.text()} - %(uploader)s - %(resolution)s - %(playlist)s - %(playlist_index)s.%(ext)s" if self.settings_widget.advanced_naming_check_box.isChecked() else f"{self.video_metadata_widget.title_label.text()}.%(ext)s"
		self.loader.submit_download_audio(
			self.video_metadata["id"],
			name
		)

	def extract_specified_audio_butt_clicked(self):
		# Открытие диалога выбора файла
		file_names, _ = QFileDialog.getOpenFileNames(self, "Choose the video", self.settings_widget.download_folder_label.text(), "Video (*.mp4)")
		if file_names:
			self.extract_audio_butt_widget.extract_progress_bar.setMaximum(len(file_names))
			self.extract_audio_butt_widget.extract_progress_bar.setValue(0)
			self.loader.submit_extract_specified_audio(
				file_names,
				self.settings_widget.enable_logging_check_box.isChecked()
			)

	def extract_all_audio_in_specified_dir_butt_clicked(self):
		# Открываем диалог для выбора директории
		selected_dir = QFileDialog.getExistingDirectory(self, "Choose the directory with video")
		if selected_dir:
			# Получаем список всех файлов в выбранной директории
			file_names = [path.join(selected_dir, video_file) for video_file in listdir(selected_dir) if video_file.endswith(".mp4")]
			if file_names:
				self.extract_audio_butt_widget.extract_progress_bar.setMaximum(len(file_names))
				self.extract_audio_butt_widget.extract_progress_bar.setValue(0)
				self.loader.submit_extract_specified_audio(
					file_names,
					self.settings_widget.enable_logging_check_box.isChecked()
				)
			else:
				log.warning("In chosen directory not video.")

	def extract_all_audio_butt_clicked(self):
		self.extract_audio_butt_widget.extract_progress_bar.setMaximum(sum(1 for f in listdir(getcwd()) if f.endswith(".mp4")))
		self.extract_audio_butt_widget.extract_progress_bar.setValue(0)
		self.loader.submit_extract_all_audio(
			self.settings_widget.enable_logging_check_box.isChecked()
		)

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
			self.playlist_flag = False if len(self.video_searcher_widget.url_line_edit.text()) < 20 else True
			return True

	def insert_video_metadata(self):
		for fmt in self.video_metadata["formats"]:
			log.debug(f"ID: {fmt['format_id']}, Height: x{fmt.get('height', '-')}, Ext: {fmt['ext']}, Note: {fmt.get('format_note', '-')}")

		response = get(self.video_metadata['thumbnail'])
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			# pixmap = pixmap.scaled(int(pixmap.width() * 0.25), int(pixmap.height() * 0.25), Qt.AspectRatioMode.KeepAspectRatio)
			pixmap = pixmap.scaled(480, 270, Qt.AspectRatioMode.KeepAspectRatio)  # 640*320, 480*270
			self.video_metadata_widget.thumbnail_label.setPixmap(pixmap)
		else:
			self.video_metadata_widget.thumbnail_label.setText("Не удалось загрузить картинку")

		udload_video_date = datetime.strptime(self.video_metadata['upload_date'], "%Y%m%d")
		self.video_metadata['upload_date'] = {
			"DD.MM.YYYY": udload_video_date.strftime("%d.%m.%Y"),
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

		self.video_metadata_widget.title_label.setText(self.video_metadata['title'])
		self.video_metadata_widget.description_label.setPlainText(self.video_metadata['description'])
		self.video_metadata_widget.duration_string_label.setText(self.video_metadata['duration_string'])
		self.video_metadata_widget.upload_date_label.setText(self.video_metadata['upload_date'][self.settings_widget.date_format_combo_box.currentText()])
		self.video_metadata_widget.view_count_label.setText(f"Количество просмотров: {self.video_metadata['view_count']}")
		self.video_metadata_widget.like_count_label.setText(f"Количество лайков: {self.video_metadata['like_count']}")
		self.video_metadata_widget.uploader_label.setText(f"<a href='{self.video_metadata['channel_url']}'>{self.video_metadata['uploader']}</a> ({self.video_metadata['channel_follower_count']} подписок)")

if __name__ == '__main__':
	app = QApplication(sys.argv)
	ui = NYTDialogWindow()
	ui.show()
	sys.exit(app.exec())
