import os
import subprocess
import shutil

def build_executable():
    print("Building Laravel Log Watcher executable...")
    
    # Clean up previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Build command
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name=LaraLogWatcher',
        '--icon=app.ico',  # Will be ignored if icon doesn't exist
        '--add-data=recent_files.json;.',  # Include recent files if it exists
        'lara_log_watcher.py'
    ]
    
    try:
        subprocess.run(cmd, check=True)
        
        # Clean up PyInstaller files
        if os.path.exists('LaraLogWatcher.spec'):
            os.remove('LaraLogWatcher.spec')
        
        print("\nBuild completed successfully!")
        print("Executable location: dist/LaraLogWatcher.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError during build: {e}")
        print("\nMake sure you have PyInstaller installed:")
        print("pip install pyinstaller")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == '__main__':
    build_executable() 