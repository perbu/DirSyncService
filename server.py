#!/usr/bin/env python
import logging
from hashlib import sha256
import os
from os.path import isfile, isdir
import uvicorn
import aiofiles
from starlette.responses import FileResponse
from fastapi import FastAPI, File, UploadFile, Response, Request, status, HTTPException


chunk_size = 8192
target_folder = "target/"

app = FastAPI()                             # this is what uvicorn looks for...
logging.basicConfig(level=logging.INFO)


@app.get("/")
async def root():
    return {"message": "Nothing to see here"}


@app.get("/checksum/{filename}")
async def checksum(filename: str, response: Response):
    """ Get checksum of the target """
    target_file = target_folder + filename
    if not isfile(target_file):
        raise HTTPException(status_code=404, detail="Item not found")
    cs_whole_file = sha256()
    checksum_chunks = []
    async with aiofiles.open(target_file, 'rb') as file:
        # AIOFile is stateless but provides this helper class:
        chunk = await file.read(chunk_size)
        while chunk:
            cs_whole_file.update(chunk)  # checksum for the whole file.
            cs_chunk = sha256()
            cs_chunk.update(chunk)  # cs for the chunk
            checksum_chunks.append(cs_chunk.hexdigest())
            chunk = await file.read(chunk_size)

    return {"checksum": cs_whole_file.hexdigest(),
            "chunks": checksum_chunks}


@app.get("/exists/{filename}")
async def exists(filename: str):
    """ Check if file exists. If it doesn't - return a 404 """
    target_file = target_folder + filename
    if not isfile(target_file):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "file found"}


@app.get("/truncate/{filename}/{lenght}")
async def truncate(filename: str, lenght: int):
    """ Truncate, typically used after incremental transfer to remove
    any bytes if the file has shrunk"""
    target_file = target_folder + filename
    if not isfile(target_file):
        raise HTTPException(status_code=404, detail="Item not found")
    async with aiofiles.open(target_file, 'a') as target:
        await target.truncate(lenght)
    return {"truncate": lenght}


@app.post("/upload/", status_code=200)
async def create_upload_file(response: Response, file: UploadFile = File(...)):
    await file.seek(0)  # Not sure we need to seek, doesn't hurt.
    async with aiofiles.open(target_folder + file.filename, 'wb') as target:
        chunk = await file.read(chunk_size)
        while chunk:
            await target.write(chunk)
            chunk = await file.read(chunk_size)
    # close the startlette file:
    await file.close()
    await target.close()
    response.status_code = status.HTTP_201_CREATED
    return {"filename": target_folder + file.filename}


@app.post("/upload_chunk/{filename}/{cid}", status_code=200)
async def chunks(filename: str, cid: int, request: Request):
    chunk_content = await request.body()
    logging.info(
        f'Overwriting chunk (len:{len(chunk_content)}) file {filename} at offset {cid * chunk_size}')
    async with aiofiles.open(target_folder + filename, 'r+b') as target:
        await target.seek(cid * chunk_size)
        await target.write(chunk_content)
    return {"written bytes": len(chunk_content)}


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
    if not isdir(target_folder):
        logging.error('Target folder "target_folder"')
    uvicorn.run("server:app", host="127.0.0.1",
                port=8000, log_level="info", reload=True)
