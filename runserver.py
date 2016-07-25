#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import time

from threading import Thread

from pogom import config
from pogom.app import Pogom
from pogom.utils import get_args
from pogom.search import search_loop, create_search_threads
from pogom.models import init_database, create_tables, Pokemon

from pogom.pgoapi.utilities import get_pos_by_name

log = logging.getLogger(__name__)

search_thread = Thread()

def start_locator_thread(args):
    search_thread = Thread(target=search_loop, args=(args,))
    search_thread.daemon = True
    search_thread.name = 'search_thread'
    search_thread.start()

if __name__ == '__main__':
    args = get_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [' + args.num + '] [%(module)9s] [%(levelname)5s]%(message)s')

    logging.getLogger("peewee").setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logging.WARNING)
    logging.getLogger("pogom.pgoapi.rpc_api").setLevel(logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    if args.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)

    db = init_database()
    create_tables(db)

    position = get_pos_by_name(args.location)
    if not any(position):
        log.error('Could not get a position by name, aborting.')
        sys.exit()

    log.info('Parsed location is: {:.4f}/{:.4f}/{:.4f} (lat/lng/alt)'.
             format(*position))

    config['ORIGINAL_LATITUDE'] = position[0]
    config['ORIGINAL_LONGITUDE'] = position[1]

    create_search_threads(args.num_threads)
    start_locator_thread(args)

    app = Pogom(__name__)

    config['ROOT_PATH'] = app.root_path
    config['GMAPS_KEY'] = args.google

    if args.no_server:
        while not search_thread.isAlive():
            time.sleep(1)
        search_thread.join()
    else:
        app.run(threaded=True, debug=args.debug, host=args.host, port=args.port)
