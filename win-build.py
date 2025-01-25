import os
import subprocess
import shutil

def build_executable():
    print("Building LaraLog executable...")
    
    # Clean up previous builds
    for path in ['build', 'dist']:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    # Build command with fixed options
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name=LaraLog',
        'lara_log_watcher.py'
    ]
    
    try:
        subprocess.run(cmd, check=True)
        
        # Clean up spec file
        if os.path.exists('LaraLog.spec'):
            os.remove('LaraLog.spec')
        
        print("\nBuild completed!")
        print("Executable: dist/LaraLog.exe")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure PyInstaller is installed (pip install pyinstaller)")

if __name__ == '__main__':
    build_executable() 