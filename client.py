#!/usr/bin/env python
import click
import requests
import logging
from watchdog.observers import Observer
import json

from filehandler import FileEventHandler

from time import sleep

logging.basicConfig(level=logging.INFO)

@click.command()
@click.option('--folder', default='source',
              help='The folder to monitor.')
@click.option('--baseurl', default='http://localhost:8000/',
              help='Baseurl for the sync service')
def main(folder, baseurl):
    observer = Observer()
    observer.schedule(FileEventHandler(baseurl=baseurl, chunk_size=8192),
                      folder, recursive=False)
    observer.start()
    print(f"Monitoring folder {folder}")
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    print("Exiting.")




if __name__ == "__main__":
    main()
