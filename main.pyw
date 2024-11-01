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

from yt_dlp import YoutubeDL
import json

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QLabel, QLineEdit, QCheckBox, QProgressBar, QComboBox, QPushButton, QPlainTextEdit, QMessageBox, QStatusBar
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

# todo
#  1. Сделать переименование видео после загрузки
#  2. Добавить комбобокс выбора типа источника (видео или плейлист)
#  2. Завершить реализацию загрузки плейлистов:
#  2.1. После каждого видео останавливаться на подтверждение загрузки и указание имени файла
#  2.2. Добавить настройки, выключающие переименование и добавляющие быструю загрузку
#  3. Поработать над интерфейсом программы
#  4. Провести рефакторинг кода

class NYTDialogWindow(QMainWindow):
	def __init__(self):
		super(NYTDialogWindow, self).__init__()

		#####

		self.extract_audio_butt = QPushButton("Extract audio from all .mp4 files in this directory")
		self.extract_audio_butt.clicked.connect(self.extract_audio_butt_clicked)

		self.extract_group_box_layout = QVBoxLayout()
		self.extract_group_box_layout.addWidget(self.extract_audio_butt)

		self.extract_group_box = QGroupBox("Extract")
		self.extract_group_box.setLayout(self.extract_group_box_layout)

		#####

		self.url_line_edit = QLineEdit()
		self.url_line_edit.setPlaceholderText("Enter the video or playlist URL")

		self.quality_combo_box = QComboBox()
		self.quality_combo_box.addItems(["720", "1080"])

		self.extract_audio_check_box = QCheckBox("Extract audio before download videos?")
		self.extract_audio_check_box.stateChanged.connect(self.extract_audio_check_box_state_changed)

		self.logging_check_box = QCheckBox("Enable logging?")

		self.url_layout = QHBoxLayout()
		self.url_layout.addWidget(self.url_line_edit)
		self.url_layout.addWidget(self.quality_combo_box)
		self.url_layout.addWidget(self.extract_audio_check_box)
		self.url_layout.addWidget(self.logging_check_box)

		self.find_video_butt = QPushButton("Find video")
		self.find_video_butt.clicked.connect(self.find_video_butt_clicked)

		self.video_finder_layout = QVBoxLayout()
		self.video_finder_layout.addLayout(self.url_layout)
		self.video_finder_layout.addWidget(self.find_video_butt)

		self.video_finder_widget = QWidget()
		self.video_finder_widget.setLayout(self.video_finder_layout)

		###

		self.title_label = QLineEdit()
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
		self.video_downloader_widget.setVisible(False)

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

	def extract_audio_check_box_state_changed(self, state):
		if state:
			self.download_audio_butt.setDisabled(True)
		else:
			self.download_audio_butt.setDisabled(False)

	def download_progress_bar_update_value(self, new_value):
		if new_value['status'] == 'downloading':
			self.download_progress_bar.setMaximum(new_value['total_bytes'])
			self.download_progress_bar.setValue(new_value['downloaded_bytes'])
			self.status_bar.showMessage(new_value['_percent_str'])

	def find_video_butt_clicked(self):
		ydl_opts = {
			'quiet': True,  # Отключает лишние сообщения в консоли
			'no_warnings': True,
		}
		with YoutubeDL(ydl_opts) as ydl:
			info = ydl.extract_info(self.url_line_edit.text(), download=False)  # Только извлекает информацию

		self.video_downloader_widget.setVisible(True)

		response = get(info['thumbnail'])
		if response.status_code == 200:
			pixmap = QPixmap()
			pixmap.loadFromData(response.content)
			# pixmap = pixmap.scaled(int(pixmap.width() * 0.25), int(pixmap.height() * 0.25), Qt.AspectRatioMode.KeepAspectRatio)
			pixmap = pixmap.scaled(640, 320, Qt.AspectRatioMode.KeepAspectRatio)
			self.thumbnail_label.setPixmap(pixmap)
		else:
			self.thumbnail_label.setText("Не удалось загрузить картинку")

		self.title_label.setText(info['title'])
		self.description_label.setPlainText(info['description'])
		self.upload_date_label.setText(f"Дата загрузки: {info['upload_date']}")
		self.duration_string_label.setText(info['duration_string'])
		self.view_count_label.setText(f"Количество просмотров: {info['view_count']}")
		self.like_count_label.setText(f"Количество лайков: {info['like_count']}")
		self.uploader_label.setText(f"<a href='{info['channel_url']}'>{info['uploader']}</a> ({info['channel_follower_count']} подписок)")

	def download_metadata_butt_clicked(self):
		ydl_opts = {
			'quiet': True,  # Отключает лишние сообщения в консоли
			'no_warnings': True,
		}
		with YoutubeDL(ydl_opts) as ydl:
			info = ydl.extract_info(self.url_line_edit.text(), download=False)  # Только извлекает информацию

		print(info)
		with open("info.json", "w", encoding="utf-8") as file:
			json.dump(info, file, indent=4)

	def download_video_butt_clicked(self):  # download_playlist()
		ydl_opts = {
			"format": f"best[height<={self.quality_combo_box.currentText()}]",
			"quiet": not self.logging_check_box.isChecked(),
			"output": "%(title)s.%(ext)s",
			"progress_hooks": [self.download_progress_bar_update_value],
		}
		try:
			with YoutubeDL(ydl_opts) as ydl:
				ydl.download([self.url_line_edit.text()])
				self.status_bar.showMessage("[+] Video from playlist has been downloaded")
		except Exception as err:
			self.status_bar.showMessage(f"[✗] ERROR: Downloading error {err}")

		if self.extract_audio_check_box.isChecked():
			self.extract_audio_butt_clicked()

	def extract_audio_butt_clicked(self):  # extract_audio
		for file in listdir():
			if file.endswith(".mp4"):
				command = [
					"ffmpeg",  # Путь к ffmpeg (если он не в PATH)
					"-i", file,  # Входное видео
					"-vn",  # Опция для указания, что нужно только аудио
					"-acodec", "libmp3lame",  # Копирование аудио без перекодирования
					"-ab", "192k",  # Установка битрейта аудио
					file.replace(".mp4", ".mp3")  # Выходное аудио
				]
				try:
					if self.logging_check_box.isChecked():
						run(command, check=True)
					else:
						run(command, capture_output=True, check=True)
					self.status_bar.showMessage(f"[✓] File {file} converted successfully")
				except CalledProcessError as err:
					self.status_bar.showMessage(f"[✗] ERROR: File {file} could not be converted {err}")
			else:
				self.status_bar.showMessage(f"[-] Ignored the '{file}'")

	def download_audio_butt_clicked(self):  # download_audio_from_playlist()
		ydl_opts = {
			"format": "bestaudio/best",
			"quiet": not self.logging_check_box.isChecked(),
			"output": "%(title)s.%(ext)s",
			"progress_hooks": [self.download_progress_bar_update_value],
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
				ydl.download([self.url_line_edit.text()])
				self.status_bar.showMessage("[+] Audio from playlist has been downloaded")
		except Exception as err:
			self.status_bar.showMessage(f"[✗] ERROR: Downloading error {err}")

if __name__ == '__main__':
	app = QApplication(sys.argv)
	ui = NYTDialogWindow()
	ui.show()
	sys.exit(app.exec())
