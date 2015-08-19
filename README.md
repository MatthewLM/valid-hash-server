valid-hash-server: Server for obtaining blockchain hashes
=========================================================

This python module provides the ability to provide blockchain hashes for
cryptocurrencies that utilise the getblockcount and getblockhash RPC
commands.

This module uses the python WSGI interface. When installed it allows 
clients to download blockhashes for configured coins. The server expects
POST requests with 0 to 32 binary block hashes under the MIME type
application/octet-stream. The hashes should be listed in reverse 
chronological order. When the server finds a block hash that it knows is
in the main chain it will respond with the last 16 bytes of the blockhash
(in reverse order) and of every other blockhash that comes after it in the 
blockchain.

This allows client applications to determine the correct blocks for the
main chain as according to the server.

This software is used to download block hashes for the Peercoin Android
Application, and can also be used for other applications that require
centralised block validation. This avoids requiring full PoS validation.

Installation on a Server
------------------------

This assumes that you have a Debian Jessie 8.1 server. Other debian/ubuntu
servers may or may not work with these instructions.

### Prepare your server

Ensure that your server is correctly prepared, kept secure and up-to-date.
You will need python3, apache2, and mod_wsgi installed:

```
sudo apt-get install python3 apache2 libapache2-mod-wsgi-py3
```

### Install the module

To install the module clone this repository or extract an archive to a
directory on your server. Move to this directory and enter the following
command:

```
sudo python3 setup.py install
```

### Configure coins

Decide upon a data directory for your server. By default it is set to
~/.valid_hash_server/

Under this directory create the configuration for your coins inside a
file named coin.conf. This file is a INI style configuration file. Use
the following format:

```
[coin_name]
user=rpcusername
pass=rpcpassword
host=rpchostname
port=rpcport
```

You can create multiple sections for multiple coins. You will of-course
need to run the coin daemons for the configured coins with the correct
rpc details.

### Initial Synchronisation

To synchronise with the blockchains of the configured coins run the 
command:

```
python3 -m valid_hash_server.sync
```

This may take some time for coins with an inefficient getblockhash RPC
command. This command also takes the argument "--dir" or "-d" followed
by the directory that you wish to use. You can also list specific coin
names to synchronise at the end of the command. Use the "--help"
argument for details.

### Virtual Host configuration

Move to the directory for the virtual hosts:

```
cd /etc/apache2/sites-available/
```

Now under this directory create a file with a name of your choice to
hold the virtual host configuration for the server. Inside this file
you will need the following, replacing the ALL_CAPITALS parts:

```
<VirtualHost *:80>
        ServerName SERVER_HOST_NAME
        Redirect permanent / https://SERVER_HOST_NAME
</VirtualHost>

<IfModule mod_ssl.c>

<VirtualHost *:443>

        ServerName SERVER_HOST_NAME
        ErrorLog PATH_TO_ERROR_LOG
        LogLevel info

        WSGIScriptAlias / PATH_TO_SCRIPT
        WSGIDaemonProcess valid_hash_server user=YOUR_USER
        WSGIProcessGroup valid_hash_server

        <Directory PATH_TO_SCRIPT_DIRECTORY>
            Require all granted
        </Directory>

        SSLEngine on
        SSLCertificateFile PATH_TO_SSL_CERT
        SSLCertificateKeyFile PATH_TO_SSL_PRIVATE_KEY

</VirtualHost>

</IfModule>
```

It is *strongly* recommended that you use HTTPS for your server.

### Create the python script

Now create the file given by PATH_TO_SCRIPT with the following 
contents:

```
#!/usr/bin/python3
from valid_hash_server.main import Application
application = Application()
```

You may give a data directory as an argument to the Application
construtor. The file must have permissions for the user defined in the
virtual host configuration.

### Reload apache

After reloading apache your server should be operational.

```
sudo service apache2 reload
```

