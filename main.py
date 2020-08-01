#!/usr/bin/env python

import uvicorn
from fastapi import FastAPI, File, UploadFile, Response, status, HTTPException
from starlette.responses import FileResponse
import logging
import asyncio
from aiofile import AIOFile, Reader, Writer
import hashlib
import aiofiles
import os
from os.path import isfile

chunk_size = 8192
target_folder = "target/"

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

@app.get("/")
async def root():
    return {"message": "Nothing to see here"}

@app.get("/checksum/{filename}")
async def checksum(filename: str, response: Response):
    target_file = target_folder + filename
    if not isfile(target_file):
        raise HTTPException(status_code=404, detail="Item not found")
    checksum = hashlib.sha256()
    async with AIOFile(target_file, 'rb') as file:
        # AIOFile is stateless but provides this helper class:
        reader = Reader(file,chunk_size=chunk_size)
        async for chunk in reader:
            checksum.update(chunk)
    return {"checksum:" : checksum.hexdigest() }

@app.post("/upload/", status_code=200)
async def create_upload_file(response: Response, file: UploadFile = File(...) ):
    await file.seek(0) # Not sure we need to seek, doesn't hurt.
    async with AIOFile(target_folder + file.filename, 'wb') as target:
        writer = Writer(target)
        chunk = await file.read(chunk_size)
        while chunk:
            await writer(chunk)
            chunk = await file.read(chunk_size)
    # close the startlette file:
    await file.close()
    response.status_code = status.HTTP_201_CREATED
    return {"filename": target_folder + file.filename}

@app.get("/download/{filename}")
async def download(filename: str):
    target_file = target_folder + filename
    if not isfile(target_file):
        raise HTTPException(status_code=404, detail="Item not found")
    response = FileResponse(path=target_folder + filename, filename=filename)
    return response

@app.get("/delete/{filename}")
async def delete(filename: str):
    target_file = target_folder + filename
    if not isfile(target_file):
        raise HTTPException(status_code=404, detail="Item not found")
    os.remove(target_file)
    return {"file removed": target_file}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info")