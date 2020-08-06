from fastapi.testclient import TestClient
from server import app
import json
import random
from os.path import basename
from hashlib import sha256
import os
import warnings

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
    for i in range(4):
        with open(f'target/{testfilenamepattern}_{i}', 'wb') as fh:
          # Generate deterministic random file, 70k
          fh.write(testdata)

def teardown_module(module):
    pass
    # os.remove(testfile1)

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

def test_exists():
    response = client.get(f'/exists/{testfilenamepattern}_0')
    assert response.status_code == 200
    assert response.json() ==  {"message": "file found"}

def test_not_exists():
    response = client.get('/exists/bazinga')
    assert response.status_code == 404


