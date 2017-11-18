from PIL import Image
import pytesseract
import cv2
import os
import numpy as np
import sys
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import webbrowser
from googleapiclient.discovery import build
from slackclient import SlackClient

#google keys
google_api_key = os.environ["HQ_GOOGLE_API_KEY"]
google_cse_id = os.environ["HQ_GOOGLE_CSE_ID"]

#slack api key
slack_token = os.environ["HQ_SLACK_TOKEN"]

sc = SlackClient(slack_token)


#performs the google search
def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']

#posts text to hqtrivia channel in slack
def slack_message(text):
    sc.api_call(
        "chat.postMessage",
        channel="#hqtrivia",
        text=text
    )

class ImageParser(PatternMatchingEventHandler):
        def process(self, event):
            #if the new file has the word screenshot in it perform the text analysis
            if (event.src_path.find("screenshot") != -1):

                #crop the image to remove the top and bottom of the screen to only parse out the question and answer
                #people with iphone x's might need to modify this
                image = cv2.imread(event.src_path)
                height = np.size(image, 0)
                width = np.size(image, 1)
                crop = image[int(height*0.15):int(height - height*0.2), 0:width]

                #performs a binary threshold(helps when the answers are grayed out when you're out of the game
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                gray = cv2.threshold(gray, 200, 255,
                        cv2.THRESH_BINARY)[1]

                if("-save" not in sys.argv[1:]):
                    os.remove(event.src_path)
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
            print(question)

            #UNCOMMENT TO OPEN UP TABS
            # for answer in answers:
            #     a_url = "https://en.wikipedia.org/wiki/{}".format(answer.replace("&", ""))
            #     webbrowser.open_new(a_url)
            # url = "https://www.google.com.tr/search?q={}".format(question.replace("&", ""))
            # webbrowser.open_new(url)

            results = google_search(question, google_api_key, google_cse_id, num=9)

            #just counts the number of times the answers appears in the results
            answer_results = [{'count': 0, 'alpha_key': 'A'}, {'count': 0, 'alpha_key': 'B'}, {'count': 0, 'alpha_key': 'C'}]
            for index, val in enumerate(answers):
                answer_results[index]['count'] = str(results).count(answers[index])
            result_sum = sum(answer_result['count'] for answer_result in answer_results)
            for index, answer_result in enumerate(answer_results):
                if result_sum == 0:
                    result_sum = 1
                percentage = answer_result['count']/result_sum * 100
                text = answer_result['alpha_key'] + ":'" + answers[index].lstrip() + "'(" + str(int(percentage)) + "%)"
                answer_result['text'] = text
                answer_result['percentage'] = percentage
            for ar in answer_results:
                print(ar['text'])
                if("-slack" in sys.argv[1:]):
                    slack_message(ar['text'])

        def on_created(self, event):
            self.process(event)

if __name__ == '__main__':
    observer = Observer()
    observer.schedule(ImageParser(), path='.')
    observer.start()

    while 1:
        input("\nPress anything to continue\n")
        os.system("idevicescreenshot")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
