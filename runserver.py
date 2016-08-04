#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import time
from threading import Thread, Event
from queue import Queue

from pogom import config
from pogom.app import Pogom
from pogom.utils import get_args

from pogom.search import search_overseer_thread
from pogom.models import init_database, create_tables, drop_tables, Pokemon

from pogom.pgoapi.utilities import get_pos_by_name

# Moved here so logger is configured at load time
args = get_args()
logging.basicConfig(level=logging.INFO, format='%(asctime)s[' + args.num + '][%(threadName)1s][%(module)9s] [%(levelname)5s] %(message)s')
log = logging.getLogger()

if __name__ == '__main__':

    # These are very noisey, let's shush them up a bit
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('pogom.pgoapi.pgoapi').setLevel(logging.WARNING)
    logging.getLogger('pogom.pgoapi.rpc_api').setLevel(logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # Turn these back up if debugging
    if args.debug:
        logging.getLogger('requests').setLevel(logging.DEBUG)
        logging.getLogger('pgoapi').setLevel(logging.DEBUG)
        logging.getLogger('rpc_api').setLevel(logging.DEBUG)


    position = get_pos_by_name(args.location)
    if not any(position):
        log.error('Could not get a position by name, aborting')
        sys.exit()

    log.info('Parsed location is: {:.4f}/{:.4f}/{:.4f} (lat/lng/alt)'.
             format(*position))

    config['ORIGINAL_LATITUDE'] = position[0]
    config['ORIGINAL_LONGITUDE'] = position[1]

    app = Pogom(__name__)
    db = init_database(app)
    create_tables(db)

    app.set_current_location(position);

    # Control the search status (running or not) across threads
    pause_bit = Event()
    pause_bit.clear()

    # Setup the location tracking queue and push the first location on
    new_location_queue = Queue()
    new_location_queue.put(position)

    log.debug('Starting a real search thread')
    search_thread = Thread(target=search_overseer_thread, args=(args, new_location_queue, pause_bit))

    search_thread.daemon = True
    search_thread.name = 'search_thread'
    search_thread.start()

    app.set_search_control(pause_bit)
    app.set_location_queue(new_location_queue)

    config['ROOT_PATH'] = app.root_path
    config['GMAPS_KEY'] = args.google
    config['REQ_SLEEP'] = args.scan_delay

    if args.no_server:
        # This loop allows for ctrl-c interupts to work since flask won't be holding the program open
        while search_thread.is_alive():
            time.sleep(60)
    else:
        app.run(threaded=True, use_reloader=False, debug=args.debug, host=args.host, port=args.port)
