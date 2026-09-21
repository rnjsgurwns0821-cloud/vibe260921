"""
네이버 뉴스 크롤러 - PyQt6 GUI 버전

기능:
- 검색 URL 입력 후 크롤링 시작
- 크롤링 진행 상황을 진행바로 표시 (백그라운드 스레드에서 실행하여 UI 멈춤 방지)
- 결과를 표(제목/언론사/기자/작성일)로 표시
- 표에서 행을 선택하면 해당 기사 본문을 오른쪽에 표시
- 결과를 CSV로 저장

필요 패키지: requests, beautifulsoup4, PyQt6 (모두 requirements.txt에 포함)
    pip install -r requirements.txt
실행: python naver_news_crawler_gui.py
"""

import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from naver_news_crawler import (
    SEARCH_URL,
    get_article_links,
    get_preview_articles,
    parse_article,
    save_to_csv,
    save_to_excel,
)

COLUMNS = ["제목", "언론사", "기자", "작성일"]


class CrawlerThread(QThread):
    """기사 링크 수집 및 개별 기사 파싱을 백그라운드에서 수행하는 스레드."""

    progress = pyqtSignal(int, int)          # (현재, 전체)
    article_found = pyqtSignal(dict)         # 기사 하나가 파싱될 때마다 발생
    log = pyqtSignal(str)
    finished_all = pyqtSignal(list)          # 전체 기사 리스트
    error = pyqtSignal(str)

    def __init__(self, search_url, preview_mode=False, parent=None):
        super().__init__(parent)
        self.search_url = search_url
        self.preview_mode = preview_mode
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        if self.preview_mode:
            self._run_preview()
        else:
            self._run_full()

    def _run_preview(self):
        """검색결과 페이지만 접속하여 미리보기 정보(제목/언론사/링크/요약)를 수집한다."""
        try:
            previews = get_preview_articles(self.search_url)
        except Exception as e:
            self.error.emit(f"검색 페이지를 불러오지 못했습니다:\n{e}")
            return

        self.log.emit(f"수집된 미리보기 기사 수: {len(previews)}")

        articles = []
        total = len(previews)
        for i, preview in enumerate(previews, start=1):
            if self._stop_requested:
                self.log.emit("사용자 요청으로 중단되었습니다.")
                break
            article = {
                "title": preview["title"],
                "press": preview["press"],
                "reporter": "",
                "published_at": preview["published"],
                "url": preview["naver_url"] or preview["url"],
                "content": preview["snippet"],
            }
            articles.append(article)
            self.article_found.emit(article)
            self.progress.emit(i, total)

        self.finished_all.emit(articles)

    def _run_full(self):
        try:
            links = get_article_links(self.search_url)
        except Exception as e:
            self.error.emit(f"검색 페이지를 불러오지 못했습니다:\n{e}")
            return

        self.log.emit(f"수집된 기사 링크 수: {len(links)}")

        articles = []
        total = len(links)
        for i, link in enumerate(links, start=1):
            if self._stop_requested:
                self.log.emit("사용자 요청으로 중단되었습니다.")
                break
            try:
                article = parse_article(link)
                articles.append(article)
                self.article_found.emit(article)
            except Exception as e:
                self.log.emit(f"크롤링 실패: {link} ({e})")
            self.progress.emit(i, total)

        self.finished_all.emit(articles)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1100, 650)

        self.articles = []
        self.thread = None

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # 상단: URL 입력 + 버튼
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("검색 URL:"))
        self.url_input = QLineEdit(SEARCH_URL)
        top_row.addWidget(self.url_input, stretch=1)

        self.start_btn = QPushButton("크롤링 시작")
        self.start_btn.clicked.connect(self.start_crawl)
        top_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("중단")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_crawl)
        top_row.addWidget(self.stop_btn)

        self.save_csv_btn = QPushButton("CSV로 저장")
        self.save_csv_btn.setEnabled(False)
        self.save_csv_btn.clicked.connect(self.save_csv)
        top_row.addWidget(self.save_csv_btn)

        self.save_excel_btn = QPushButton("엑셀로 저장")
        self.save_excel_btn.setEnabled(False)
        self.save_excel_btn.clicked.connect(self.save_excel)
        top_row.addWidget(self.save_excel_btn)

        root.addLayout(top_row)

        self.preview_checkbox = QCheckBox(
            "미리보기 모드 (검색결과 목록만 빠르게 수집, 기사 본문/기자명 없음)"
        )
        root.addWidget(self.preview_checkbox)

        # 진행바 + 상태
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("대기 중")
        root.addWidget(self.status_label)

        # 본문: 좌측 표 / 우측 본문 미리보기
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected_content)
        splitter.addWidget(self.table)

        self.content_view = QTextEdit()
        self.content_view.setReadOnly(True)
        self.content_view.setPlaceholderText("표에서 기사를 선택하면 본문이 여기에 표시됩니다.")
        splitter.addWidget(self.content_view)

        splitter.setSizes([650, 450])
        root.addWidget(splitter, stretch=1)

    # ---------- 크롤링 ----------

    def start_crawl(self):
        search_url = self.url_input.text().strip()
        if not search_url:
            QMessageBox.warning(self, "입력 오류", "검색 URL을 입력해주세요.")
            return

        self.articles = []
        self.table.setRowCount(0)
        self.content_view.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("크롤링 준비 중...")

        self.start_btn.setEnabled(False)
        self.save_csv_btn.setEnabled(False)
        self.save_excel_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.thread = CrawlerThread(search_url, preview_mode=self.preview_checkbox.isChecked())
        self.thread.progress.connect(self.on_progress)
        self.thread.article_found.connect(self.on_article_found)
        self.thread.log.connect(self.on_log)
        self.thread.finished_all.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def stop_crawl(self):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.stop_btn.setEnabled(False)
            self.status_label.setText("중단 요청됨...")

    def on_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"크롤링 중... ({current}/{total})")

    def on_article_found(self, article):
        self.articles.append(article)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(article["title"]))
        self.table.setItem(row, 1, QTableWidgetItem(article["press"]))
        self.table.setItem(row, 2, QTableWidgetItem(article["reporter"]))
        self.table.setItem(row, 3, QTableWidgetItem(article["published_at"]))

    def on_log(self, message):
        self.status_label.setText(message)

    def on_finished(self, articles):
        self.status_label.setText(f"완료: 총 {len(articles)}건 수집")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        has_articles = len(articles) > 0
        self.save_csv_btn.setEnabled(has_articles)
        self.save_excel_btn.setEnabled(has_articles)

    def on_error(self, message):
        QMessageBox.critical(self, "오류", message)
        self.status_label.setText("오류 발생")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ---------- 결과 확인/저장 ----------

    def show_selected_content(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        index = rows[0].row()
        if index >= len(self.articles):
            return
        article = self.articles[index]
        header = (
            f"제목: {article['title']}\n"
            f"언론사: {article['press']}   기자: {article['reporter']}   작성일: {article['published_at']}\n"
            f"URL: {article['url']}\n"
            + "-" * 60
            + "\n\n"
        )
        self.content_view.setPlainText(header + article["content"])

    def save_csv(self):
        if not self.articles:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", "naver_news_result.csv", "CSV Files (*.csv)"
        )
        if not filename:
            return
        try:
            save_to_csv(self.articles, filename)
            QMessageBox.information(self, "저장 완료", f"저장되었습니다:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))

    def save_excel(self):
        if not self.articles:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "엑셀로 저장", "naver_news_result.xlsx", "Excel Files (*.xlsx)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"
        try:
            save_to_excel(self.articles, filename)
            QMessageBox.information(self, "저장 완료", f"저장되었습니다:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", str(e))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
