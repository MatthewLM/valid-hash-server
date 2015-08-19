# Copyright 2014, 2015 Token Labs LLC
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

from http.client import HTTPConnection
import json
import base64
import decimal
import struct
import os.path

USER_AGENT = "CoinRpc"

class JSONRPCException(Exception):
    pass

class Coin():

    def __init__(self, sect, hashfile_path, username, password, host, port):

        self.last_sync = 0

        self.sect = sect
        self.hashfile = open(hashfile_path, "r+b" if os.path.exists(hashfile_path) else "w+b")

        num_hash_bytes = self.hashfile.read(4)

        if num_hash_bytes == b"":
            self.hashfile.write(struct.pack(">I", 0))
            numhashes = 0
        else:
            numhashes, = struct.unpack(">I", num_hash_bytes)

        # Read in block data

        self.hash_to_height = {}
        self.height_to_hash = []
        for x in range(numhashes):
            blk_hash = self.hashfile_block_hash(x)
            self.hash_to_height[blk_hash] = x
            self.height_to_hash.append(blk_hash)

        # Rpc

        self.host = host
        self.port = port
        self.next_id = 0
        self.auth = "Basic " + base64.b64encode((username + ":" + password).encode()).decode()

    def add_block_hash(self, block_hash, height):

        self.hashfile.seek(4 + 16*height)
        self.hashfile.write(block_hash)
        self.hashfile.seek(0)
        self.hashfile.write(struct.pack(">I", height + 1))

        self.hash_to_height[block_hash] = height

        if len(self.height_to_hash) == height:
            self.height_to_hash.append(block_hash)
        else:
            self.height_to_hash[height] = block_hash

    def remove_block(self):
        blk_hash = self.height_to_hash[-1]
        del self.hash_to_height[blk_hash]
        del self.height_to_hash[-1]

    def hashfile_block_hash(self, height):
        self.hashfile.seek(4 + 16*height)
        return self.hashfile.read(16)

    def call(self, *args):
       return self.batch([list(args)])[0]

    def batch(self, calls):

        batch_data = []
        for call in calls:
            m = call.pop(0)
            batch_data.append({
                "jsonrpc" : "2.0",
                "method"  : m,
                "params"  : call,
                "id"      : self.next_id
            })
            self.next_id += 1

        postdata = json.dumps(batch_data)

        conn = HTTPConnection(self.host, self.port)

        try:

            conn.request("POST", "", postdata, {
                "Host" : self.host,
                "User-Agent" : USER_AGENT,
                "Authorization" : self.auth,
                "Content-Type" : "application/json"
            })

            response = conn.getresponse()

            if response is None:
                raise JSONRPCException({
                    'code': -342, 
                    'message': 'missing HTTP response from server'
                })

            if response.status is not 200:
                raise JSONRPCException({
                    'code': -344,
                    'message': str(response.status) + " " + response.reason
                })

            try:
                responses = json.loads(response.read().decode())
            except ValueError as e:
                raise JSONRPCException(str(e))

        finally:
            conn.close()

        results = []

        for response in responses:
            if response['error'] is not None:
                raise JSONRPCException(response['error'])
            elif 'result' not in response:
                raise JSONRPCException({
                    'code': -343, 
                    'message': 'missing JSON-RPC result'
                })
            else:
                results.append(response['result'])

        return results


