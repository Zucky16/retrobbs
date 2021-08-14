#Based on apod.py by Rajat Goyal
#Retrieves an APOD and converts it to c64 gfx format

import sys
import requests
import urllib.request
import ctypes
import random
from datetime import datetime,timedelta
from PIL import Image
from io import BytesIO

from common.c64cvt import c64imconvert
import common.petscii as P
import common.turbo56k as TT
from common.style import default_style, RenderMenuTitle
import common.filetools as FT
from common.helpers import formatX, More
from common.bbsdebug import _LOG,bcolors


url = 'https://api.nasa.gov/planetary/apod'
key = 'DGOkUrjIeLMTJhL4ZzAVZmKgkjLNixHJAiYpfust'    #'TRUeFmW0K72G8JRKOYfhZymkQUFM9bGxF05QrbNo'

#############################
#Plugin setup
def setup():
    fname = "APOD"
    parpairs= []
    return(fname,parpairs)
#############################

start_date = datetime.today().replace(day=16, month=6, year=1995).toordinal()
end_date = datetime.today().toordinal()

##########################################
#Plugin callable function
def plugFunction(conn):



    apod_lang = {'en':['cONNECTING WITH nasa',"\r"+chr(P.LT_GREEN)+"pRESS "+chr(P.PALETTE[default_style.PbColor])	\
                    +"["+chr(P.PALETTE[default_style.PtColor])+"return"+chr(P.PALETTE[default_style.PbColor])+"]"	\
                    +chr(P.LT_GREEN)+" TO DISPLAY IMAGE\rpRESS "+chr(P.YELLOW)+"["+chr(P.PALETTE[default_style.PtColor])	\
                    +"return"+chr(P.PALETTE[default_style.PbColor])+"]"+chr(P.LT_GREEN)+" AGAIN FOR A NEW\rRANDOM IMAGE\roR "	\
                    +chr(P.PALETTE[default_style.PbColor])+"["+chr(P.PALETTE[default_style.PtColor])+"_"	\
                    +chr(P.PALETTE[default_style.PbColor])+"]"+chr(P.LT_GREEN)+" TO GO BACK"],
                'es':['cONNECTANDO CON LA nasa',"\r"+chr(P.LT_GREEN)+"pRESIONE "+chr(P.PALETTE[default_style.PbColor])	\
                    +"["+chr(P.PALETTE[default_style.PtColor])+"return"+chr(P.PALETTE[default_style.PbColor])+"]"	\
                    +chr(P.LT_GREEN)+" PARA MOSTRAR IMAGEN\rpRESIONE "+chr(P.YELLOW)+"["+chr(P.PALETTE[default_style.PtColor])	\
                    +"return"+chr(P.PALETTE[default_style.PbColor])+"]"+chr(P.LT_GREEN)	\
                    +" DE NUEVO\rPARA OTRA IMAGE AL AZAR\ro "+chr(P.PALETTE[default_style.PbColor])+"["	\
                    +chr(P.PALETTE[default_style.PtColor])+"_"+chr(P.PALETTE[default_style.PbColor])+"]"+chr(P.LT_GREEN)	\
                    +" PARA VOLVER"]}

    #conn.Sendall("apod")
    #time.sleep(1)
    loop = True
    rdate = datetime.today()
    while loop == True:
        # # Text mode
        conn.Sendall(TT.to_Text(0,0,0))
        RenderMenuTitle(conn,'apod')
        conn.Sendall(apod_lang.get(conn.bbs.lang,'en')[0]+chr(P.YELLOW)+"..."+chr(P.COMM_B)+chr(P.CRSR_LEFT))
        i = 0
        idata = None
        _LOG("Receiving APOD info",id=conn.id)
        while idata == None and i<5:
            idata = apod_info(rdate,conn.bbs.PlugOptions.get('nasakey','DEMO_KEY')) #<<<< Change this to custom ini
            rdate = datetime.fromordinal(random.randint(start_date, end_date))
            if idata == None:
                _LOG(bcolors.OKBLUE+"Retrying..."+bcolors.ENDC,id=conn.id)
            i += 1
            conn.Sendall(".")
        conn.Sendall('\a'+chr(P.DELETE)*(23+i))
        if idata != None:
            date = idata["date"]
            _LOG("Showing APOD info for "+date,id=conn.id)
            imurl = idata["url"]
            title = idata["title"]
            desc = idata["explanation"]
            if "copyright" in idata:
                autor = idata["copyright"]
            else:
                autor = ''

            texto = formatX(title) #textwrap.wrap(''.join(c.lower() if c.isupper() else c.upper() for c in title),40)
            #Prints date
            texto += formatX("\n"+chr(P.LT_BLUE)+P.toPETSCII(date)+chr(P.WHITE)+"\n\n",convert=False)
            if autor != '':
                autor = chr(P.ORANGE)+"bY:"+P.toPETSCII(autor)+chr(P.PALETTE[default_style.TxtColor])+'\r'
                at = formatX(autor,convert=False) #textwrap.wrap(''.join(c.lower() if c.isupper() else c.upper() for c in autor),40)
            else:
                at = ['\r']
            texto += at+formatX(desc)

            if More(conn,texto,25) == 0:
                conn.Sendall(chr(P.DELETE)*8)
            else:
                conn.Sendall(chr(P.DELETE)*13)
            conn.Sendall(apod_lang.get(conn.bbs.lang,'en')[1])
            tecla = conn.ReceiveKey(b'\r_')
            if conn.connected == False:
                return()
            if tecla == b'_' or tecla == b'':
                loop = False
            if loop == True:
                conn.Sendall("\rcONVERTING IMAGE"+chr(P.YELLOW)+chr(P.COMM_B)+chr(P.CRSR_LEFT))
                _LOG("Downloading and generating image",id=conn.id)
                try:
                    img = apod_img(imurl) #img, bm, scr, cram, bg
                    FT.SendBitmap(conn, img)
                except:
                    _LOG(bcolors.WARNING+"Error receiving APOD image"+bcolors.ENDC,id=conn.id)
                    conn.Sendall("\rerror, UNABLE TO RECEIVE IMAGE")

                tecla = conn.ReceiveKey(b'\r_')
                conn.Sendall(TT.enable_CRSR())
                if conn.connected == False:
                    _LOG(bcolors.WARNING+"ShowAPOD - Disconnect"+bcolors.ENDC,id=conn.id)
                    return()
                if tecla == b'_' or tecla == b'':
                    loop = False
            #else:
            #	rdate = datetime.datetime.fromordinal(random.randint(apod.start_date, apod.end_date))
        else:
            conn.Sendall("\rerror, UNABLE TO CONNECT WITH nasa")
            _LOG(bcolors.WARNING+"Error while reaching NASA"+bcolors.ENDC,id=conn.id)
            loop = False
