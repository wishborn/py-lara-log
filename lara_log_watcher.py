import sys
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                           QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
                           QHeaderView, QTextBrowser, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json

# Constants
MAX_RECENT_FILES = 10

# Legacy path for backward compatibility with older versions
LEGACY_RECENT_FILES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'recent_files.json'
)

def get_config_path():
    """
    Determine the path to the laralog.config file.

    Why this function exists: The app previously stored recent files in
    `recent_files.json` next to the script. We now need to store and
    automatically update `laralog.config` in the same folder the LaraLog
    executable is launched from. When running as a PyInstaller executable,
    we use the executable's directory. During development, we use the
    current working directory to mimic the behavior of "where it's fired from".
    """
    try:
        # When frozen by PyInstaller, use the directory of the executable
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            # In development, prefer the current working directory
            base_dir = os.getcwd()
    except Exception:
        base_dir = os.getcwd()

    return os.path.join(base_dir, 'laralog.config')

class LogEntry:
    def __init__(self, timestamp, level, message, details=None):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.details = details or ""
        
    @staticmethod
    def parse_log_entry(log_line):
        try:
            # Extract timestamp and level using regex
            match = re.match(r'\[(.*?)\] \w+\.(\w+): (.*)', log_line)
            if match:
                timestamp, level, rest = match.groups()
                
                # Try to parse the JSON content
                try:
                    data = json.loads(rest)
                    # Extract the main error message (first line of exception)
                    exception_text = data.get('exception', '')
                    if exception_text:
                        # Split by newline and get first line for message
                        message = exception_text.split('\n')[0].strip()
                        # Keep the full exception text as details
                        details = exception_text
                    else:
                        # If no exception, use the entire rest as message
                        message = rest
                        # Look for other JSON fields that might be useful
                        details = json.dumps(data, indent=2)
                except json.JSONDecodeError:
                    # If not JSON, use the text as is
                    message = rest
                    details = rest
                    
                return LogEntry(timestamp, level.lower(), message, details)
        except Exception as e:
            print(f"Error parsing log entry: {e}")
            return None

