#!/usr/bin/python
import subprocess

subprocess.call(['mkdir', 'env'])

subprocess.call(['virtualenv', 'env'])
subprocess.call(['env/bin/pip', 'install', 'trello'])
