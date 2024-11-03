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
from os import listdir, rename
from subprocess import run, CalledProcessError
from requests import get
from datetime import datetime
import logging as log

from concurrent.futures import ThreadPoolExecutor

from yt_dlp import YoutubeDL
import json

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QCheckBox, QProgressBar, QComboBox, QPushButton, QPlainTextEdit, QSpacerItem, QMessageBox, QStatusBar, QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QObject, pyqtSignal

# Настройка логирования
log.basicConfig(
    level=log.DEBUG,  # Уровень логирования
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат логов
    handlers=[
        log.StreamHandler(),  # Обработчик для вывода в консоль
        log.FileHandler('NYT.log', encoding='utf-8')  # Обработчик для записи в файл
    ]
)

# todo
#  1. Сделать переименование видео после загрузки
#  2. Завершить реализацию загрузки плейлистов:
#  2.1. После каждого видео останавливаться на подтверждение загрузки и указание имени файла
#  2.2. Добавить настройки, выключающие переименование и добавляющие быструю загрузку
#  3. Поработать над интерфейсом программы
#  4. Провести рефакторинг кода

class Loader(QObject):
	founded = pyqtSignal(dict)
	updated = pyqtSignal(int, int, str)
	messaged = pyqtSignal(str)

	def __init__(self):
		super(Loader, self).__init__()
		self.__executor = ThreadPoolExecutor(max_workers=1)

	def submit_find_video(self, video_url):
		future = self.__executor.submit(self.__get_video_metadata, video_url)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_video(self, video_url, video_title, video_metadata_title, video_format, quiet, run_extract_audio):
		future = self.__executor.submit(self.__download_video, video_url, video_title, video_metadata_title, video_format, quiet, run_extract_audio)
		future.add_done_callback(self.__internal_done_callback)

	def submit_download_audio(self, video_url, quiet):
		future = self.__executor.submit(self.__download_audio, video_url, quiet)
		future.add_done_callback(self.__internal_done_callback)

	def submit_extract_specified_audio(self, filenames, logging):
		future = self.__executor.submit(self.__extract_specified_audio, filenames, logging)
		future.add_done_callback(self.__internal_done_callback)

	def submit_extract_all_audio(self, logging):
		future = self.__executor.submit(self.__extract_all_audio, logging)
		future.add_done_callback(self.__internal_done_callback)

	def __get_video_metadata(self, video_url):
		ydl_opts = {
			'quiet': True,			# Отключает лишние сообщения в консоли
			'no_warnings': True,
		}
		with YoutubeDL(ydl_opts) as ydl:
			self.__found_emitter(ydl.extract_info(video_url, download=False))  # Только извлекает информацию

	def __download_video(self, video_url, video_title, video_metadata_title, video_format, quiet, run_extract_audio):
		ydl_opts = {
			"format": f"best[height<={video_format}]",
			"quiet": not quiet,
			"output": "%(title)s.%(ext)s",
			"progress_hooks": [self.__update_emitter],
		}
		try:
			with YoutubeDL(ydl_opts) as ydl:
				ydl.download([video_url])
				self.__message_emitter("[+] Video from playlist has been downloaded")
		except Exception as err:
			self.__message_emitter(f"[✗] ERROR: Downloading error {err}")

		# rename(video_metadata_title, video_title)

		if run_extract_audio:
			self.__ffmpeg_extract_audio(video_title, quiet)

	def __download_audio(self, video_url, quiet):
		ydl_opts = {
			"format": "bestaudio/best",
			"quiet": not quiet,
			"output": "%(title)s.%(ext)s",
			"progress_hooks": [self.__update_emitter],
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

	def __extract_specified_audio(self, filenames, logging):
		for file in filenames:
			self.__ffmpeg_extract_audio(file, logging)
		self.__message_emitter(f"[✓] Extraction complete")

	def __extract_all_audio(self, logging):
		for file in listdir():
			self.__ffmpeg_extract_audio(file, logging)
		self.__message_emitter(f"[✓] Extraction complete")

	def __ffmpeg_extract_audio(self, filename, logging):
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
				if logging:
					run(command, check=True)
				else:
					run(command, capture_output=True, check=True)
				self.__message_emitter(f"[✓] File {filename} converted successfully")
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
			log.debug(f"total_bytes = {updated_data['total_bytes']}, downloaded_bytes = {updated_data['downloaded_bytes']}, _percent_str = {updated_data['_percent_str']}")

	def __message_emitter(self, message):
		self.messaged.emit(message)
		log.info(message)

	def __internal_done_callback(self, future):
		# self.__executor.shutdown(wait=False)
		log.debug(future)

class VideoFinderWidget(QWidget):
	def __init__(self):
		super(VideoFinderWidget, self).__init__()

		self.logging_check_box = QCheckBox("Enable logging?")
		self.rename_check_box = QCheckBox("Activate the video rename mode?")
		self.extract_audio_check_box = QCheckBox("Extract audio before download videos?")
		self.quality_combo_box = QComboBox()
		self.source_combo_box = QComboBox()
		self.source_check_box = QCheckBox("Activate extra download mode?")
		self.url_label = QLabel("https://www.youtube.com/watch?v=")
		self.url_line_edit = QLineEdit()
		self.find_video_butt = QPushButton("Find video")
		self.other_data_display_check_box = QCheckBox("Display other video data?")
		self.date_format_combo_box = QComboBox()
		self.bottom_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

		self.quality_combo_box.addItems(["720", "1080"])
		self.source_combo_box.addItems(["video", "playlist"])
		self.source_check_box.setVisible(False)
		self.url_line_edit.setFixedWidth(250)
		self.url_line_edit.setPlaceholderText("Enter the video or playlist URL")
		self.url_line_edit.setText("YgoGXLWEVUk")
		# self.url_line_edit.setText("PL2MbnZfZV5Ksz3V1TABFnBiEXDjK4RqKM")
		self.other_data_display_check_box.setChecked(True)
		self.date_format_combo_box.addItems(["DD.MM.YYYY", "YYYY.MM.DD", "YYYY-MM-DD"])

		self.source_layout = QHBoxLayout()
		self.source_layout.addWidget(self.source_combo_box)
		self.source_layout.addWidget(self.source_check_box)

		self.url_layout = QHBoxLayout()
		self.url_layout.addWidget(self.url_label)
		self.url_layout.addWidget(self.url_line_edit)

		self.upload_date_layout = QHBoxLayout()
		self.upload_date_layout.addWidget(self.other_data_display_check_box)
		self.upload_date_layout.addWidget(self.date_format_combo_box)

		self.video_finder_layout = QVBoxLayout()
		self.video_finder_layout.addWidget(self.logging_check_box)
		self.video_finder_layout.addWidget(self.rename_check_box)
		self.video_finder_layout.addWidget(self.extract_audio_check_box)
		self.video_finder_layout.addLayout(self.source_layout)
		self.video_finder_layout.addLayout(self.url_layout)
		self.video_finder_layout.addWidget(self.find_video_butt)
		self.video_finder_layout.addLayout(self.upload_date_layout)
		self.video_finder_layout.addSpacerItem(self.bottom_spacer)

		###

		self.setLayout(self.video_finder_layout)

class VideoDataWidget(QWidget):
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

class DownloadButtWidget(QWidget):
	def __init__(self):
		super(DownloadButtWidget, self).__init__()

		self.download_metadata_butt = QPushButton("Save all metadata (JSON)")
		self.download_video_butt = QPushButton("Download in video format (MP4)")
		self.download_audio_butt = QPushButton("Download in audio format (MP3)")

		self.download_metadata_butt.setEnabled(False)

		self.download_butt_layout = QVBoxLayout()
		self.download_butt_layout.addWidget(self.download_metadata_butt)
		self.download_butt_layout.addWidget(self.download_video_butt)
		self.download_butt_layout.addWidget(self.download_audio_butt)

		###

		self.setLayout(self.download_butt_layout)

class ExtractAudioButtWidget(QWidget):
	def __init__(self):
		super(ExtractAudioButtWidget, self).__init__()

		self.extract_specified_audio_butt = QPushButton("Audio from specified .mp4 file")
		self.extract_all_audio_butt = QPushButton("Audio from all .mp4 files in this directory")
		self.extract_bottom_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

		self.extract_audio_butt_layout = QHBoxLayout()
		self.extract_audio_butt_layout.addWidget(self.extract_specified_audio_butt)
		self.extract_audio_butt_layout.addWidget(self.extract_all_audio_butt)

		self.extract_audio_butt_widget_layout = QVBoxLayout()
		self.extract_audio_butt_widget_layout.addLayout(self.extract_audio_butt_layout)
		self.extract_audio_butt_widget_layout.addSpacerItem(self.extract_bottom_spacer)

		###

		self.setLayout(self.extract_audio_butt_widget_layout)

class NYTDialogWindow(QMainWindow):
	def __init__(self):
		super(NYTDialogWindow, self).__init__()

		self.video_metadata = None

		#####

		self.video_finder_widget = VideoFinderWidget()

		self.video_finder_widget.rename_check_box.stateChanged.connect(self.rename_check_box_state_changed)
		self.video_finder_widget.extract_audio_check_box.stateChanged.connect(self.extract_audio_check_box_state_changed)
		self.video_finder_widget.source_combo_box.currentTextChanged.connect(self.source_combo_box_current_text_changed)
		self.video_finder_widget.source_check_box.stateChanged.connect(self.source_check_box_state_changed)
		self.video_finder_widget.other_data_display_check_box.stateChanged.connect(self.other_data_display_check_box_state_changed)
		self.video_finder_widget.date_format_combo_box.currentTextChanged.connect(self.date_format_combo_box_current_text_changed)
		self.video_finder_widget.find_video_butt.clicked.connect(self.find_video_butt_clicked)

		self.settings_group_box_layout = QVBoxLayout()
		self.settings_group_box_layout.addWidget(self.video_finder_widget)

		self.settings_group_box = QGroupBox("Settings")
		self.settings_group_box.setFixedWidth(500)
		self.settings_group_box.setLayout(self.settings_group_box_layout)

		###

		self.video_data_widget = VideoDataWidget()
		self.download_butt_widget = DownloadButtWidget()
		self.download_progress_bar = QProgressBar()

		self.download_progress_bar.setValue(0)

		self.download_butt_widget.download_metadata_butt.clicked.connect(self.download_metadata_butt_clicked)
		self.download_butt_widget.download_video_butt.clicked.connect(self.download_video_butt_clicked)
		self.download_butt_widget.download_audio_butt.clicked.connect(self.download_audio_butt_clicked)

		self.download_group_box_layout = QVBoxLayout()
		self.download_group_box_layout.addWidget(self.video_data_widget)
		self.download_group_box_layout.addWidget(self.download_butt_widget)
		self.download_group_box_layout.addWidget(self.download_progress_bar)

		self.download_group_box = QGroupBox("Download")
		self.download_group_box.setLayout(self.download_group_box_layout)
		self.download_group_box.setFixedWidth(500)
		self.download_group_box.setVisible(False)
		# self.download_group_box.setEnabled(False)

		#####

		self.extract_audio_butt_widget = ExtractAudioButtWidget()

		self.extract_audio_butt_widget.extract_specified_audio_butt.clicked.connect(self.extract_specified_audio_butt_clicked)
		self.extract_audio_butt_widget.extract_all_audio_butt.clicked.connect(self.extract_all_audio_butt_clicked)

		self.extract_group_box_layout = QVBoxLayout()
		self.extract_group_box_layout.addWidget(self.extract_audio_butt_widget)

		self.extract_group_box = QGroupBox("Extract")
		self.extract_group_box.setFixedWidth(500)
		self.extract_group_box.setLayout(self.extract_group_box_layout)

		#####

		# Dialog window customization

		self.status_bar = QStatusBar()

		self.left_half_main_layout = QVBoxLayout()
		self.left_half_main_layout.addWidget(self.settings_group_box)

		self.right_half_main_layout = QVBoxLayout()
		self.right_half_main_layout.addWidget(self.download_group_box)
		self.right_half_main_layout.addWidget(self.extract_group_box)

		self.main_layout = QHBoxLayout()
		self.main_layout.addLayout(self.left_half_main_layout)
		self.main_layout.addLayout(self.right_half_main_layout)

		self.central_widget = QWidget()
		self.central_widget.setLayout(self.main_layout)

		self.setWindowTitle("NYT Window")
		self.setCentralWidget(self.central_widget)
		self.setStatusBar(self.status_bar)
		# self.setMinimumSize(600, 480)

		#####

		self.loader = Loader()
		self.loader.founded.connect(self.loader_founded)
		self.loader.updated.connect(self.loader_updated)
		self.loader.messaged.connect(self.loader_messaged)

	def loader_founded(self, video_metadata):
		self.download_group_box.setVisible(True)
		# self.video_downloader_widget.setEnabled(True)

		response = get(video_metadata['thumbnail'])
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			# pixmap = pixmap.scaled(int(pixmap.width() * 0.25), int(pixmap.height() * 0.25), Qt.AspectRatioMode.KeepAspectRatio)
			pixmap = pixmap.scaled(480, 270, Qt.AspectRatioMode.KeepAspectRatio)  #640*320, 480*270
			self.video_data_widget.thumbnail_label.setPixmap(pixmap)
		else:
			self.video_data_widget.thumbnail_label.setText("Не удалось загрузить картинку")

		udload_video_date = datetime.strptime(video_metadata['upload_date'], "%Y%m%d")
		video_metadata['upload_date'] = {
			"DD.MM.YYYY": udload_video_date.strftime("%d.%m.%Y"),
			"YYYY.MM.DD": udload_video_date.strftime("%Y.%m.%d"),
			"YYYY-MM-DD": udload_video_date.strftime("%Y-%m-%d")
		}

		self.video_data_widget.title_label.setText(video_metadata['title'])
		self.video_data_widget.description_label.setPlainText(video_metadata['description'])
		self.video_data_widget.duration_string_label.setText(video_metadata['duration_string'])
		self.video_data_widget.upload_date_label.setText(video_metadata['upload_date'][self.video_finder_widget.date_format_combo_box.currentText()])
		self.video_data_widget.view_count_label.setText(f"Количество просмотров: {video_metadata['view_count']}")
		self.video_data_widget.like_count_label.setText(f"Количество лайков: {video_metadata['like_count']}")
		self.video_data_widget.uploader_label.setText(f"<a href='{video_metadata['channel_url']}'>{video_metadata['uploader']}</a> ({video_metadata['channel_follower_count']} подписок)")

		self.video_metadata = video_metadata

	def loader_updated(self, max_percent, current_percent, message):
		self.download_progress_bar.setMaximum(max_percent)
		self.download_progress_bar.setValue(current_percent)
		self.status_bar.showMessage(message)

	def loader_messaged(self, message):
		self.status_bar.showMessage(message)

	def rename_check_box_state_changed(self, state):
		if state:
			self.video_data_widget.title_label.setReadOnly(True)
		else:
			self.video_data_widget.title_label.setReadOnly(False)

	def extract_audio_check_box_state_changed(self, state):
		if state:
			self.download_butt_widget.download_audio_butt.setDisabled(True)
		else:
			self.download_butt_widget.download_audio_butt.setDisabled(False)

	def source_combo_box_current_text_changed(self, state):
		if state == "video":
			self.video_finder_widget.url_label.setText("https://www.youtube.com/watch?v=")
			self.video_finder_widget.source_check_box.setVisible(False)
		else:
			self.video_finder_widget.url_label.setText("https://www.youtube.com/playlist?list=")
			self.video_finder_widget.source_check_box.setVisible(True)

	def source_check_box_state_changed(self, state):
		if state:
			self.download_group_box.setVisible(True)
		else:
			self.download_group_box.setVisible(False)

	def other_data_display_check_box_state_changed(self, state):
		if state:
			self.video_data_widget.other_data_group_box.setVisible(True)
			self.video_finder_widget.date_format_combo_box.setVisible(True)
		else:
			self.video_data_widget.other_data_group_box.setVisible(False)
			self.video_finder_widget.date_format_combo_box.setVisible(False)

	def date_format_combo_box_current_text_changed(self, state):
		if self.video_data_widget.isVisible():
			self.video_data_widget.upload_date_label.setText(self.video_metadata['upload_date'][state])

	def find_video_butt_clicked(self):
		self.loader.submit_find_video(
			self.video_finder_widget.url_line_edit.text()
		)

	def download_metadata_butt_clicked(self):
		pass
		# print(repr(self.video_metadata['title']))
		# print(self.video_metadata['title'].encode("utf-16").decode("utf-8"))
		# title = self.video_metadata['title'].replace('\x00', '').encode('utf-8').decode("utf-8")
		# repr(self.video_metadata['title'].encode('utf-8').decode('utf-8'))
		# print(self.video_metadata['title'].encode('utf-16').decode('utf-8', 'ignore'))
		# print(self.video_metadata['title'])
		# print(self.video_metadata['title'])
		# print(self.video_metadata['title'].encode('utf-8').decode('utf-8'))
		# print(self.video_metadata['title'].encode('unicode_escape').decode('utf-8'))

		# title = json.loads(json.dumps(self.video_metadata, ensure_ascii=False))
		# print(self.video_metadata['title'])

		# converted_string = ""
		# for char in self.video_metadata['title']:
		# 	try:
		# 		converted_string += char.encode('utf-8').decode('utf-8')
		# 	except UnicodeEncodeError:
		# 		converted_string += char.encode('utf-16-be').decode('utf-8', 'ignore')

		# print(json.loads('{' + self.video_metadata['title'] + '}')['title'])
		# with open(f"{self.video_metadata['title']}.json", "w", encoding="utf-8") as json_file:
		# 	json.dump(self.video_metadata, json_file, indent=4)

	def download_video_butt_clicked(self):  # download_playlist()
		self.loader.submit_download_video(
			self.video_finder_widget.url_line_edit.text(),
			self.video_data_widget.title_label.text(),
			f"{self.video_metadata['title']}.mp4",
			self.video_finder_widget.quality_combo_box.currentText(),
			self.video_finder_widget.logging_check_box.isChecked(),
			self.video_finder_widget.extract_audio_check_box.isChecked()
		)

	def download_audio_butt_clicked(self):  # extract_audio
		self.loader.submit_download_audio(
			self.video_finder_widget.url_line_edit.text(),
			self.video_finder_widget.logging_check_box.isChecked()
		)

	def extract_specified_audio_butt_clicked(self):
		# Открытие диалога выбора файла
		file_names, _ = QFileDialog.getOpenFileNames(self, "Выберите файл", "", "Все файлы (*)")
		if file_names:
			log.debug(f"Выбранный файл: {file_names}")
			self.loader.submit_extract_specified_audio(
				file_names,
				self.video_finder_widget.logging_check_box.isChecked()
			)

	def extract_all_audio_butt_clicked(self):  # download_audio_from_playlist()
		self.loader.submit_extract_all_audio(
			self.video_finder_widget.logging_check_box.isChecked()
		)

if __name__ == '__main__':
	app = QApplication(sys.argv)
	ui = NYTDialogWindow()
	ui.show()
	sys.exit(app.exec())
