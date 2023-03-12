# !/usr/bin/env python3

# OpenAI Feed Trans
# Author: frish
# Website: https://fri.sh
# Version: 0.1
#
# This script reads a remote RSS feed, uses OpenAI to perform translation, and then generates a new RSS feed
# that is stored at a specified location. It supports resuming translation from where it left off, as well
# as caching of OpenAI requests.


import os
import re
import logging
import time
import json
import shutil
import hashlib
import requests
import feedparser
import openai
from feedgen.feed import FeedGenerator
from feedgen.entry import FeedEntry
from config import *

def split_content(content, max_tokens):
    """
    This function splite an entry into little part strings,
    to avoid OpenAI API request out of max tokens.
    by the way, this piece of code gen by chatGPT T_T
    """

    # 根据换行符将内容拆分成段落
    paragraphs = content.split('\n')

    # 初始化结果数组和当前段落
    result = []
    current_paragraph = ''

    # 遍历每个段落
    for p in paragraphs:
        # 如果当前段落为空，则将其设置为当前段落
        if not current_paragraph:
            current_paragraph = p
        # 如果当前段落加上下一个句子的长度小于等于max_tokens，则将其加入当前段落
        elif len(current_paragraph) + len(p) + 1 <= max_tokens:
            current_paragraph += ' ' + p
        else:
            # 将当前段落加入结果数组
            result.append(current_paragraph)
            current_paragraph = p

    # 如果还有剩余的段落，则将其加入结果数组
    if current_paragraph:
        result.append(current_paragraph)

    # 将结果数组中的段落合并成一篇文章，并保证不将一句完整的句子分割
    final_result = []
    current_sentence = ''
    for p in result:
        # 使用正则表达式将段落拆分成句子
        sentences = re.split(r'(?<=[^A-Z].[.?!]) +(?=[A-Z])', p)
        for s in sentences:
            # 如果当前句子为空，则将其设置为当前句子
            if not current_sentence:
                current_sentence = s
            # 如果当前句子加上下一个句子的长度小于等于max_tokens，则将其加入当前句子
            elif len(current_sentence) + len(s) + 1 <= max_tokens:
                current_sentence += ' ' + s
            else:
                # 将当前句子加入结果数组
                final_result.append(current_sentence)
                current_sentence = s

    # 如果还有剩余的句子，则将其加入结果数组
    if current_sentence:
        final_result.append(current_sentence)

    return final_result
    
class OpenAITranslator():

    def __init__(self, model = "gpt-3.5-turbo", max_retry=5, wait_time=1, temperature=0.5, max_tokens=3000):
        self.__openai = openai
        self.__openai.api_key = API_KEY
        self.__max_retry = max_retry
        self.__wait_time = wait_time
        self.__temperature = temperature
        self.__max_tokens = max_tokens
        self.__model = model
        self.__prompt_prefix = PROMPT_PREFIX
        self.total_token_count = self.load_token_count()
        self.token_count = 0

    def prompt_token_count(self, prompt):
        return round(len(prompt) / 4) + 1

    def load_token_count(self):
        log_file = os.path.join(LOG_DIR, 'token_count.txt')
        if os.path.exists(log_file):
            with open(log_file) as f:
                i = f.read()
                if i:
                    return int(i)
                else:
                    return 0
        else:
            return 0

    def save_token_count(self, result):
        self.token_count += result.usage.total_tokens
        self.total_token_count += result.usage.total_tokens

        log_file = os.path.join(LOG_DIR, 'token_count.txt')
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

        with open(log_file, 'w') as f:
            f.write(str(self.total_token_count))

    def __request(self, prefix, prompt):
        retry_count = 0
        while retry_count < self.__max_retry:
            try:
                logging.debug(f"request openAI, cost about ({self.prompt_token_count(prompt) * 2}) tokens")
                result = openai.ChatCompletion.create(
                    model=self.__model,
                    messages=[
                        {"role": "system", "content": "你是一个翻译家"},
                        {"role": "user", "content": prefix},
                        {"role": "user", "content": prompt}
                    ],
                    # prompt=prefix + prompt,
                    max_tokens=self.__max_tokens,
                    temperature=self.__temperature
                )
                logging.info(f"Response OK. prompt_tokens: {result.usage.prompt_tokens}, completion_tokens: {result.usage.completion_tokens}, total_tokens: {result.usage.total_tokens}")
                
                self.save_token_count(result)
                return result.choices[0].message.content

            except openai.error.APIError as e:
                if e.status_code == 500:  # "Internal server error"
                    logging.warning(f"API Internal server error ({e.status_code}): {e.message})")
                    logging.warning(f"Retrying... ({retry_count + 1}/{self.__max_retry})")
                    time.sleep(self.__wait_time)
                    retry_count += 1
                else:
                    logging.error(f"API Error, return origin prompt")
                    return prompt
        else:
            logging.error(f"API Error: Failed after {self.max_retry} retries, return origin prompt")
            return prompt

    def translate(self, content):
        return self.__request(self.__prompt_prefix, content)

