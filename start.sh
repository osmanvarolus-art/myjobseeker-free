#!/usr/bin/env sh
# Start MyJobSeeker and open it in your browser. Needs Python 3.10 or newer, nothing else.
cd "$(dirname "$0")" && exec python3 app/myjobseeker.py --open
