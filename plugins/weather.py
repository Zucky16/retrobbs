from base64 import decode
import python_weather
import asyncio
import requests
import string
import time
#from sympy import content
import json
#from datetime import date
from geopy.geocoders import Nominatim

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

import numpy as NP

from common.connection import Connection
from common.c64cvt import GetIndexedImg, PaletteHither, c64imconvert
import common.filetools as FT
import common.turbo56k as TT
import common.petscii as P

wgfx24: list #Weather gfx 24px 
wgfx8:  list  #Weather gfx 8px
wtypes =    {110:2,113:2,                                       #Clear
            116:7,                                              #Partly Cloudy
            119:1,                                              #Cloudy
            122:23,                                             #Overcast
            143:6,                                              #Mist
            176:13,263:13,353:13,                               #Light showers
            179:14,362:14,374:14,311:14,323:14,326:14,368:14,   #Light snow/sleet
            182:4,185:4,281:4,314:4,317:4,350:4,377:4,365:4,    #Moderate/heavy snow/sleet
            200:15,386:15,392:15,                               #Thundery showers
            227:17,230:17,320:17,                               #Blizzard
            248:5,260:5,                                        #Fog
            266:13,293:13,296:13,                               #Light rain
            299:3,302:3,356:3,                                  #Moderate rain
            305:11,308:11,359:11,                               #Heavy rain
            335:24,371:24,395:0,338:24,                         #Heavy snow
            389:0                                               #Thunder
}
wwind =     {'N':0,'NNE':7,'NE':7,'ENE':7,'E':2,'ESE':6,'SE':6,'SSE':6,'S':1,'SSW':5,'SW':5,'WSW':5,'W':3,'WNW':8,'NW':8,'NNW':8}


#############################
#Plugin setup
def setup():
    global wgfx8
    global wgfx24
    global font_text
    global font_temp
    global font_title
    gfx = NP.array(Image.open('plugins/weather_icons.png'))
    wgfx24 = [gfx[x:x+24,y:y+24] for x in range(0,48,24) for y in range(0,312,24)]
    wgfx8 = [gfx[x:x+8,y:y+8] for x in range(56,72,8) for y in range(0,40,8)]
    # for i in wgfx8:
    #     Image.fromarray(i).show()
    font_title = ImageFont.truetype("plugins/karen2blackint.ttf", 16)   #<
    font_temp = ImageFont.truetype("plugins/karen2blackint.ttf", 24)    #<
    font_text = ImageFont.truetype("plugins/BetterPixels.ttf",16)       #<


    fname = "WEATHER" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

##########################################
#Plugin callable function
def plugFunction(conn:Connection):
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    #First get location from the connection IP
    response = requests.get('https://ipinfo.io/'+conn.addr[0])   #('https://geolocation-db.com/jsonp/200.59.72.128')
    result = response.content.decode()
    # Convert this data into a dictionary
    result  = json.loads(result)
    pointd = result.get('loc','46.23,6.08')  #str(result['latitude'])+','+str(result['longitude'])
    locqry = result.get('city','Meyrin')
    done = False
    loop = asyncio.new_event_loop()
    geoLoc = Nominatim(user_agent="RetroBBS")
    while conn.connected and not done:
        conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
        img = loop.run_until_complete(getweather(conn,locqry,geoLoc))
        if img != None:
            FT.SendBitmap(conn,img,multi=False,preproc=False,lines=23,display=False)
            conn.Sendall(TT.split_Screen(23,False,0,6))
        else:
            conn.Sendall(chr(P.CLEAR)+chr(P.WHITE)+'location not found!')
            time.sleep(2)
        conn.Sendall(TT.enable_CRSR())
        conn.Sendall(chr(P.CLEAR)+chr(P.YELLOW)+'[n]EW LOCATION OR _ TO EXIT\r')
        if conn.ReceiveKey(b'N_') == b'_':
            done = True
        else:
            conn.Sendall('lOCATION:')
            locqry = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'),30))
            tloc = geoLoc.geocode(locqry,language=conn.bbs.lang)
            if tloc == None:
                #Default to Meyrin
                locqry = 'Meyrin'
 
    loop.close()
    conn.Sendall(chr(0)*2+TT.split_Screen(0,False,0,0))
    return