class Cache():
    def __init__(self) -> None:
        self.__entries = None
        self.__splits = {}
        self.__urls = []
        self.__splits_cache_file = os.path.join(CACHE_DIR, SPLITS_CACHE_FILENAME)
        self.__cache_file = os.path.join(CACHE_DIR, CACHE_FILENAME)
        self.updated = time.strptime("2023-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        self.__load()

    def __load(self):
        if os.path.exists(self.__splits_cache_file):
            with open(self.__splits_cache_file, 'r') as f:
                self.__splits = json.load(f)
                logging.debug(f"Local splits cache loaded ({self.__splits_cache_file}).")

        if os.path.exists(self.__cache_file):
            d = feedparser.parse(self.__cache_file) 
            self.__entries = d.entries
            self.updated = d.feed.updated_parsed
            self.__urls = [ e.link for e in d.entries ]
            logging.debug(f"Local cache feed loaded ({self.__cache_file}), last update in {d.feed.updated}")

    def count(self):
        return len(self.__entries)

    def splits(self, content):
        md5 = hashlib.md5()
        md5.update(content.encode('utf-8'))
        hashtag = md5.hexdigest()
        if hashtag in self.__splits.keys():
            return self.__splits[hashtag]

    def save_splits(self, content, translated_content):
        md5 = hashlib.md5()
        md5.update(content.encode('utf-8'))
        hashtag = md5.hexdigest()
        self.__splits[hashtag] = translated_content
        with open(self.__splits_cache_file, 'w') as f:
            json.dump(self.__splits, f, indent=2)
            

    def clean_splits(self):
        self.__splits = {}
        os.remove(self.__splits_cache_file)
    
    def cached(self, url):
        return url in self.__urls

    def add(self, url):
        self.__urls.append(url)

    def content(self,url):
        
        index = [i for i, d in enumerate(self.__entries) if d.get('link') == url][0]
        content = self.__entries[index].content[0].value
        type = self.__entries[index].content[0].type

        return (content, type)


class Feed():
    def __init__(self):
        self.__translated_entries = []
        self.__translator = OpenAITranslator()
        self.__cache = Cache()
        self.__loaded = False
        self.__translator = OpenAITranslator(
            model=OPENAI_MODEL,
            max_retry=MAX_RETRY,
            wait_time=WAIT_TIME,
            temperature=OPENAI_TEMPERATURE,
            max_tokens=MAX_TOKENS
        )

    def load(self, url):
        try:
            feed = requests.get(url)
            if feed.status_code == 200:
                tmp_path = os.path.join(TMP_DIR, 'openai_feed_trans_get_feed.xml')
                with open(tmp_path, 'wb') as f:
                    f.write(feed.content)

                self.__source_feed = feedparser.parse(tmp_path)
                if self.__source_feed.feed:
                    self.__loaded = True
                    logging.info(f"Load source feed succeed, from {url}.")
                    return True
                else:
                    logging.error(f"Load source failed, from {url}, Exception: Bad Feed.")
            else:
                logging.error(f"Load source failed, from {url}, Exception: HTTP status code {feed.status_code}")
        except Exception as e:
            logging.error(f"Load source failed, from {url}, Exception: {e}")
        
    def is_new_updated(self):
        new_date = self.__source_feed.feed.updated_parsed
        cache_date = self.__cache.updated
        return new_date > cache_date
    
    def is_unfinished(self):
        new_feed_count = len(self.__source_feed.entries)
        logging.info(f"Last time work is unfinished...")
        return new_feed_count > self.__cache.count()

    def __clone_to_feedgen_entry(self, feed_parser_entry):
        # Clone from feedParser entry type to feedGen entry type
        # Without content
        entry = feed_parser_entry
        
        new_entry = FeedEntry()
        new_entry.title(entry.title)
        new_entry.link(entry.links)
        new_entry.author(entry.authors)
        new_entry.published(entry.published)
        new_entry.id(entry.id)
        new_entry.summary(entry.summary)
        new_entry.pubDate(entry.published)
        new_entry.description(None, True)

        return new_entry

    def translate_entries(self):
        if not self.__loaded: raise "Source not loaded, use it before load()"

        entries = self.__source_feed.entries
        cache = self.__cache

        for entry in entries:
            url = entry.link
            new_entry = self.__clone_to_feedgen_entry(entry)

            if cache.cached(url):
                new_entry.content(cache.content(url)[0], None, cache.content(url)[1])
                logging.debug(f"Entry \"{entry.title}\" already cached.")
            else:
                splited_contents = split_content(entry.content[0].value, MAX_TOKENS)
                translated_content = ""
                logging_index = 0
                logging_cached = ''
                for content in splited_contents:
                    split_cache = cache.splits(content)
                    if split_cache:
                        c = split_cache
                        logging_cached = '(Cached)'
                    else:
                        c = self.__translator.translate(content)
                        cache.save_splits(content, c)
                        logging_cached = ''

                    translated_content += c

                    logging_index += 1
                    logging.info(f"{logging_cached} Entry \"{entry.title}\" Translateing... ({logging_index}/{len(splited_contents)})")

                logging.info(f"Entry \"{entry.title}\" Translated.")
                new_entry.content(translated_content, None, entry.content[0].type)
                cache.clean_splits()
            
            self.__translated_entries.append(new_entry)
            self.save(os.path.join(CACHE_DIR, CACHE_FILENAME))

        logging.info(f"All done. Token cost this time: {self.__translator.token_count}") 

    def save(self, url):
        feed = self.__source_feed.feed
        entries = self.__source_feed.entries

        # Set feed header
        fg = FeedGenerator()
        fg.title(feed.title)
        fg.subtitle(feed.subtitle)
        fg.link(href=feed.link)
        fg.description(feed.description)
        fg.logo(feed.image.href)
        fg.pubDate(feed.updated)
        fg.lastBuildDate(feed.updated)
        fg.generator('AI-TransRSS', '0.1', 'https://fri.sh')
        fg.language("zh-CN")

        image = feed.image
        fg.image(url=image.href, title=image.title, link=image.link, width=str(image.width),height=str(image.height))

        # Set entries
        for entry in self.__translated_entries:
            fg.add_entry(entry, order='append') 
        
        # Save to file
        fg.rss_file(url)

if __name__ == '__main__':
    logging.basicConfig(
        level=LOGGING_LEVEL,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(LOG_DIR, "openai_feed_trans.log"))
        ]
    )

    logging.info(f"-----------------------------------------------")  
    logging.info(f"OpenAIFeedTrans start.") 

    ai = OpenAITranslator()

    feed = Feed()
    if feed.load(RSS_URL):
        if feed.is_new_updated() or feed.is_unfinished():
            feed.translate_entries()
        
            # Copy the translated feed to your web dir
            if not os.path.exists(OUTPUT_DIR):
                os.mkdir(OUTPUT_DIR)

            # Copy the translated feed to your web dir
            if not os.path.exists(CACHE_DIR):
                os.mkdir(CACHE_DIR)

            shutil.copy(os.path.join(CACHE_DIR, CACHE_FILENAME), os.path.join(OUTPUT_DIR, OUTPUT_FILENAME))
        else:
            logging.info(f"Source feed is not updated, bye.")
 
 
   