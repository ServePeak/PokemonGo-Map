#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import getpass
import argparse
import re
import uuid
import os
import simplejson as json
from datetime import datetime, timedelta
import ConfigParser
import platform
import logging
import shutil

from . import config
from exceptions import APIKeyException

DEFAULT_THREADS = 1

log=logging.getLogger(__name__)

def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string

def verify_config_file_exists(filename):
    fullpath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(fullpath) is False:
        log.info("Could not find " + filename + ", copying default")
        shutil.copy2(fullpath + '.example', fullpath)

def parse_config(args):
    verify_config_file_exists('../config/config.ini')
    Config = ConfigParser.ConfigParser()
    Config.read(os.path.join(os.path.dirname(__file__), '../config/config.ini'))
    args.step_limit = int(Config.get('Search', 'Steps'))
    args.scan_delay = int(Config.get('Search', 'Scan_delay'))
    args.host = Config.get('Web', 'Host') 
    args.port = int(Config.get('Web', 'Port'))
    args.db = Config.get('MySQL', 'Database')
    args.user = Config.get('MySQL', 'Username')
    args.pword = Config.get('MySQL', 'Password')
    args.myhost = Config.get('MySQL', 'Host')
    args.google = Config.get('API_Keys', 'google')
    return args

def get_args():
    # fuck PEP8
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--auth-service', type=str.lower, help='Auth Service', default='ptc')
    parser.add_argument('-u', '--username', help='Username', required=True)
    parser.add_argument('-p', '--password', help='Password', required=False)
    parser.add_argument('-l', '--location', type=parse_unicode, help='Location, can be an address or coordinates', required=False)
    parser.add_argument('-st', '--step-limit', help='Steps', required=False, type=int)
    parser.add_argument('-sd', '--scan-delay', help='Time delay before beginning new scan', required=False, type=int, default=1)
    parser.add_argument('-dc','--display-in-console',help='Display Found Pokemon in Console',action='store_true',default=False)
    parser.add_argument('-H', '--host', help='Set web server listening host', default='127.0.0.1')
    parser.add_argument('-P', '--port', type=int, help='Set web server listening port', default=5000)
    parser.add_argument('-ns', '--no-server', help='No-Server Mode. Starts the searcher but not the Webserver.', action='store_true', default=False, dest='no_server')
    parser.add_argument('-t', '--threads', help='Number of search threads', required=False, type=int, default=DEFAULT_THREADS, dest='num_threads')
    parser.add_argument('-d', '--debug', help='Debug Mode', action='store_true')
    parser.add_argument('-N', '--num', help='Number to differentiate runs', required=True)
    parser.set_defaults(DEBUG=False)
    args = parser.parse_args()
    
    real_step = args.step_limit
    args = parse_config(args) 
    if real_step:
      args.step_limit = real_step
    
    if (args.username is None or args.location is None or args.step_limit is None):
        parser.print_usage()
        print sys.argv[0] + ': error: arguments -u/--username, -l/--location, -st/--step-limit, -N/--num are required'
        sys.exit(1);

    if args.password is None:
        args.password = getpass.getpass()

    return args

def get_pokemon_name(pokemon_id):
    if not hasattr(get_pokemon_name, 'names'):
        file_path = os.path.join(
            config['ROOT_PATH'],
            config['LOCALES_DIR'],
            'pokemon.{}.json'.format(config['LOCALE']))

        with open(file_path, 'r') as f:
            get_pokemon_name.names = json.loads(f.read())

    return get_pokemon_name.names[str(pokemon_id)]
