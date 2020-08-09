from fastapi.testclient import TestClient
from server import app
import json
import random
from os.path import basename
from hashlib import sha256
import os
import warnings
import io
import logging

testfilenamepattern = 'testfile'
client = TestClient(app)
# aiofiles generates a lot of warnings:
warnings.filterwarnings("ignore", category=DeprecationWarning)

def generate_testdata(size=70000, seed=31337):
    random.seed(seed)
    lst = [random.randint(30, 250) for i in range(size)]
    return bytes(lst)

def setup_module(module):
    print(f"Setting up tests in {module}")
    testdata = generate_testdata()
    for i in range(3):
        with open(f'target/{testfilenamepattern}_{i}', 'wb') as fh:
            # Generate deterministic random file, 70k
            fh.write(testdata)


def teardown_module(module):
    # the third file is deleted during the tests.
    for i in range(2):
        os.remove(f'target/{testfilenamepattern}_{i}')


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Nothing to see here"}


def test_download():
    response = client.get(f'/download/{testfilenamepattern}_0')
    assert response.status_code == 200
    assert response.content == generate_testdata()


def test_checksum():
    response = client.get(f'/checksum/{testfilenamepattern}_0')
    assert response.status_code == 200

    testdata = generate_testdata()
    # checksum for the whole "file"
    cs_whole = sha256()
    cs_whole.update(testdata)
    payload = response.json()

    assert payload['checksum'] == cs_whole.hexdigest()

    view = memoryview(testdata)
    cs_chunks = []
    # calculate checksums for each 8k block - take care to slice out the last one.
    for chunk in range((70000 // 8192)+1):
        cs = sha256()
        cs.update(view[chunk * 8192:min(70000, chunk*8192+8192)])
        cs_chunks.append(cs.hexdigest())
    assert payload['chunks'] == cs_chunks

def test_checksum_404():
    response = client.get('/checksum/not_here')
    assert response.status_code == 404

def test_exists():
    response = client.get(f'/exists/{testfilenamepattern}_0')
    assert response.status_code == 200
    assert response.json() == {"message": "file found"}


def test_not_exists():
    response = client.get('/exists/bazinga')
    assert response.status_code == 404


def test_incremental_upd():
    testdata = generate_testdata()
    nullchunk = bytes([0 for i in range(8192)])
    response = client.post(f'/upload_chunk/{testfilenamepattern}_0/0',
                           data=nullchunk)
    assert response.status_code == 200

    view = memoryview(testdata)
    cs_whole = sha256()
    cs_whole.update(nullchunk)
    cs_whole.update(view[8192:70000])
    response = client.get(f'/checksum/{testfilenamepattern}_0')
    assert response.status_code == 200

    assert response.json()['checksum'] == cs_whole.hexdigest()

def test_truncate():
    target_size = 50000
    response = client.post(f'/truncate/', json={'filename': f'{testfilenamepattern}_1', 'lenght':50000})
    assert response.status_code == 200

    actual_size = os.stat(f'target/{testfilenamepattern}_1').st_size
    assert actual_size == target_size
    logging.basicConfig(level=logging.WARN)


def test_upload_and_download():
    testfilename = f'{testfilenamepattern}_3'
    testdata = generate_testdata(size=40000)
    testdatafh = io.BytesIO(testdata)
    testdatafh.name = testfilename
    files = {'file': testdatafh}
    upload_resp = client.post(f'/upload/', files=files)
    assert upload_resp.status_code == 201
    download_resp = client.get(f'/download/{testfilename}')
    assert testdata == download_resp.content

def test_delete():
    filename = f'{testfilenamepattern}_2'
    print(f"Deleteing file {filename}")
    response = client.post(f'/delete/', json={ 'filename': filename })
    assert response.status_code == 200
    assert os.path.isfile('target/{testfilenamepattern}_2') == False

def test_settings():
    response = client.get('/info')
    assert response.status_code == 200
    j = response.json()
    assert j["chunksize"] == 8192
    assert j["folder"] == "target/"