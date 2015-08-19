#!/usr/bin/python3
#
# Project: valid-hash-server
# File: appdata.py
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

import configparser
import os.path
import os
import fcntl
import sys

from valid_hash_server.rwlock import RWLock
from valid_hash_server.coin import Coin

class AppData ():

    def __init__(self, directory):

        if directory is None:
            directory = os.path.expanduser("~/.valid_hash_server")

        # Create directory if need be
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Prevent multiple program instances within same directory

        self.lockfilePath = os.path.join(directory, "lock")
        self.lockfile = open(self.lockfilePath, "w")

        try:
            fcntl.lockf(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            sys.exit("Another instance of valid-hash-server is running.")

        self.directory = directory

        conf = configparser.ConfigParser()
        conf.read_file(open(os.path.join(directory, "coin.conf")))

        self.coins = {}

        for sect in conf.sections():
            self.coins[sect] = Coin(
                sect,
                os.path.join(directory, sect + "_hashfile.dat"),
                conf[sect]["user"],
                conf[sect]["pass"],
                conf[sect]["host"],
                conf[sect]["port"],
            )
        
        self.io_lock = RWLock()

    def __del__(self):

        fcntl.lockf(self.lockfile, fcntl.LOCK_UN)
        self.lockfile.close()

        if os.path.isfile(self.lockfilePath):
            os.unlink(self.lockfilePath) 

