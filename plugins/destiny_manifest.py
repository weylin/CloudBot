#!/usr/bin/env python

# Manifest class
# Based on: http://destinydevs.github.io/BungieNetPlatform/docs/Manifest

import requests, zipfile, os
import json, sqlite3
import pickle
import glob

# Dictionary that tells where to get the hashes for each table
# FULL DICTIONARY

hash_dict = {
    'DestinyProgressionDefinition': 'hash',
    'DestinyInventoryItemDefinition': 'hash',
    'DestinyInventoryBucketDefinition': 'hash',
    'DestinyItemTierTypeDefinition': 'hash',
    'DestinyStatDefinition': 'hash',
    'DestinyStatGroupDefinition': 'hash',
    'DestinyVendorDefinition': 'hash',
    'DestinyFactionDefinition': 'hash',
    'DestinyProgressionLevelRequirementDefinition': 'hash',
    'DestinyRewardSourceDefinition': 'hash',
    'DestinyObjectiveDefinition': 'hash',
    'DestinySandboxPerkDefinition': 'hash',
    'DestinyLocationDefinition': 'hash',
    'DestinyDestinationDefinition': 'hash',
    'DestinyActivityGraphDefinition': 'hash',
    'DestinyActivityDefinition': 'hash',
    'DestinyActivityModifierDefinition': 'hash',
    'DestinyActivityModeDefinition': 'hash',
    'DestinyPlaceDefinition': 'hash',
    'DestinyActivityTypeDefinition': 'hash',
    'DestinySocketTypeDefinition': 'hash',
    'DestinySocketCategoryDefinition': 'hash',
    'DestinyTalentGridDefinition': 'hash',
    'DestinyDamageTypeDefinition': 'hash',
    'DestinyLoreDefinition': 'hash',
    'DestinyItemCategoryDefinition': 'hash',
    'DestinyRaceDefinition': 'hash',
    'DestinyGenderDefinition': 'hash',
    'DestinyClassDefinition': 'hash',
    'DestinyMilestoneDefinition': 'hash',
    'DestinyUnlockDefinition': 'hash',
    'DestinyHistoricalStatsDefinition': 'statId'
}

HEADERS = {}

class DestinyManifestException(Exception):
    pass


def __get_manifest():
    manifest_url = 'https://www.bungie.net/Platform/Destiny2/Manifest/'

    # Get the manifest location from the json
    manifest = requests.get(manifest_url, headers=HEADERS).json()

    try:
        mani_url = 'https://www.bungie.net' + manifest['Response']['mobileWorldContentPaths']['en']
    except KeyError:
        err_msg = "Error fetching the manifest URL. Status: '{}' Message: '{}'".format(manifest['ErrorStatus'], manifest['Message'])
        raise DestinyManifestException(err_msg)


    #Download the file, write it to MANZIP
    r = requests.get(mani_url)
    with open("DESTINYMANZIP", "wb") as zip:
        zip.write(r.content)
    print("Download Complete!")

    #Extract the file contents, and rename the extracted file
    # to 'Manifest.content'
    with zipfile.ZipFile('DESTINYMANZIP') as zip:
        name = zip.namelist()
        zip.extractall()
    os.rename(name[0], 'Manifest.content')
    print('Unzipped!')

def __build_dict(hash_dict):
    #connect to the manifest
    con = sqlite3.connect('Manifest.content')
    print('Connected')
    #create a cursor object
    cur = con.cursor()

    all_data = {}
    #for every table name in the dictionary
    for table_name in hash_dict.keys():
        #get a list of all the jsons from the table
        cur.execute('SELECT json from ' + table_name)
        print('Generating '+table_name+' dictionary....')

        #this returns a list of tuples: the first item in each tuple is our json
        items = cur.fetchall()

        #create a list of jsons
        item_jsons = [json.loads(item[0]) for item in items]

        #create a dictionary with the hashes as keys
        #and the jsons as values
        item_dict = {}
        item_hash = hash_dict[table_name]
        for item in item_jsons:
            item_dict[item[item_hash]] = item

        #add that dictionary to our all_data using the name of the table
        #as a key.
        all_data[table_name] = item_dict
    print('Dictionary Generated!')
    return all_data

def __get_manifest_version():
    manifest_url = 'https://www.bungie.net/Platform/Destiny2/Manifest/'
    r = requests.get(manifest_url)
    manifest = r.json()
    try:
        manifest_version = manifest['Response']['version']
    except KeyError:
        err_msg = "Error fetching the manifest version. Status: '{}' Message: '{}'".format(manifest['ErrorStatus'], manifest['Message'])
        raise DestinyManifestException(err_msg)
    else:
        return manifest_version

def __create_manifest():
    __get_manifest()
    version = __get_manifest_version()
    all_data = __build_dict(hash_dict)
    filename = 'destiny_manifest_{}.pickle'.format(version)
    with open(filename, 'wb') as data:
        pickle.dump(all_data, data)
    print("{} created!\nDONE!".format(filename))

def __cleanup_files(filename):
    try:
        os.remove('DESTINYMANZIP')
    except OSError:
        print('DESTINYMANZIP not found. Skipping...')

    try:
        os.remove('Manifest.content')
    except OSError:
        print('Manifest.content not found. Skipping...')

    try:
        os.remove(filename)
    except OSError:
        print('{} not found. Nothing to delete!'.format(filename))

def is_manifest_current(key):
    global HEADERS
    HEADERS = {'X-API-Key': key}

    # Get manifest version
    remote_version = __get_manifest_version()

    # Get any existing manifest pickles
    pickles = glob.glob('destiny_manifest_*.pickle')

    # Get manifest version, but only if one pickle
    if 0 < len(pickles) <= 1:
        local_filename = pickles[0]
    elif len(pickles) > 1:
        os.remove(sorted(pickles)[0])
        local_filename = sorted(pickles)[-1]
    else:
        return False

    # Get local manifest version
    local_version = local_filename.split('_')[-1]

    return local_version >= remote_version

def gen_manifest_pickle(key, force=False):
    global HEADERS
    HEADERS = {'X-API-Key': key}

    # Get any existing manifest pickles
    pickles = glob.glob('destiny_manifest_*.pickle')

    # If more than one pickle, only keep latest one
    if len(pickles) == 1:
        local_filename = pickles[0]
    elif len(pickles) > 1:
        os.remove(sorted(pickles)[0])
        local_filename = sorted(pickles)[-1]
    else:
        pass

    # Check if pickle exists, if not, create one
    if len(pickles) == 0:
        print('Generating new Destiny manifest pickle...')
        __create_manifest()
        return 'New Destiny manifest pickle created!'
    elif force or not is_manifest_current():
        print('Destiny manifest pickle out of date, generating new one...')
        print('Deleting old pickle: {}...'.format(local_filename))
        __cleanup_files(local_filename)

        print('Generating new Destiny manifest pickle...')
        __create_manifest()
        return 'Destiny manifest pickle updated'
    else:
        return 'Pickle exists and is up to date!'

if __name__ == '__main__':
    gen_manifest_pickle()
