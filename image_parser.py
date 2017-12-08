from PIL import Image
import pytesseract
import cv2
import os
import numpy as np
import sys
import webbrowser
from googleapiclient.discovery import build
from slackclient import SlackClient
from pprint import pprint
from urllib.parse import urlencode, urlparse, parse_qs
import xml.etree.ElementTree as ElementTree
import asyncio
import threading

from lxml.html import fromstring
from requests import get

import sys
from GoogleScraper import scrape_with_config, GoogleSearchError
from GoogleScraper.database import ScraperSearch, SERP, Link

#google keys
google_api_key = os.environ["HQ_GOOGLE_API_KEY"]
google_cse_id = os.environ["HQ_GOOGLE_CSE_ID"]

#slack api key
slack_token = os.environ["HQ_SLACK_TOKEN"]

sc = SlackClient(slack_token)

full_word_weight = 2
first_result_weight = 10

def google_scraper(keywords):
    # See in the config.cfg file for possible values
    config = {
        'use_own_ip': True,
        'keywords': keywords,
        'search_engines': ['google'],
        'num_pages_for_keyword': 1,
        'scrape_method': 'http',
        'do_caching': False,
        'google_sleeping_ranges': {
            1: (0, 1),
            5: (0, 2),
            30: (10, 20),
            127: (30, 50),
        },
        'log_level': 'CRITICAL'
    }

    try:
        search = scrape_with_config(config)
    except GoogleSearchError as e:
        print(e)

    # let's inspect what we got
    results = ""
    for serp in search.serps:
        # ... more attributes ...
        for link in serp.links:
            results += str(link.title) + " " + str(link.snippet)
    return results
def get_google_results(keyword):
    url = "https://www.google.com.tr/search?q={}".format(keyword.replace("&", ""))
    raw = get(url).text
    page = fromstring(raw)
    result = str(ElementTree.tostring(page, encoding='utf8', method='xml'))
    print(result)
    return result
class ImageParser():

        def process(self, file_path):
                #crop the image to remove the top and bottom of the screen to only parse out the question and answer
                #people with iphone x's might need to modify this
                image = cv2.imread(file_path)
                height = np.size(image, 0)
                width = np.size(image, 1)
                crop = image[int(height*0.15):int(height - height*0.2), 0:width]

                #performs a binary threshold(helps when the answers are grayed out when you're out of the game
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                gray = cv2.threshold(gray, 200, 255,
                        cv2.THRESH_BINARY)[1]

                if("-save" not in sys.argv[1:]):
                    os.remove(file_path)
                #creates a new file
                filename = "{}.png".format(os.getpid())
                cv2.imwrite(filename, gray)

                #this is where the OCR happens
                text = pytesseract.image_to_string(Image.open(filename))

                os.remove(filename)

                #simple split to split questions and answers, assumes the last 3 elements are answers
                split = text.split("\n\n")

                if len(split) >= 4:

                    #creates the questions from the first (length - 3) elements, probably a better way to do this but whatever
                    question = " ".join(split[:len(split) - 3]).replace("\n", " ")
                    #gets the answers from last 3 elements
                    answers = split[len(split) - 3:]
                    self.score_answers(question, answers)

        def score_answers(self, question, answers):

            self.open_browser(question, answers)
            filteredAnswers = []
            keywords = [question]
            # for i, answer in enumerate(answers):
            #     filteredAnswers.append(' '.join(filter(lambda x: x.lower() not in ["the"],  answer.split())))
            #     keywords.append(question + " " + filteredAnswers[i])

            result_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(result_loop)
            results = []
            tasks = []
            # for k, keyword in enumerate(keywords):
            #     task = asyncio.ensure_future(get_google_results(keyword, k))
            #     tasks.append(task)
            # done, _ = result_loop.run_until_complete(asyncio.wait(tasks))
            #
            # for fut in done:
            #     results.append(fut.result())
            results.append({'text': self.google_search(question, google_api_key, google_cse_id, num=9), 'index': 0})
            results.append({'text': google_scraper(keywords), 'index': 0})

            #just counts the number of times the answers appears in the results
            answer_results = [{'count': 0, 'alpha_key': 'A'}, {'count': 0, 'alpha_key': 'B'}, {'count': 0, 'alpha_key': 'C'}]
            for r, result in enumerate(results):
                for a, answer in enumerate(answers):
                    answerCount = 0
                    splitArray = [answer.lower()]
                    for i, key in enumerate(splitArray):
                        count = str(result['text']).lower().count(key)
                        original_count = count
                        if(result['index'] == 0):
                            count += original_count * first_result_weight
                        if(i == len(splitArray) - 1):
                            count += original_count * full_word_weight
                        answerCount += count
                    answer_results[a]['count'] += answerCount
            result_sum = sum(answer_result['count'] for answer_result in answer_results)

            for r, result in enumerate(results):
                for a, answer in enumerate(answers):
                    answerCount = 0
                    splitArray = self.create_answer_search_keys(answer)
                    for i, key in enumerate(splitArray):
                        count = str(result['text']).lower().count(key)/len(splitArray)
                        count *= 0.5
                        answerCount += count
                    answer_results[a]['count'] += answerCount
            result_sum = sum(answer_result['count'] for answer_result in answer_results)
            for index, answer_result in enumerate(answer_results):
                if result_sum == 0:
                    result_sum = 1
                percentage = answer_result['count']/result_sum * 100
                text = answer_result['alpha_key'] + ":'" + answers[index].lstrip() + "'(" + str(int(percentage)) + "%)"
                text2 = answer_result['alpha_key'] + "'(" + str(int(percentage)) + "%)"
                answer_result['text'] = text
                answer_result['text2'] = text2
                answer_result['percentage'] = percentage

            append_slack = ""
            for ar in answer_results:
                append_slack += ar['text2'] + " "

            slack_text = append_slack + " \n" + question + "\n"
            print(question)

            for ar in answer_results:
                slack_text += ar['text'] + "\n"
                print(ar['text'])

            if("-slack" in sys.argv[1:]):
                self.slack_message(slack_text)

        def create_answer_search_keys(self, answer):
            answerKeys = answer.split()
            if(len(answerKeys) > 1):
                answerKeys.append(answer)
            answerKeys = list(filter(lambda x: (x.lower() not in ["the"] and len(x) > 2 or x[0].isupper()), answerKeys))
            answerKeys = list(map(lambda x: x.lower(), answerKeys))
            return answerKeys

        def open_browser(self, question, answers):
            if ("-wiki" in sys.argv[1:]):
                for answer in answers:
                    a_url = "https://en.wikipedia.org/wiki/{}".format(answer.replace("&", ""))
                    webbrowser.open_new(a_url)
            if ("-google" in sys.argv[1:]):
                url = "https://www.google.com.tr/search?q={}".format(question.replace("&", ""))
                webbrowser.open_new(url)
        #performs the google search
        def google_search(self, search_term, api_key, cse_id, **kwargs):
            service = build("customsearch", "v1", developerKey=api_key)
            res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
            return res['items']

        #posts text to hqtrivia channel in slack
        def slack_message(self, text):
            sc.api_call(
                "chat.postMessage",
                channel="#hqtrivia",
                text=text
            )