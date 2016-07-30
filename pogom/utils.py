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
import requests

from . import config
from exceptions import APIKeyException

log = logging.getLogger(__name__)


def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string


def verify_config_file_exists(filename):
    fullpath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(fullpath):
        log.info("Could not find " + filename + ", copying default")
        shutil.copy2(fullpath + '.example', fullpath)

def parse_config(args):
    verify_config_file_exists('../config/config.ini')
    Config = ConfigParser.ConfigParser()
    Config.read(os.path.join(os.path.dirname(__file__), '../config/config.ini'))
    args.step_limit = int(Config.get('Search', 'Steps'))
    args.thread_delay = int(Config.get('Search', 'Thread_delay'))
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
    parser.add_argument('-a', '--auth-service', type=str.lower,
                        help='Auth Service', default='ptc')
    parser.add_argument('-u', '--username', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    parser.add_argument('-l', '--location', type=parse_unicode,
                        help='Location, can be an address or coordinates')
    parser.add_argument('-st', '--step-limit', help='Steps', type=int)
    parser.add_argument('-sd', '--scan-delay',
                        help='Time delay between requests in scan threads',
                        type=float, default=0.8)
    parser.add_argument('-td', '--thread-delay',
                        help='Time delay between each scan thread loop',
                        type=float, default=20)
    parser.add_argument('-ld', '--login-delay',
                        help='Time delay between each login attempt',
                        type=float, default=5)
    parser.add_argument('-dc', '--display-in-console',
                        help='Display Found Pokemon in Console',
                        action='store_true', default=False)
    parser.add_argument('-H', '--host', help='Set web server listening host',
                        default='127.0.0.1')
    parser.add_argument('-P', '--port', type=int,
                        help='Set web server listening port', default=5000)
    parser.add_argument('-L', '--locale',
                        help='Locale for Pokemon names (default: {},\
                        check {} for more)'.
                        format(config['LOCALE'], config['LOCALES_DIR']), default='en')
    parser.add_argument('-d', '--debug', help='Debug Mode', action='store_true')
    parser.add_argument('-ns', '--no-server',
                        help='No-Server Mode. Starts the searcher but not the Webserver.',
                        action='store_true', default=False)
    parser.add_argument('-t', '--num-threads', help='Number of search threads', type=int, default=1)
    parser.add_argument('-dm', '--dbmax', help='Max connections for the database', type=int, default=10)

    parser.add_argument('-N', '--num', help='Number to differentiate runs', required=True)
    parser.add_argument('-wh', '--webhook', help='Define URL(s) to POST webhook information to',
                        nargs='*', default=False, dest='webhooks')
    parser.set_defaults(DEBUG=False)

    args = parser.parse_args()

    real_step = args.step_limit
    real_delay = args.thread_delay
    
    args = parse_config(args) 
    
    if real_delay:
      args.thread_delay = real_delay
      
    if real_step:
      args.step_limit = real_step

    if (args.username is None or args.location is None or args.step_limit is None):
        parser.print_usage()
        print sys.argv[0] + ': error: arguments -u/--username, -l/--location, -st/--step-limit, -N/--num are required'
        sys.exit(1);

    if args.password is None:
        args.password = getpass.getpass()

    return args

def i8ln(word):
    log.debug("Translating: %s", word)
    if config['LOCALE'] == "en": return word
    if not hasattr(i8ln, 'dictionary'):
        file_path = os.path.join(
            config['ROOT_PATH'],
            config['LOCALES_DIR'],
            '{}.json'.format(config['LOCALE']))
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                i8ln.dictionary = json.loads(f.read())
        else:
            log.warning("Skipping translations - Unable to find locale file: %s", file_path)
            return word
    if word in i8ln.dictionary:
        log.debug("Translation = %s", i8ln.dictionary[word])
        return i8ln.dictionary[word]
    else:
        log.debug("Unable to find translation!")
        return word

def get_pokemon_data(pokemon_id):
    if not hasattr(get_pokemon_data, 'pokemon'):
        file_path = os.path.join(
            config['ROOT_PATH'],
            config['LOCALES_DIR'],
            'pokemon.json')

        with open(file_path, 'r') as f:
            get_pokemon_data.pokemon = json.loads(f.read())
    return get_pokemon_data.pokemon[str(pokemon_id)]

def get_pokemon_name(pokemon_id):
    return i8ln(get_pokemon_data(pokemon_id)['name'])

def get_pokemon_rarity(pokemon_id):
    return i8ln(get_pokemon_data(pokemon_id)['rarity'])

def get_pokemon_types(pokemon_id):
    pokemon_types = get_pokemon_data(pokemon_id)['types']
    return map(lambda x: {"type": i8ln(x['type']), "color": x['color']}, pokemon_types)

def send_to_webhook(message_type, message):
    args = get_args()

    data = {
        'type': message_type,
        'message': message
    }

    if args.webhooks:
        webhooks = args.webhooks

        for w in webhooks:
            try:
                requests.post(w, json=data, timeout=(None, 1))
            except requests.exceptions.ReadTimeout:
                log.debug('Could not receive response from webhook')
            except requests.exceptions.RequestException as e:
                log.debug(e)
