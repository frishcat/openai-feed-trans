# OpenAI Feed Trans

`Ver 0.1`

Recently, after the release of the `openai-gtp3.5-turbo` API, I thought it would be very convenient if it could be used to automatically translate foreign RSS feeds that are difficult to read and update them using my RSS reader as a subscription. Since I just started learning Python, I tried to generate some code with the help of chatGPT. After a few days of tinkering, it actually worked!

If someone also wants to translate RSS feeds and has their own www server, you are welcome to use it. Please note that OpenAI Feed Trans is only a small tool for personal use. Do not publicly release translated subscription sources, as this may cause copyright issues.

When using it, you need to have your own OpenAI API-KEY.

# Basic Features

- Read a remote RSS feed
- Use OpenAI to translate the entire feed, while preserving the original RSS styles
- Generate a new translated feed and save it to a specified path (such as wwwroot)
- With system scheduled tasks, it can check whether the source feed has been updated periodically. It has caching functionality, so it only translates new entries and will not repeatedly consume tokens
- When the program fails, it will resume translation from the breakpoint of the incomplete entry
- The log records all consumed tokens

# Usage

1. Install `python 3.10` (other versions have not been tested)
2. Install dependencies with `pip install -r requirements.txt`(or in a virtual environment)
3. Modify `config.ini` for configuration. Please ensure that the working directory has the corresponding read and write permissions
Run `python3 src/main.py`
Set a system scheduled task to automatically check the source feed for automatic translation updates.
