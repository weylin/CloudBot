import json
import urllib.request as ur
import urllib.parse as par
from datetime import datetime, timedelta
import time
from cloudbot import hook

#Grab the PS4 data. Maybe expand to XB1 and PC later?
html = ur.urlopen('http://content.ps4.warframe.com/dynamic/worldState.php').read() 

#Convert to JSON Variable
data = json.loads(html.decode('utf-8'))

#color st00f
boldred = '\x02\x033'
boldblue = '\x02\x0312'
end = '\x02\x03'

#Set Current time for later use maybe? 
#Goal: No need to advertise arrival after the fact, maybe check and return countdown for departure?
#Goal: Countdown for arrival as well? Instead of just the when? When + days/hours?
#current_epoch = str(time.time())

#Creating a dict for current Planet:Relay value. 
#We need this to properly associate what what is in the JSON to what players know in game.
hubs = {

    #'PlanetHub'    :   'Relay'     #Console annotation
    #                                      PC     PS4  XB1    MR   Lotus
    'MercuryHUB'    :   'Larunda',  #      ✓      -    -      0    ✓
    'VenusHUB'      :   'Vesper',   #      -      -    ✓      0    ✓
    'EarthHUB'      :   'Strata',   #      -      ✓    -      0    ✓
    'SaturnHUB'     :   'Kronia',   #      ✓      ✓    -      4       
    'EuropaHUB'     :   'Leonov',   #      -      -    ✓      5       
    'ErisHUB'       :   'Kuiper',   #      -      ✓    -      8       
    'PlutoHUB'      :   'Orcus'     #      ✓      -    ✓      8       
}

#@hook.command('baro')
#def baro(bot, text):
#   #Grab the JSON data specific to Void Traders.
#    trader = data['VoidTraders']
#    #Loop through all the items in this section.
#    for item in trader:
#        #Grabbing a few items... Name and destination specifically.
#        baro = item['Character']
#        node = item['Node']
#        #Go through our hubs dict. If Destination ("node") matches we'll set relay to the name of the corresponding Planet Relay.#
#
#        #Grab the arrival and departure times which are stored in an epoch str (or is it an int?). 
#        arrival_epoch = item['Activation']['sec']
#        depart_epoch = item['Expiry']['sec']
#        #return what we know. 
#        #Goal, use .format and get some colors working?
#        return baro + ' Arrives at the ' + relay + ' Relay at ' \
#        + datetime.utcfromtimestamp(arrival_epoch).strftime('%X UTC on %x')

def getitem():
    trader = data['VoidTraders']
    for item in trader:
        baro = item['Character']
        node = item['Node']
        manifest = item['Manifest']
        for sale in manifest:
            itemType = sale['ItemType']
            primePrice = sale['PrimePrice']
            regularPrice = sale['RegularPrice']
          
            print(baro + "Has arrived at the " + node + "with: " + itemType + str(primePrice) + str(regularPrice))

@hook.command('baro')
def time():
    #Output
    output = []
    #Get the current datetime as a timestamp (epoch) and put in a a var. 
    current_epoch = int(datetime.now().timestamp())
    #Get the Void Trader specific data from our JSON variable.
    trader = data['VoidTraders']
    #Iterate over the data and grab our arrival and departure time which is \
    # an epoch str in the JSON.
    for item in trader:
        baro = item['Character']
        arrival_epoch = int(item['Activation']['sec'])
        node = item['Node']
        for item, key in hubs.items():
            if node == item:
                relay = key


        #depart_epoch = item['Expiry']['sec']
        #If the current time is after the arrival time gather data.
        if current_epoch > arrival_epoch:
            getitem()
            output = 'Baro is here! {}'.format('\x02\x033' + str(arrival_epoch) + '\x02\x03')
            #need call get item and print item stuffs.
            return output
        else:
            #Get the difference between now and the next arrival time, \
            #set to time_til variable
            time_til = arrival_epoch - current_epoch
            #Doing a timedelta, time_til is seconds
            #Long math that should probably go in it's own class.
            d = timedelta(seconds=time_til)
            minutes = d.seconds / 60
            remmins = minutes % 60
            hours = d.seconds / 24
            remhours = hours % 24
            output = '{}{}{} Returns to the {}{}{} Relay in: {} days, {} hours, and {}'\
            ' minutes'.format(boldred, baro, end, boldblue, relay, end, d.days, int(remhours), int(remmins))
            return output