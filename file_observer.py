from watchdog.events import PatternMatchingEventHandler
from image_parser import ImageParser


class FileObserver(PatternMatchingEventHandler):
    def process(self, event):
        # if the new file has the word screenshot in it perform the text analysis
        if (event.src_path.find("screenshot") != -1):
            ImageParser().process(file_path = event.src_path)
    def on_created(self, event):
        self.process(event)