class LogWatcher(QThread):
    log_updated = pyqtSignal(object)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.active = True
        self.last_position = 0
        self.filters = []
    
    def set_filters(self, filters):
        self.filters = filters
    
    def should_display_log(self, level):
        if not self.filters:
            return True
        return level.lower() in self.filters
    
    def run(self):
        while self.active:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as file:
                    file.seek(self.last_position)
                    while self.active:
                        line = file.readline()
                        if line:
                            entry = LogEntry.parse_log_entry(line.strip())
                            if entry and self.should_display_log(entry.level):
                                self.log_updated.emit(entry)
                            self.last_position = file.tell()
                        else:
                            self.msleep(100)
            else:
                self.msleep(1000)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laravel Log Watcher")
        self.setMinimumSize(1200, 800)
        
        # Load recent files
        self.recent_files = self.load_recent_files()
        # Persist any cleanup (e.g., deduplication, migration) immediately
        self.save_recent_files()
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Top controls
        top_controls = QHBoxLayout()
        
        # File selection
        file_selection_layout = QVBoxLayout()
        select_file_btn = QPushButton("Select Log File")
        select_file_btn.clicked.connect(self.select_file)
        file_selection_layout.addWidget(select_file_btn)
        
        # Recent files combo box
        self.recent_files_combo = QComboBox()
        self.recent_files_combo.addItem("Recent Files")
        self.recent_files_combo.addItems(self.recent_files)
        self.recent_files_combo.currentIndexChanged.connect(self.recent_file_selected)
        file_selection_layout.addWidget(self.recent_files_combo)
        
        top_controls.addLayout(file_selection_layout)
        
        self.file_path_label = QLabel("No file selected")
        top_controls.addWidget(self.file_path_label)
        
        # Watch control
        self.watch_btn = QPushButton("Start Watching")
        self.watch_btn.clicked.connect(self.toggle_watching)
        self.watch_btn.setEnabled(False)
        top_controls.addWidget(self.watch_btn)
        
        layout.addLayout(top_controls)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Log Levels:"))
        
        # Log level filters
        self.log_levels = ['emergency', 'alert', 'critical', 'error', 
                          'warning', 'notice', 'info', 'debug']
        self.filter_checks = {}
        
        for level in self.log_levels:
            checkbox = QCheckBox(level.capitalize())
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_filters)
            self.filter_checks[level] = checkbox
            filter_layout.addWidget(checkbox)
        
        layout.addLayout(filter_layout)
        
        # Create splitter for table and details
        splitter = QSplitter(Qt.Vertical)
        
        # Log table
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(['Time', 'Type', 'Message'])
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.itemSelectionChanged.connect(self.show_details)
        splitter.addWidget(self.log_table)
        
        # Details view
        self.details_view = QTextBrowser()
        self.details_view.setMinimumHeight(200)
        splitter.addWidget(self.details_view)
        
        layout.addWidget(splitter)
        
        # Bottom controls
        bottom_controls = QHBoxLayout()
        
        # Clear button
        clear_btn = QPushButton("Clear Display")
        clear_btn.clicked.connect(self.clear_display)
        bottom_controls.addWidget(clear_btn)
        
        # Empty Log button
        empty_log_btn = QPushButton("Empty Log")
        empty_log_btn.clicked.connect(self.empty_log_file)
        bottom_controls.addWidget(empty_log_btn)
        
        layout.addLayout(bottom_controls)
        
        self.watcher = None
        self.current_file = None
        self.watching = False
        self.log_entries = []
    
    def load_recent_files(self):
        config_path = get_config_path()
        # 1) Try the new config location first
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data = data if isinstance(data, list) else []
                    return self._dedupe_and_trim(data)
        except Exception:
            pass

        # 2) Fall back to legacy location (migrate if found)
        try:
            if os.path.exists(LEGACY_RECENT_FILES_PATH):
                with open(LEGACY_RECENT_FILES_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data = data if isinstance(data, list) else []
                data = self._dedupe_and_trim(data)
                # Save immediately to the new location to migrate
                try:
                    with open(config_path, 'w', encoding='utf-8') as nf:
                        json.dump(data, nf)
                    # Migration successful; attempt to remove legacy file
                    try:
                        os.remove(LEGACY_RECENT_FILES_PATH)
                    except Exception:
                        pass
                except Exception:
                    # Ignore write errors; we can still proceed in-memory
                    pass
                return data
        except Exception:
            pass

        return []

    def save_recent_files(self):
        config_path = get_config_path()
        try:
            # Always save a cleaned, trimmed list
            cleaned = self._dedupe_and_trim(self.recent_files)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned, f)
            self.recent_files = cleaned
        except Exception as e:
            print(f"Error saving recent files: {e}")

    def add_recent_file(self, file_path):
        # Remove any existing entries that match this path (case-insensitive on Windows)
        target_key = self._normalize_path(file_path)
        self.recent_files = [p for p in self.recent_files if self._normalize_path(p) != target_key]
        # Insert at the top and persist
        self.recent_files.insert(0, file_path)
        self.recent_files = self._dedupe_and_trim(self.recent_files)
        self.save_recent_files()
        
        # Update combo box
        self.recent_files_combo.clear()
        self.recent_files_combo.addItem("Recent Files")
        self.recent_files_combo.addItems(self.recent_files)

    def recent_file_selected(self, index):
        if index > 0 and self.recent_files_combo.currentText() != "Recent Files":
            file_path = self.recent_files_combo.currentText()
            if os.path.exists(file_path):
                self.set_current_file(file_path)
            else:
                QMessageBox.warning(self, "Warning", f"File not found:\n{file_path}")
                # Remove all duplicates of this path and persist
                target_key = self._normalize_path(file_path)
                self.recent_files = [p for p in self.recent_files if self._normalize_path(p) != target_key]
                self.save_recent_files()
                self.recent_files_combo.removeItem(index)

    def _normalize_path(self, path):
        """
        Normalize a filesystem path for duplicate comparisons.

        Why this function exists: Windows paths are case-insensitive and may
        vary in separators. Normalization ensures we prevent duplicates even if
        the same path is represented with different case or slashes.
        """
        try:
            return os.path.normcase(os.path.normpath(path))
        except Exception:
            return path

    def _dedupe_and_trim(self, files):
        """
        Remove duplicate paths (case-insensitive on Windows) while preserving
        order and enforce MAX_RECENT_FILES length.

        Why this function exists: We need a single source of truth for recent
        files without duplicates, and we must keep the list bounded.
        """
        seen = set()
        unique = []
        for p in files or []:
            if not p:
                continue
            key = self._normalize_path(p)
            if key in seen:
                continue
            seen.add(key)
            unique.append(p)
        return unique[:MAX_RECENT_FILES]

    def set_current_file(self, file_path):
        self.current_file = file_path
        self.file_path_label.setText(os.path.basename(file_path))
        self.watch_btn.setEnabled(True)
        self.add_recent_file(file_path)
        
        # If already watching, restart with new file
        if self.watching:
            self.stop_watching()
            self.start_watching()

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Laravel Log File",
            "",
            "Log Files (*.log);;All Files (*.*)"
        )
        
        if file_path:
            self.set_current_file(file_path)
    
    def update_filters(self):
        active_filters = [level for level, checkbox in self.filter_checks.items()
                         if checkbox.isChecked()]
        
        if self.watcher:
            self.watcher.set_filters(active_filters)
        
        # Update visible rows
        for row in range(self.log_table.rowCount()):
            level = self.log_table.item(row, 1).text().lower()
            self.log_table.setRowHidden(row, level not in active_filters)
    
    def toggle_watching(self):
        if not self.watching:
            self.start_watching()
        else:
            self.stop_watching()
    
    def start_watching(self):
        if self.current_file:
            self.watcher = LogWatcher(self.current_file)
            self.watcher.log_updated.connect(self.add_log_entry)
            self.update_filters()
            self.watcher.start()
            self.watching = True
            self.watch_btn.setText("Stop Watching")
    
    def stop_watching(self):
        if self.watcher:
            self.watcher.active = False
            self.watcher.wait()
            self.watcher = None
        self.watching = False
        self.watch_btn.setText("Start Watching")
    
    def add_log_entry(self, entry):
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        
        # Add items
        self.log_table.setItem(row, 0, QTableWidgetItem(entry.timestamp))
        self.log_table.setItem(row, 1, QTableWidgetItem(entry.level.upper()))
        self.log_table.setItem(row, 2, QTableWidgetItem(entry.message))
        
        # Store the full entry for details view
        self.log_entries.append(entry)
        
        # Scroll to the new row
        self.log_table.scrollToBottom()
        
        # Apply current filters
        level = entry.level.lower()
        active_filters = [level for level, checkbox in self.filter_checks.items()
                         if checkbox.isChecked()]
        self.log_table.setRowHidden(row, level not in active_filters)
    
    def show_details(self):
        selected_rows = self.log_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            entry = self.log_entries[row]
            if entry.details:
                # Format the details with proper line breaks and spacing
                formatted_details = entry.details
                if isinstance(formatted_details, str):
                    try:
                        # Try to parse and re-format JSON
                        data = json.loads(formatted_details)
                        formatted_details = json.dumps(data, indent=4)
                    except json.JSONDecodeError:
                        # If not JSON, preserve line breaks
                        formatted_details = formatted_details.replace('\\n', '\n')
                self.details_view.setPlainText(formatted_details)
            else:
                self.details_view.setPlainText("No additional details available")
    
    def clear_display(self):
        self.log_table.setRowCount(0)
        self.log_entries.clear()
        self.details_view.clear()
    
    def empty_log_file(self):
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No log file selected!")
            return
            
        reply = QMessageBox.question(
            self,
            "Empty Log File",
            f"Are you sure you want to empty the log file?\n\nThis will permanently delete all contents of:\n{self.current_file}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Stop watching if active
                was_watching = self.watching
                if was_watching:
                    self.stop_watching()
                
                # Empty the file
                with open(self.current_file, 'w') as file:
                    pass
                
                # Clear the display
                self.clear_display()
                
                # Restart watching if it was active
                if was_watching:
                    self.start_watching()
                    
                QMessageBox.information(self, "Success", "Log file has been emptied successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to empty log file:\n{str(e)}")
    
    def closeEvent(self, event):
        self.stop_watching()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 