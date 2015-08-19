#!/usr/bin/python3
#
# Project: valid-hash-server
# File: sync.py
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

import os.path
import argparse
import time

from valid_hash_server.appdata import AppData
from valid_hash_server.coin import JSONRPCException

def to_mini_hash(blk_hash):
    return bytes.fromhex(blk_hash)[32:15:-1]

def maybe_sync(coin, appdata):

    # Sync no more than once a second
    
    with appdata.io_lock.writer():
        if (coin.last_sync + 1 < time.time()):
            sync_no_lock(coin, appdata)
            coin.last_sync = time.time()

def sync(coin, appdata):

    with appdata.io_lock.writer():
        sync_no_lock(coin, appdata)

def sync_no_lock(coin, appdata):

    try:

        if len(coin.height_to_hash) == 0:
            height_cursor = 0
        else:

            height_cursor = len(coin.height_to_hash) - 1

            # Check that the hash is on the main chain, and go backwards until we find one on the main chain

            actuals = []

            while (True):

                actual = coin.call("getblockhash", height_cursor)
                actual = to_mini_hash(actual)
                has = coin.height_to_hash[height_cursor]

                if (actual != has):
                    coin.remove_block()
                    actuals.append(actual)
                    height_cursor -= 1
                else:
                    break

            # Add the actual blocks

            height_cursor += 1

            while (len(actuals) > 0):
                coin.add_block_hash(actuals.pop(), height_cursor)
                height_cursor += 1

        # Now add all new hashes

        blk_count = coin.call("getblockcount")
        toget = blk_count - height_cursor + 1

        while toget > 0:
            togetnow = min(toget, 100)
            calls = []
            for x in range(togetnow):
                calls.append(["getblockhash", height_cursor + x])
            result = coin.batch(calls)
            for blk_hash in result:
                blk_hash = to_mini_hash(blk_hash)
                coin.add_block_hash(blk_hash, height_cursor)
                height_cursor += 1
            toget -= togetnow
            print("%s block %s/%s" % (coin.sect, height_cursor - 1, blk_count))

    except JSONRPCException as e:
        print(e)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dir", default=None, help="The data directory to be used")
    parser.add_argument("coin", nargs="*", help="A list of coins to synchronise. If ommitted, all configured coins will be synchronised.")

    args = parser.parse_args()
    appdata = AppData(args.dir)

    # Sync all coins if none specified
    coins = args.coin if len(args.coin) > 0 else appdata.coins

    for coin in coins:
        if coin not in appdata.coins:
            exit(coin + " not in coin.conf")

    for coin in coins:
        sync(appdata.coins[coin], appdata)

