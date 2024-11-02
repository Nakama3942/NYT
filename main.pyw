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

from concurrent.futures import ThreadPoolExecutor, as_completed
# from threading import Thread

from yt_dlp import YoutubeDL
import json

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QLabel, QLineEdit, QCheckBox, QProgressBar, QComboBox, QPushButton, QPlainTextEdit, QMessageBox, QStatusBar
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QObject

# todo
#  1. Сделать переименование видео после загрузки
#  2. Добавить комбобокс выбора типа источника (видео или плейлист)
#  2. Завершить реализацию загрузки плейлистов:
#  2.1. После каждого видео останавливаться на подтверждение загрузки и указание имени файла
#  2.2. Добавить настройки, выключающие переименование и добавляющие быструю загрузку
#  3. Поработать над интерфейсом программы
#  4. Провести рефакторинг кода

class Loader(QObject):
	founded = pyqtSignal(dict)
	updated = pyqtSignal(int, int, str)
	finished = pyqtSignal(str)

	def __init__(self):
		super(Loader, self).__init__()
		self.__executor = ThreadPoolExecutor(max_workers=1)

	def submit_find_video(self, video_url):
		future = self.__executor.submit(self.find_video, video_url)
		future.add_done_callback(self.__internal_done_callback)

	def find_video(self, video_url):
		ydl_opts = {
			'quiet': True,  # Отключает лишние сообщения в консоли
			'no_warnings': True,
		}
		with YoutubeDL(ydl_opts) as ydl:
			self.founded.emit(ydl.extract_info(video_url, download=False))  # Только извлекает информацию

	def submit_download_video(self, video_url, video_title, video_metadata_title, video_format, quiet, run_extract_audio, logging):
		future = self.__executor.submit(self.download_video, video_url, video_title, video_metadata_title, video_format, quiet, run_extract_audio, logging)
		future.add_done_callback(self.__internal_done_callback)

	def download_video(self, video_url, video_title, video_metadata_title, video_format, quiet, run_extract_audio, logging):
		ydl_opts = {
			"format": f"best[height<={video_format}]",
			"quiet": not quiet,
			"output": "%(title)s.%(ext)s",
			"progress_hooks": [self.update_emitter],
		}
		try:
			with YoutubeDL(ydl_opts) as ydl:
				ydl.download([video_url])
				self.finished.emit("[+] Video from playlist has been downloaded")
		except Exception as err:
			self.finished.emit(f"[✗] ERROR: Downloading error {err}")

		# rename(video_metadata_title, video_title)

		if run_extract_audio:
			self.__ffmpeg_extract_audio(video_title, logging)

	def submit_download_audio(self, video_url, quiet):
		future = self.__executor.submit(self.download_audio, video_url, quiet)
		future.add_done_callback(self.__internal_done_callback)

	def download_audio(self, video_url, quiet):
		ydl_opts = {
			"format": "bestaudio/best",
			"quiet": not quiet,
			"output": "%(title)s.%(ext)s",
			"progress_hooks": [self.update_emitter],
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
				self.finished.emit("[+] Audio from playlist has been downloaded")
		except Exception as err:
			self.finished.emit(f"[✗] ERROR: Downloading error {err}")

	def submit_extract_audio(self, logging):
		future = self.__executor.submit(self.download_audio, logging)
		future.add_done_callback(self.__internal_done_callback)

	def extract_audio(self, logging):
		for file in listdir():
			self.__ffmpeg_extract_audio(file, logging)

	def __ffmpeg_extract_audio(self, filename, logging):
		print(1)
		print(filename)
		if filename.endswith(".mp4"):
			print(2)
			command = [
				"ffmpeg",  # Путь к ffmpeg (если он не в PATH)
				"-i", filename,  # Входное видео
				"-vn",  # Опция для указания, что нужно только аудио
				"-acodec", "libmp3lame",  # Копирование аудио без перекодирования
				"-ab", "192k",  # Установка битрейта аудио
				filename.replace(".mp4", ".mp3")  # Выходное аудио
			]
			print(3)
			try:
				if logging:
					run(command, check=True)
				else:
					run(command, capture_output=True, check=True)
				print(4)
				self.progress_update_signal.emit(f"[✓] File {filename} converted successfully")
			except CalledProcessError as err:
				self.progress_update_signal.emit(f"[✗] ERROR: File {filename} could not be converted {err}")
		else:
			self.progress_update_signal.emit(f"[-] Ignored the '{filename}'")

	def update_emitter(self, emit_value):
		if emit_value['status'] == 'downloading':
			self.updated.emit(emit_value['total_bytes'], emit_value['downloaded_bytes'], emit_value['_percent_str'])

	def __internal_done_callback(self, future):
		# self.__executor.shutdown(wait=False)
		print(future)

class NYTDialogWindow(QMainWindow):
	def __init__(self):
		super(NYTDialogWindow, self).__init__()

		self.video_metadata = None

		#####

		self.extract_audio_butt = QPushButton("Extract audio from all .mp4 files in this directory")
		self.extract_audio_butt.clicked.connect(self.extract_audio_butt_clicked)

		self.extract_group_box_layout = QVBoxLayout()
		self.extract_group_box_layout.addWidget(self.extract_audio_butt)

		self.extract_group_box = QGroupBox("Extract")
		self.extract_group_box.setLayout(self.extract_group_box_layout)

		#####

		self.logging_check_box = QCheckBox("Enable logging?")

		self.rename_check_box = QCheckBox("Activate the video rename mode?")
		self.rename_check_box.stateChanged.connect(self.rename_check_box_state_changed)

		self.extract_audio_check_box = QCheckBox("Extract audio before download videos?")
		self.extract_audio_check_box.stateChanged.connect(self.extract_audio_check_box_state_changed)

		self.quality_combo_box = QComboBox()
		self.quality_combo_box.addItems(["720", "1080"])

		self.source_combo_box = QComboBox()
		self.source_combo_box.addItems(["video", "playlist"])
		self.source_combo_box.currentTextChanged.connect(self.source_combo_box_current_text_changed)

		self.source_check_box = QCheckBox("Activate extra download mode?")
		self.source_check_box.stateChanged.connect(self.source_check_box_state_changed)
		self.source_check_box.setVisible(False)

		self.source_layout = QHBoxLayout()
		self.source_layout.addWidget(self.source_combo_box)
		self.source_layout.addWidget(self.source_check_box)

		self.url_label = QLabel("https://www.youtube.com/watch?v=")

		self.url_line_edit = QLineEdit()
		self.url_line_edit.setPlaceholderText("Enter the video or playlist URL")
		self.url_line_edit.setText("YgoGXLWEVUk")
		# self.url_line_edit.setText("PL2MbnZfZV5Ksz3V1TABFnBiEXDjK4RqKM")

		self.url_layout = QHBoxLayout()
		self.url_layout.addWidget(self.url_label)
		self.url_layout.addWidget(self.url_line_edit)

		self.find_video_butt = QPushButton("Find video")
		self.find_video_butt.clicked.connect(self.find_video_butt_clicked)

		self.video_finder_layout = QVBoxLayout()
		self.video_finder_layout.addWidget(self.logging_check_box)
		self.video_finder_layout.addWidget(self.rename_check_box)
		self.video_finder_layout.addWidget(self.extract_audio_check_box)
		self.video_finder_layout.addLayout(self.source_layout)
		self.video_finder_layout.addLayout(self.url_layout)
		self.video_finder_layout.addWidget(self.find_video_butt)

		self.video_finder_widget = QWidget()
		self.video_finder_widget.setLayout(self.video_finder_layout)

		###

		self.title_label = QLineEdit()
		self.title_label.setMinimumWidth(400)
		self.description_label = QPlainTextEdit()
		self.description_label.setReadOnly(True)
		self.upload_date_label = QLabel()

		self.main_info_layout = QVBoxLayout()
		self.main_info_layout.addWidget(self.title_label)
		self.main_info_layout.addWidget(self.description_label)
		self.main_info_layout.addWidget(self.upload_date_label)

		self.duration_string_label = QLabel()

		self.duration_string_info_layout = QVBoxLayout()
		self.duration_string_info_layout.addWidget(self.duration_string_label)

		self.duration_string_group_box = QGroupBox("Длительность")
		self.duration_string_group_box.setLayout(self.duration_string_info_layout)

		self.view_count_label = QLabel()
		self.like_count_label = QLabel()

		self.video_count_data_layout = QHBoxLayout()
		self.video_count_data_layout.addWidget(self.view_count_label)
		self.video_count_data_layout.addWidget(self.like_count_label)

		self.video_count_data_group_box = QGroupBox("Статистика")
		self.video_count_data_group_box.setLayout(self.video_count_data_layout)

		self.uploader_label = QLabel()
		self.uploader_label.setOpenExternalLinks(True)  # Открытие ссылок в браузере
		self.uploader_label.setTextFormat(Qt.TextFormat.RichText)  # Поддержка HTML
		self.uploader_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)  # Включаем интерактивность

		self.uploader_label_layout = QVBoxLayout()
		self.uploader_label_layout.addWidget(self.uploader_label)

		self.uploader_label_group_box = QGroupBox("Автор")
		self.uploader_label_group_box.setLayout(self.uploader_label_layout)

		self.banner_right_video_info_layout = QVBoxLayout()
		self.banner_right_video_info_layout.addLayout(self.main_info_layout)
		self.banner_right_video_info_layout.addWidget(self.duration_string_group_box)
		self.banner_right_video_info_layout.addWidget(self.video_count_data_group_box)
		self.banner_right_video_info_layout.addWidget(self.uploader_label_group_box)

		self.thumbnail_label = QLabel()
		self.thumbnail_label.setFixedSize(640, 320)

		self.banner_video_info_layout = QHBoxLayout()
		self.banner_video_info_layout.addWidget(self.thumbnail_label)
		self.banner_video_info_layout.addLayout(self.banner_right_video_info_layout)

		self.video_data_widget = QWidget()
		self.video_data_widget.setLayout(self.banner_video_info_layout)

		###

		self.download_metadata_butt = QPushButton("Save all metadata (JSON)")
		self.download_metadata_butt.clicked.connect(self.download_metadata_butt_clicked)

		self.download_video_butt = QPushButton("Download in video format (MP4)")
		self.download_video_butt.clicked.connect(self.download_video_butt_clicked)

		self.download_audio_butt = QPushButton("Download in audio format (MP3)")
		self.download_audio_butt.clicked.connect(self.download_audio_butt_clicked)

		self.download_butt_layout = QHBoxLayout()
		self.download_butt_layout.addWidget(self.download_metadata_butt)
		self.download_butt_layout.addWidget(self.download_video_butt)
		self.download_butt_layout.addWidget(self.download_audio_butt)

		###

		self.download_progress_bar = QProgressBar()
		self.download_progress_bar.setValue(0)

		###

		self.video_downloader_layout = QVBoxLayout()
		self.video_downloader_layout.addWidget(self.video_data_widget)
		self.video_downloader_layout.addLayout(self.download_butt_layout)
		self.video_downloader_layout.addWidget(self.download_progress_bar)

		self.video_downloader_widget = QWidget()
		self.video_downloader_widget.setLayout(self.video_downloader_layout)
		# self.video_downloader_widget.setVisible(False)
		self.video_downloader_widget.setEnabled(False)

		###

		self.download_group_box_layout = QVBoxLayout()
		self.download_group_box_layout.addWidget(self.video_finder_widget)
		self.download_group_box_layout.addWidget(self.video_downloader_widget)

		self.download_group_box = QGroupBox("Download")
		self.download_group_box.setLayout(self.download_group_box_layout)

		#####

		self.main_layout = QVBoxLayout()
		self.main_layout.addWidget(self.extract_group_box)
		self.main_layout.addWidget(self.download_group_box)

		# Dialog window customization
		self.central_widget = QWidget()
		self.central_widget.setLayout(self.main_layout)

		self.status_bar = QStatusBar()

		self.setWindowTitle("NYT Window")
		self.setCentralWidget(self.central_widget)
		self.setStatusBar(self.status_bar)
		# self.setMinimumSize(600, 480)

		#####

		self.loader = Loader()
		self.loader.founded.connect(self.loader_founded)
		self.loader.updated.connect(self.loader_updated)
		self.loader.finished.connect(self.loader_finished)

	def loader_founded(self, video_metadata):
		self.video_metadata = video_metadata

		# self.video_downloader_widget.setVisible(True)
		self.video_downloader_widget.setEnabled(True)

		response = get(video_metadata['thumbnail'])
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			# pixmap = pixmap.scaled(int(pixmap.width() * 0.25), int(pixmap.height() * 0.25), Qt.AspectRatioMode.KeepAspectRatio)
			pixmap = pixmap.scaled(640, 320, Qt.AspectRatioMode.KeepAspectRatio)
			self.thumbnail_label.setPixmap(pixmap)
		else:
			self.thumbnail_label.setText("Не удалось загрузить картинку")

		self.title_label.setText(video_metadata['title'])
		self.description_label.setPlainText(video_metadata['description'])
		self.upload_date_label.setText(f"Дата загрузки: {video_metadata['upload_date']}")
		self.duration_string_label.setText(video_metadata['duration_string'])
		self.view_count_label.setText(f"Количество просмотров: {video_metadata['view_count']}")
		self.like_count_label.setText(f"Количество лайков: {video_metadata['like_count']}")
		self.uploader_label.setText(f"<a href='{video_metadata['channel_url']}'>{video_metadata['uploader']}</a> ({video_metadata['channel_follower_count']} подписок)")

	def loader_updated(self, max_percent, current_percent, message):
		self.download_progress_bar.setMaximum(max_percent)
		self.download_progress_bar.setValue(current_percent)
		self.status_bar.showMessage(message)

	def loader_finished(self, message):
		self.status_bar.showMessage(message)

	def rename_check_box_state_changed(self, state):
		if state:
			self.title_label.setReadOnly(True)
		else:
			self.title_label.setReadOnly(False)

	def extract_audio_check_box_state_changed(self, state):
		if state:
			self.download_audio_butt.setDisabled(True)
		else:
			self.download_audio_butt.setDisabled(False)

	def source_combo_box_current_text_changed(self, state):
		if state == "video":
			self.url_label.setText("https://www.youtube.com/watch?v=")
			self.source_check_box.setVisible(False)
		else:
			self.url_label.setText("https://www.youtube.com/playlist?list=")
			self.source_check_box.setVisible(True)

	def source_check_box_state_changed(self, state):
		if state:
			self.video_data_widget.setVisible(True)
		else:
			self.video_data_widget.setVisible(False)

	def find_video_butt_clicked(self):
		self.loader.submit_find_video(
			self.url_line_edit.text()
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
		# with open(f"{converted_string}.json", "w", encoding="utf-8") as json_file:
		# 	json.dump(self.video_metadata, json_file, indent=4)

	def download_video_butt_clicked(self):  # download_playlist()
		self.loader.submit_download_video(
			self.url_line_edit.text(),
			self.title_label.text(),
			f"{self.video_metadata['title']}.mp4",
			self.quality_combo_box.currentText(),
			self.logging_check_box.isChecked(),
			self.extract_audio_check_box.isChecked(),
			self.logging_check_box.isChecked()
		)

	def extract_audio_butt_clicked(self):  # extract_audio
		self.loader.submit_download_audio(
			self.url_line_edit.text(),
			self.logging_check_box.isChecked()
		)

	def download_audio_butt_clicked(self):  # download_audio_from_playlist()
		self.loader.submit_extract_audio(
			self.logging_check_box.isChecked()
		)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	ui = NYTDialogWindow()
	ui.show()
	sys.exit(app.exec())
