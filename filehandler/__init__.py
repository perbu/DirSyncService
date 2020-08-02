from watchdog.events import FileSystemEvent, FileCreatedEvent, FileDeletedEvent, FileModifiedEvent
from os.path import basename
from os import stat
import logging
import requests
from hashlib import sha256


class FileEventHandler(object):
    """ EventHandler class for watchdog.
    Contains method for interacting with the server.
    Gets event and fires of client.
    """

    def __init__(self, baseurl, chunk_size):
        self.baseUrl = baseurl
        self.chunkSize = chunk_size

    # Entrypoint
    def dispatch(self, event: FileSystemEvent):
        if isinstance(event, FileCreatedEvent) or isinstance(event, FileModifiedEvent):
            file = event.src_path
            if self.remote_exists(basename(file)):
                local_cs = self.get_local_checksum(file)
                remote_cs = self.get_remote_checksum(file)
                changed_blocks = self.compare(local_cs, remote_cs)
                self.incremental_send(file, changed_blocks)
                self.truncate(file, stat(file).st_size)
            else:
                self.send_file(file)
        elif isinstance(event, FileDeletedEvent):
            logging.info("File deleted")
            self.delete_file(basename(event.src_path))
        else:
            logging.debug(f"Other event: {event}")

    def compare(self, local_cs, remote_cs):
        # import pudb; pu.db
        logging.debug(f'Local checksums: {local_cs}')
        logging.debug(f'Remote checksums: {remote_cs}')
        if local_cs['checksum'] == remote_cs['checksum']:
            # zero changed blocks, they are identical
            return []
        else:
            remote_blocks = len(remote_cs['chunks'])
            logging.debug(f'Remote blocks for compare {remote_blocks}')
            changed_blocks = []
            for idx, chunk in enumerate(local_cs['chunks']):
                logging.debug(f"Comparing block {idx}")
                if idx >= remote_blocks:
                    logging.debug("No block on remote side to compare with.")
                    changed_blocks.append(idx)
                elif chunk != remote_cs['chunks'][idx]:
                    changed_blocks.append(idx)
            return changed_blocks

    def remote_exists(self, filename):
        url = self.baseUrl + 'checksum/' + basename(filename)
        r = requests.get(url)
        if r.ok:
            return True
        else:
            return False

    def truncate(self, filename, lenght):
        print(f"Truncating {filename} to {lenght}")
        url = self.baseUrl + 'truncate/' + \
            basename(filename) + '/' + str(lenght)
        requests.get(url)

    def get_local_checksum(self, filename):
        cs_whole = sha256()
        chunk_checksums = []
        with open(filename, 'rb') as fh:
            for chunk in read_in_chunks(fh, chunk_size=self.chunkSize):
                cs_whole.update(chunk)
                cs_chunk = sha256()
                cs_chunk.update(chunk)
                chunk_checksums.append(cs_chunk.hexdigest())
        return {"checksum": cs_whole.hexdigest(),
                "chunks": chunk_checksums}

    def get_remote_checksum(self, filename):
        """ fetch the remote checksum so we can compare """
        url = self.baseUrl + 'checksum/' + basename(filename)
        r = requests.get(url)
        return r.json()

    def send_block(self, filename: str, block: int, content: bytes):
        filename = basename(filename)
        url = self.baseUrl + 'upload_chunk/' + filename + '/' + str(block)
        r = requests.post(url, data=content)
        logging.info(f'Sending block {block} on file {filename} with len {len(content)}: {r.text}')

    def incremental_send(self, filename: str, blocks: list):
        logging.info(f"Doing incremental change on {filename}")
        logging.info(f"Changed blocks: {blocks}")
        with open(filename, 'rb') as fh:
            for block in blocks:
                fh.seek(block * self.chunkSize)
                content = fh.read(self.chunkSize)
                self.send_block(filename, block, content)
        return True

    def send_file(self, file: str):
        url = self.baseUrl + 'upload/'
        with open(file, 'rb') as fh:
            files = {'file': fh}
            r = requests.post(url, files=files)
            logging.info(f"Sending file {file}: {r.text}")

    def delete_file(self, file: str):
        url = self.baseUrl + 'delete/' + file
        r = requests.get(url)
        logging.info(f"Deleteing file {file}: {r.text}")



def read_in_chunks(file_object, chunk_size=8192):
    """Generator to read a file piece by piece.
    Default chunk size: 8k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data
