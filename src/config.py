# Author: frish
# Website: https://fri.sh
# Version: 0.1a
#
# This file reads the config.ini file and sets the variables accordingly.
#
# 0.1a update:
# - Move setup paths code to config.py from main.py

import os
import logging
import configparser


d = configparser.ConfigParser()
d.read('config.ini')

# - env
os.environ["http_proxy"] = d['env']['http_proxy']
os.environ["https_proxy"] = d['env']['https_proxy']

# - source
RSS_URL = d['source']['rss_url']

# - OpenAI
API_KEY = d['openai']['api-key']
PROMPT_PREFIX = d['openai']['prompt_prefix']
MAX_RETRY = int(d['openai']['max_retry'])
MAX_TOKENS = int(d['openai']['max_tokens'])
WAIT_TIME = float(d['openai']['wait_time'])  
OPENAI_MODEL = d['openai']['model']
OPENAI_TEMPERATURE = float(d['openai']['temperatur']) 

# - Local Setup
CACHE_DIR = d['local']['cache_dir']
SPLITS_CACHE_FILENAME = 'ai_request_cache.json'
CACHE_FILENAME = d['local']['cache_filename']
LOG_DIR = d['local']['log_dir']
TMP_DIR = d['local']['tmp_dir']
OUTPUT_DIR = d['local']['output_dir']
OUTPUT_FILENAME = d['local']['output_filename']

# - Logging Setup
LOGGING_LEVEL=eval(d['logging']['level'])

# - Setup paths
if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR)

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)

if not os.path.exists(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)