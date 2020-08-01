#!/usr/bin/env python
import click
import requests
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileCreatedEvent, FileDeletedEvent, FileModifiedEvent
from os.path import basename

from time import sleep

logging.basicConfig(level=logging.INFO)

class FileEventHandler(object):
    """ EventHandler class for watchdog. Gets event and fires of 
    client.
    """

    def __init__(self, baseurl):
        self.baseUrl = baseurl

    def send_file(self, file: str):
        url = self.baseUrl + 'upload/'
        print(f"Sending file: {file}")
        with open(file, 'rb') as fh:
            files = {'file': fh}
            r = requests.post(url, files=files)
            print(r.text)
        print("I think this went well.")

    def delete_file(self, file: str):
        url = self.baseUrl + 'delete/' + file
        r = requests.get(url)
        print(r.text)

    def dispatch(self, event: FileSystemEvent):
        if isinstance(event, FileCreatedEvent):
            logging.debug("New file created")
            self.send_file(event.src_path)
        elif isinstance(event,FileModifiedEvent):
            logging.debug("File modified")
            self.send_file(event.src_path)
        elif isinstance(event, FileDeletedEvent):
            logging.debug("File deleted")
            self.delete_file(basename(event.src_path))
        else:
            logging.debug(f"Other event: {event}")


@click.command()
@click.option('--folder', default='source',
              help='The folder to monitor.')
@click.option('--baseurl', default='http://localhost:8000/',
              help='Baseurl for the sync service')

def main(folder, baseurl):
    observer = Observer()
    observer.schedule(FileEventHandler(baseurl=baseurl), folder, recursive=False)
    observer.start()
    print(f"Monitoring folder {folder}")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    print("Exiting.")

if __name__ == "__main__":
    main()