async def getweather(conn:Connection,locquery,geoLoc:Nominatim):

    # declare the client. format defaults to the metric system (celcius, km/h, etc.)
    units = conn.bbs.PlugOptions.get('wxunits',python_weather.METRIC)
    client = python_weather.Client(format=units)
    img = GetIndexedImg(0) #Image.new('1', (320,200), color = 'black')
    draw = ImageDraw.Draw(img)
    # fetch a weather forecast from a city
    try:
        weather = await client.get(locquery) #("Trelew")
        if weather.location == None:    #Invalid location
            await client.close()
            return None
    except:
        await client.close()
        return None
    draw.rectangle([0,0,319,15],15)
    j = 3
    for i in range(0,7):
        draw.line(((2+(int(j*i)),0),(-13+(int(j*i)),15)),fill=11)
        #j += 0.1
    # Get full location from returned coordinates
    #geoLoc = Nominatim(user_agent="RetroBBS")
    floc = geoLoc.reverse(str(weather.location[0])+','+str(weather.location[1]),language=conn.bbs.lang)
    address = floc.raw.get('address',{})
    #City
    city = address.get('village',address.get('town',address.get('city',address.get('municipality','Unknown'))))
    #Region
    region = address.get('state',address.get('region',address.get('county','')))
    #Country
    country = address.get('country',address.get('country_code',address.get('continent','')))
    locdisplay = city+('-'+region if region != '' else '')+('-'+country if country != '' else '')
    l,t,r,b = draw.textbbox((160,2),locdisplay,font=font_title,anchor='mt')
    draw.rectangle([l-1,t-1,r+1,b+1],15)
    draw.text((160,2),locdisplay.replace('|','-'),11,font=font_title,anchor='mt')
    draw.line(((0,16),(319,16)),fill=11)
    for i in range(0,320,2):
        draw.point((i,17),fill=11)
        draw.point((i+1,18),fill=11)
        draw.point((i,54),fill=6)
        draw.point((i+1,53),fill=6)

    #Current temperature
    ctemp = weather.current.temperature
    if units == 'F':
        if ctemp < 32:
            tco = 4
        elif ctemp < 41:
            tco = 14
        elif ctemp < 59:
            tco = 3
        elif ctemp < 77:
            tco = 7
        elif ctemp < 86:
            tco = 8
        else:
            tco = 2
    else:
        if ctemp < 0:
            tco = 4
        elif ctemp < 5:
            tco = 14
        elif ctemp < 15:
            tco = 3
        elif ctemp < 25:
            tco = 7
        elif ctemp < 30:
            tco = 8
        else:
            tco = 2
    draw.text((40, 24),str(ctemp)+'°'+units,tco,font=font_temp)
    #Current weather type
    tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(weather.current.type.value,8)]))
    img.paste(tmp,(8,24))
    #Current wind conditions
    tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[16]))
    img.paste(tmp,(104,24))
    draw.text((136,28),str(weather.current.wind_speed)+('km/h' if units == 'C' else 'mph'),1,font=font_title)
    tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx8[wwind[weather.current.wind_direction]]))
    img.paste(tmp,(184,32))
    #Pressure
    tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[10]))
    img.paste(tmp,(224,24))
    draw.text((256,28),str(weather.current.pressure)+('hPa' if units == 'C' else 'Hg'),1,font=font_title)
    draw.line(((0,55),(319,55)),fill=6)

    # get the weather forecast for a few days
    draw.text((54,58),'Morning',1,font=font_text,anchor='mt')
    draw.text((126,58),'Noon',1,font=font_text,anchor='mt')
    draw.text((198,58),'Evening',1,font=font_text,anchor='mt')
    draw.text((268,58),'Night',1,font=font_text,anchor='mt')
    ix = 0

    for forecast in weather.forecasts:
        draw.text((0,76+(ix*32)),forecast.date.strftime('%a'),1,font=font_text)
        ih = 0
        for hourly in forecast.hourly:
            if ih == 3: # Morning
                #print(hourly.type.value,hourly.description)
                tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(hourly.type.value,8)]))
                img.paste(tmp,(32,72+(ix*32)))
                draw.text((56,76+(ix*32)),str(hourly.temperature)+'°',1,font=font_text)
            elif ih == 4: #Noon
                #print(hourly.type.value,hourly.description)
                tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(hourly.type.value,8)]))
                img.paste(tmp,(104,72+(ix*32)))
                draw.text((128,76+(ix*32)),str(hourly.temperature)+'°',1,font=font_text)
            elif ih == 6: #Evening
                #print(hourly.type.value,hourly.description)
                tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(hourly.type.value,8)]))
                img.paste(tmp,(176,72+(ix*32)))
                draw.text((200,76+(ix*32)),str(hourly.temperature)+'°',1,font=font_text)
            elif ih == 7: #Night
                #print(hourly.type.value,hourly.description)
                tmp = PaletteHither.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(hourly.type.value,8)]))
                img.paste(tmp,(248,72+(ix*32)))
                draw.text((272,76+(ix*32)),str(hourly.temperature)+'°',1,font=font_text)
            ih += 1
        ix += 1

    # close the wrapper once done
    await client.close()
    return(img)

