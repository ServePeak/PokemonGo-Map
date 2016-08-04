#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twitter import *
from pyshorteners import Shortener
from pygeocoder import Geocoder
import argparse
import time as t
import datetime
import copy
import os
import simplejson as json
import urllib
import ConfigParser

# pokemon to find
rares = []
idToPokemon = {}

def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-P', '--port', type=int, help='Set web server listening port', required=True)
  return parser.parse_args()

def load_credentials():
  Config = ConfigParser.ConfigParser()
  Config.read(os.path.join(os.path.dirname(__file__), './config/config.ini'))
  creds = []
  creds.append(Config.get('API_Keys', 'google'))
  creds.append(Config.get('API_Keys', 'twitter_access_token'))
  creds.append(Config.get('API_Keys', 'twitter_access_secret'))
  creds.append(Config.get('API_Keys', 'twitter_consumer_key'))
  creds.append(Config.get('API_Keys', 'twitter_consumer_secret'))
  return creds

def tweet():
  args = get_args()
  creds = load_credentials()
  
  shortener = Shortener('Google', api_key=creds[0])
  tweet = Twitter(auth=OAuth(creds[1], creds[2], creds[3], creds[4]))
        
  url = "http://127.0.0.1:" + str(args.port) + "/rare"
  response = urllib.urlopen(url)
  dump = json.loads(response.read())
  new = copy.deepcopy(dump)
  old = {
    'pokemons': []
  }
  
  if os.path.isfile(os.path.join(os.path.dirname(__file__), './data.json')):
    with open(os.path.join(os.path.dirname(__file__), './data.json')) as data_file:
      old = json.load(data_file)

  # Deletes encounter id for next step
  for e_new in new['pokemons']:
    for e_old in old['pokemons']:
      if e_new['encounter_id'] == e_old['encounter_id']:
        del e_new['encounter_id']
        break

  # Existing encounter ids are rare pokemon
  # This entire step is to parse the data for a tweet
  for e_new in new['pokemons']:
    if e_new['pokemon_id'] in rares:
      if 'encounter_id' in e_new:
        location = str(Geocoder.reverse_geocode(e_new['latitude'], e_new['longitude'])[0]).split(',')
        destination = location[0] + ", " + location[1].split()[0]
        time = datetime.datetime.fromtimestamp(e_new['disappear_time']/1000)
        hour = time.hour + 6
        gmap = 'https://www.google.fr/maps/place/' \
                + str(e_new['latitude']) + ',' + str(e_new['longitude']) + '/'
        if hour >= 24:
          hour -= 24
        tweeting = "{} à {} jusqu'à {}:{}:{}. #PokemonGo {}".format( \
          idToPokemon[str(e_new['pokemon_id'])].encode('utf-8'), destination, \
          hour, str(time.minute).zfill(2), str(time.second).zfill(2), \
          shortener.short(gmap))
        tweet.statuses.update(status=tweeting)
        print tweeting
        # Google api timeout
        t.sleep(0.5)
    
  with open(os.path.join(os.path.dirname(__file__), './data.json'), 'w') as outfile:
    json.dump(dump, outfile)
    
if __name__ == "__main__":
  # Read list of rares, if not add all kanto pokemon id
  if os.path.isfile(os.path.join(os.path.dirname(__file__), './rares.txt')):
    with open(os.path.join(os.path.dirname(__file__), './rares.txt'), 'r') as file:
      rares = [int(x) for x in file.read().split()]
  else:
    print("rares.txt not found, adding all pokemon instead.")
    rares = [x+1 for x in range(151)]

  with open(os.path.join(os.path.dirname(__file__), './static/locales/pokemon.fr.json')) as data_file:
    idToPokemon = json.load(data_file)

  while True:
    try:
      tweet()
      print("[{}] Tweeting complete. Restarting in 10 seconds.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
      t.sleep(10)
    except Exception as e:
      print("[{}] Crashed. Retrying in 10 seconds.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
      t.sleep(10)
      tweet()
