#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
from peewee import Model, SqliteDatabase, InsertQuery, IntegerField, CharField, DoubleField, BooleanField, DateTimeField, OperationalError, InternalError, create_model_tables
from playhouse.flask_utils import FlaskDB
from playhouse.pool import PooledMySQLDatabase
from playhouse.shortcuts import RetryOperationalError
from datetime import datetime
from base64 import b64encode

from . import config
from .utils import get_pokemon_name, get_args
from .transform import transform_from_wgs_to_gcj
from .customLog import printPokemon

log = logging.getLogger(__name__)

flaskDb = FlaskDB()

class MyRetryDB(RetryOperationalError, PooledMySQLDatabase):
    pass

def init_database(app): 
    args = get_args()

    db = MyRetryDB(
        args.db, 
        user=args.user, 
        passwd=args.pword, 
        host=args.myhost,
        max_connections=args.dbmax,
        stale_timeout=300)
    log.info('Connecting to MySQL database on {}.'.format(args.myhost))
    app.config['DATABASE'] = db
    flaskDb.init_app(app)
    return db

class BaseModel(flaskDb.Model):

    @classmethod
    def get_all(cls):
        return [m for m in cls.select().dicts()]


class Pokemon(BaseModel):
    # We are base64 encoding the ids delivered by the api
    # because they are too big for sqlite to handle
    encounter_id = CharField(primary_key=True)
    spawnpoint_id = CharField(index=True)
    pokemon_id = IntegerField(index=True)
    latitude = DoubleField()
    longitude = DoubleField()
    disappear_time = DateTimeField(index=True)
    
    class Meta:
        indexes = ((('latitude', 'longitude'), False),)

    @classmethod
    def get_active(cls, swLat, swLng, neLat, neLng):
        if swLat == None or swLng == None or neLat == None or neLng == None:
            query = (Pokemon
                 .select()
                 .where(Pokemon.disappear_time > datetime.utcnow())
                 .dicts())
        else:
            query = (Pokemon
                 .select()
                 .where((Pokemon.disappear_time > datetime.utcnow()) &
                    (Pokemon.latitude >= swLat) &
                    (Pokemon.longitude >= swLng) &
                    (Pokemon.latitude <= neLat) &
                    (Pokemon.longitude <= neLng))
                 .dicts())

        pokemons = []
        for p in query:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
            pokemons.append(p)

        return pokemons

    @classmethod
    def get_active_by_id(cls, ids, swLat, swLng, neLat, neLng):
        if swLat == None or swLng == None or neLat == None or neLng == None:
            query = (Pokemon
                     .select()
                     .where((Pokemon.pokemon_id << ids) &
                            (Pokemon.disappear_time > datetime.utcnow()))
                     .dicts())
        else:
            query = (Pokemon
                     .select()
                     .where((Pokemon.pokemon_id << ids) &
                            (Pokemon.disappear_time > datetime.utcnow()) &
                            (Pokemon.latitude >= swLat) &
                            (Pokemon.longitude >= swLng) &
                            (Pokemon.latitude <= neLat) &
                            (Pokemon.longitude <= neLng))
                     .dicts())

        pokemons = []
        for p in query:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
            pokemons.append(p)

        return pokemons

class ScannedLocation(BaseModel):
    scanned_id = CharField(primary_key=True)
    latitude = DoubleField()
    longitude = DoubleField()
    last_modified = DateTimeField(index=True)
    
    class Meta:
        indexes = ((('latitude', 'longitude'), False),)

    @classmethod
    def get_recent(cls, swLat, swLng, neLat, neLng):
        query = (ScannedLocation
                 .select()
                 .where((ScannedLocation.last_modified >= (datetime.utcnow() - timedelta(minutes=15))) &
                    (ScannedLocation.latitude >= swLat) &
                    (ScannedLocation.longitude >= swLng) &
                    (ScannedLocation.latitude <= neLat) &
                    (ScannedLocation.longitude <= neLng))
                 .dicts())

        scans = []
        for s in query:
            scans.append(s)

        return scans

def parse_map(map_dict, iteration_num, step, step_location):
    pokemons = {}
    scanned = {}

    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    for cell in cells:
        for p in cell.get('wild_pokemons', []):
            d_t = datetime.utcfromtimestamp(
                (p['last_modified_timestamp_ms'] +
                 p['time_till_hidden_ms']) / 1000.0)
            printPokemon(p['pokemon_data']['pokemon_id'],p['latitude'],p['longitude'],d_t)
            pokemons[p['encounter_id']] = {
                'encounter_id': b64encode(str(p['encounter_id'])),
                'spawnpoint_id': p['spawnpoint_id'],
                'pokemon_id': p['pokemon_data']['pokemon_id'],
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'disappear_time': d_t
            }

    pokemons_upserted = 0


    if pokemons:
        pokemons_upserted = len(pokemons)
        log.debug("Upserting {} pokemon".format(len(pokemons)))
        bulk_upsert(Pokemon, pokemons)

    log.info("Upserted {} pokemon".format(pokemons_upserted))

    scanned[0] = {
        'scanned_id': str(step_location[0])+','+str(step_location[1]),
        'latitude': step_location[0],
        'longitude': step_location[1],
        'last_modified': datetime.utcnow(),
    }

    bulk_upsert(ScannedLocation, scanned)

def bulk_upsert(cls, data):
    num_rows = len(data.values())
    i = 0
    step = 120
    
    flaskDb.connect_db()

    while i < num_rows:
        log.debug("Inserting items {} to {}".format(i, min(i+step, num_rows)))
        try:
            InsertQuery(cls, rows=data.values()[i:min(i+step, num_rows)]).upsert().execute()
        except (OperationalError, InternalError) as e:
            log.warning("%s... Retrying", e)
            continue

        i+=step
        
    flaskDb.close_db(None)

def create_tables(db):
    db.connect()
    db.create_tables([Pokemon, ScannedLocation], safe=True)
    db.close()
