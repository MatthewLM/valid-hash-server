#!/usr/bin/python3
#
# Project: valid-hash-server
# File: main.py
#
# Copyright 2015 Matthew Mitchell
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from valid_hash_server.appdata import AppData
from valid_hash_server.sync import maybe_sync

import sys

HTTP_OK = "200 OK"
HTTP_METHOD_NOT_ALLOWED = "405 Method Not Allowed"
HTTP_UNSUPPORTED = "415 Unsupported media type"
HTTP_NOT_ACCEPTABLE = "406 Not Acceptable"
HTTP_NOT_FOUND = "404 Not Found"

GET_RESP = b"Requires POST data, as application/octet-stream. 32 bytes of block hash data (little-endian) per known block in reverse chronological order. Returns the first block hash that is valid plus all following block hashes, using 16 byes per hash. Also in little-endian. Upto 32 hashes are allowed in the POST request."

MIME_TYPE = "application/octet-stream"

TEXT_PLAIN_HEADERS = [('Content-Type', 'text/plain')]

def is_acceptable(header, expect):

    start = expect.split("/")[0]

    for mime in header.split(","):
        mime = mime.strip()
        if mime in ["*/*", start + "/*", expect]:
            return True

    return False

class Application():

    def __init__(self, directory=None):
        self.appdata = AppData(directory)

    def __call__(self, env, start_response):

        if env["wsgi.multiprocess"]:
            sys.exit("Cannot run valid-hash-file server with wsgi.multiprocess. Please use threads only")

        # Determine page

        page = env["PATH_INFO"]
        if page[-1] == "/":
            page = page[1:-1]
        else:
            page = page[1:]

        if page not in self.appdata.coins:
            start_response(HTTP_NOT_FOUND, TEXT_PLAIN_HEADERS)
            return [bytes(page + " not a valid coin on this server", "utf-8")]

        coin = self.appdata.coins[page]

        if env['REQUEST_METHOD'] != "POST":

            allow_headers = [("Allow", "POST, GET")]

            if env['REQUEST_METHOD'] == "OPTIONS":
                # Preflight requests need to be implemented for Ajax queries
                headers.append(('Access-Control-Allow-Headers', 'Content-Type, Accept, Accept-Encoding, Content-Length, Host, Origin, User-Agent, Referer'))
                start_response(HTTP_OK, allow_headers)
                return [b""]
            elif env['REQUEST_METHOD'] == "GET":
                start_response(HTTP_OK, TEXT_PLAIN_HEADERS)
                return [GET_RESP]
            else:
                start_response(HTTP_METHOD_NOT_ALLOWED, allow_headers)
                return [b""]

        # If content type is set, should be application/octet-stream
        if "CONTENT_TYPE" in env and env["CONTENT_TYPE"] != MIME_TYPE:
            start_response(HTTP_UNSUPPORTED, [])
            return [b""]

        # If accept header is set, should be application/octet-stream
        if 'HTTP_ACCEPT' in env and not is_acceptable(env['HTTP_ACCEPT'], MIME_TYPE):
            start_response(HTTP_NOT_ACCEPTABLE, [])
            return [b""]

        headers = [('Content-Type', MIME_TYPE)]

        # Get blockhash locator from POST data
        locator = env['wsgi.input'].read()

        # Ensured synced
        maybe_sync(coin, self.appdata)

        with self.appdata.io_lock.reader():

            # Loop through locator and find first shared block
            # Up to 32 hashes allowed

            start_height = 0

            for x in range(min(len(locator) // 32, 32)):
                try:
                    start_height = coin.hash_to_height[locator[x*32 : x*32 + 16]]
                    break
                except KeyError:
                    pass

            # Give upto 50,000 hashes as a repsonse
            # Return a copy of list to make sure it is not changed after look is released
            amount = min(len(coin.height_to_hash) - start_height, 50000)

            start_response(HTTP_OK, headers)
            return coin.height_to_hash[start_height : start_height + amount]

