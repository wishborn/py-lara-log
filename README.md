# Laravel Log Watcher

A Python application for monitoring Laravel log files in real-time with filtering capabilities.

## Features

- Real-time log file monitoring
- Filter logs by Laravel log levels (emergency, alert, critical, error, warning, notice, info, debug)
- Start/Stop watching functionality
- Clear display option
- Modern Qt-based user interface

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
2. Use the checkboxes to filter specific log levels
3. Click "Start Watching" to begin monitoring the log file
4. Use "Clear Display" to clear the log display
5. Click "Stop Watching" to pause monitoring

## Requirements

- Python 3.7+
- PyQt6
- watchdog 