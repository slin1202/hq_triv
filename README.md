# hq trivia

## Requirements:

  - Python v3.6
  - OpenCV v3.0
  - tesseract-ocr
  - libimobiledevice
  

Run the following command to install all the modules

```pip3 install -r requirements.txt```

Afterwards you will need to get setup with OpenCV, follow the instructions here:

### OpenCV 3.0 with Python 3.6
https://www.pyimagesearch.com/2015/06/15/install-opencv-3-0-and-python-2-7-on-osx/
This might take a while

Next you will need tesseract, https://github.com/tesseract-ocr/tesseract/wiki

Finally, you will need libimobiledevice. I just used the binary distribution found here: https://github.com/benvium/libimobiledevice-macosx


## Possible TODOS

1. Generalize answer search (lower case and separate words) so that it isn't looking for an exact match in the results
2. Parse out common words such as "the, and, or" in answers (this might help, not sure)
3. Add multiple search apis such as *cough* Bing
4. Make api calls for the question + answer as well (3 more api calls, need to more sure they don't slow the app)
5. General performance boosts (need to make it run fast, usually the host talks for 1-2 seconds before the question shows up so we only have ~8 seconds to get the answer and determine the likelihood that the program is correct)
6. Add classification of the question (could just simply be based on filtering on words "Who, what, where, why, how")
7. Add an adaptive weighting system based on various factors such as (search engine used, type of question, etc) historical data to determine the score