##########################################


def apod_info(idate, key='DEMO_KEY', retry = False):

    global url
    #global key

    date = idate.strftime("%Y-%m-%d")
    resp = None
    while resp == None:
        try :
            param = {'api_key': key, 'date': date}
            resp = requests.get(url, params=param).json()
            #apod_url = resp["hdurl"]
            if "media_type" in resp:
                m_type = resp["media_type"]
            else:
                m_type = ''
            if m_type != 'image' and retry == True:
                print(datetime.now(),'APOD - Not an image, retrying...', file=sys.stderr)
                resp = None
                date = datetime.fromordinal(random.randint(start_date, end_date)).strftime("%Y-%m-%d")
        except :
            if retry == True:
                print(datetime.now(),'APOD - Error, retrying...', file=sys.stderr)
            else:
                m_type = ''
                resp = -1
    if m_type != 'image':
        resp = None

    return(resp)

#apod_link = f'https://apod.nasa.gov/apod/ap{date.replace("-", "")[2:]}.html'

def apod_img(url):

    cv_img = None
    bitmap = None
    screen = None
    colorRAM = None
    background = 0
    try:
        apod_im = requests.get(url, allow_redirects=True)
        print(datetime.now(),'APOD - Image retrieved', file=sys.stderr)

    except:
        print(datetime.now(),'APOD - Error retreiving image', file=sys.stderr)
        return(cv_img, bitmap, screen, colorRAM, background)
    try:
        img = Image.open(BytesIO(apod_im.content))

        img = img.convert("RGB")

        #cv_img, bitmap, screen, colorRAM, background = c64imconvert(img,1)

    except:
        print(datetime.now(),'APOD - Error converting image', file=sys.stderr)

    return (img)

