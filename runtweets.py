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
        
  url = "http://127.0.0.1:" + str(args.port) + "/raw_data"
  response = urllib.urlopen(url)
  dump = json.loads(response.read())
  new = copy.deepcopy(dump)
  old = {
    'pokemons': []
  }
  
  if os.path.isfile('data.json'):
    with open('data.json') as data_file:
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
        destination = location[0]
        if len(location) == 5:
          destination += ", " + location[1]
        time = datetime.datetime.fromtimestamp(e_new['disappear_time']/1000)
        ampm = "AM"
        hour = time.hour
        gmap = 'https://www.google.com/maps/dir/Current+Location/' \
                + str(e_new['latitude']) + ',' + str(e_new['longitude'])
        if hour > 12:
          hour -= 12
          ampm = "PM"
        elif hour == 12:
          ampm = "PM"
        elif hour == 0:
          hour = 12
        tweeting = "{} at {} until {}:{}:{} {}. #PokemonGo {}".format( \
          e_new['pokemon_name'], destination, \
          hour, str(time.minute).zfill(2), str(time.second).zfill(2), ampm, \
          shortener.short(gmap))
        tweet.statuses.update(status=tweeting)
        print tweeting
        # Google api timeout
        t.sleep(0.5)
    
  with open('data.json', 'w') as outfile:
    json.dump(dump, outfile)
    
if __name__ == "__main__":
  # Read list of rares, if not add all kanto pokemon id
  if os.path.isfile('rares.txt'):
    with open('rares.txt', 'r') as file:
      rares = [int(x) for x in file.read().split()]
  else:
    print("rares.txt not found, adding all pokemon instead.")
    rares = [x+1 for x in range(151)]

  while True:
    try:
      tweet()
      print("[{}] Tweeting complete. Restarting in 10 seconds.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
      t.sleep(10)
    except Exception as e:
      print("[{}] Crashed. Retrying in 10 seconds.".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
      t.sleep(10)
      tweet()