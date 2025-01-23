# Laravel Log Watcher

A Python application for monitoring Laravel log files in real-time with filtering capabilities.

## Features

- Real-time log file monitoring
- Table-based log display with columns for Time, Type, and Message
- Expandable details view showing full stack traces and JSON data
- Filter logs by Laravel log levels (emergency, alert, critical, error, warning, notice, info, debug)
- Start/Stop watching functionality
- Clear display option
- Empty log file option (with confirmation)
- Modern Qt-based user interface with splitter for adjustable views

## Installation

1. Clone this repository
2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development Mode
```bash
python lara_log_watcher.py
```

### Creating Executable
To create a standalone executable:
```bash
pyinstaller --onefile --windowed lara_log_watcher.py
```

The executable will be created in the `dist` directory.

## Usage

1. Click "Select Log File" to choose your Laravel log file
2. Use the checkboxes to filter specific log levels (filters update in real-time)
3. Click "Start Watching" to begin monitoring the log file
4. Click on any log entry to view its full details in the bottom panel
5. Use "Clear Display" to clear the current view (doesn't affect the log file)
6. Use "Empty Log" to delete all contents of the log file (requires confirmation)
7. Click "Stop Watching" to pause monitoring

## Requirements

- Python 3.7+
- PyQt5
- watchdog 