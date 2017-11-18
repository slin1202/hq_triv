from image_parser import ImageParser
from watchdog.observers import Observer
import os

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
