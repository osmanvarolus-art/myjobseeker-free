@echo off
REM Start MyJobSeeker and open it in your browser. Needs Python 3.10 or newer.
cd /d "%~dp0"
py -3 app\myjobseeker.py --open || python app\myjobseeker.py --open
