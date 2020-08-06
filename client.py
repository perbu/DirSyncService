#!/usr/bin/env python

"""
  dirsync client
  This takes a folder as parameter and keeps it in sync on the server side.
  PoC.

"""


import logging
from time import sleep
import click
from watchdog.observers import Observer
from filehandler import FileEventHandler # all the logic is in here.

logging.basicConfig(level=logging.INFO)


@click.command()
@click.option('--folder', default='source',
              help='The folder to monitor.')
@click.option('--baseurl', default='http://localhost:8000/',
              help='Baseurl for the sync service')
def main(folder, baseurl):
    """ main is invoked through click """

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
