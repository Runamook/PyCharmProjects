#! /usr/bin/python3
#
#################################################################
## Copyright (c) 2013 Norbert S. <junky-zs@gmx.de>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
#################################################################

import sys, tkinter, serial, time, _thread

global g_info_datum
global g_info_zeit
global g_heizgeraet_i_vorlauf_soll
global g_heizgeraet_f_vorlauf_ist
global g_heizgeraet_f_ruecklauf
global g_heizgeraet_f_mischer
global g_heizgeraet_i_betriebsmodus
global g_heizgeraet_b_brenner
global g_heizgeraet_i_leistung
global g_heizgeraet_b_heizungspumpe
global g_heizgeraet_b_zirkulationspumpe
global g_heizgeraet_b_speicherladepumpe

global g_heizkreis_f_Aussen
global g_heizkreis_f_Soll_HK1
global g_heizkreis_f_Ist_HK1
global g_heizkreis_f_Steuer_FB
global g_heizkreis_i_betriebtotal_minuten
global g_heizkreis_i_betriebheizung_minuten
global g_heizkreis_i_brenner_ein_counter
global g_heizkreis_i_betriebsart

global g_warmwasser_i_Soll
global g_warmwasser_f_Ist
global g_warmwasser_f_Speicheroben
global g_warmwasser_i_betriebszeit

global g_solar_f_kollektor
global g_solar_f_speicherunten
global g_solar_i_ertrag_letztestunde
global g_solar_i_laufzeit_minuten
global g_solar_i_laufzeit_stunden
global g_solar_b_pumpe

g_info_datum="--.--.----"
g_info_zeit="--:--:--"
g_heizgeraet_i_vorlauf_soll=0
g_heizgeraet_f_vorlauf_ist=0.0
g_heizgeraet_f_ruecklauf=0.0
g_heizgeraet_f_mischer=0.0
g_heizgeraet_i_betriebsmodus=99
g_heizgeraet_b_brenner=0
g_heizgeraet_i_leistung=0
g_heizgeraet_b_heizungspumpe=0
g_heizgeraet_b_zirkulationspumpe=0
g_heizgeraet_b_speicherladepumpe=0

g_heizkreis_f_Aussen=0.0
g_heizkreis_f_Soll_HK1=0.0
g_heizkreis_f_Ist_HK1=0.0
g_heizkreis_f_Steuer_FB=0.0
g_heizkreis_i_betriebtotal_minuten=0
g_heizkreis_i_betriebheizung_minuten=0
g_heizkreis_i_brenner_ein_counter=0
g_heizkreis_i_betriebsart=0

g_warmwasser_i_Soll=0
g_warmwasser_f_Ist=0.0
g_warmwasser_f_Speicheroben=0.0
g_warmwasser_i_betriebszeit=0

g_solar_f_kollektor=0.0
g_solar_f_speicherunten=0.0
g_solar_i_ertrag_letztestunde=0
g_solar_i_laufzeit_minuten=0
g_solar_i_laufzeit_stunden=0
g_solar_b_pumpe=0


global g_thread_run
g_thread_run=1

global g_update_request
g_update_request=False

global g_thread_lock
g_thread_lock=_thread.allocate_lock()

global g_i_hexheader_counter
g_i_hexheader_counter=0

# port handle
global port

# Display Steuerung
global g_current_display
g_current_display="system"

global crc_table
crc_table =    [0x00, 0x02 ,0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x16, 0x18,
                0x1A, 0x1C, 0x1E, 0x20, 0x22, 0x24, 0x26, 0x28, 0x2A, 0x2C, 0x2E, 0x30, 0x32,
                0x34, 0x36, 0x38, 0x3A, 0x3C, 0x3E, 0x40, 0x42, 0x44, 0x46, 0x48, 0x4A, 0x4C,
                0x4E, 0x50, 0x52, 0x54, 0x56, 0x58, 0x5A, 0x5C, 0x5E, 0x60, 0x62, 0x64, 0x66,
                0x68, 0x6A, 0x6C, 0x6E, 0x70, 0x72, 0x74, 0x76, 0x78, 0x7A, 0x7C, 0x7E, 0x80,
                0x82, 0x84, 0x86, 0x88, 0x8A, 0x8C, 0x8E, 0x90, 0x92, 0x94, 0x96, 0x98, 0x9A,
                0x9C, 0x9E, 0xA0, 0xA2, 0xA4, 0xA6, 0xA8, 0xAA, 0xAC, 0xAE, 0xB0, 0xB2, 0xB4,
                0xB6, 0xB8, 0xBA, 0xBC, 0xBE, 0xC0, 0xC2, 0xC4, 0xC6, 0xC8, 0xCA, 0xCC, 0xCE,
                0xD0, 0xD2, 0xD4, 0xD6, 0xD8, 0xDA, 0xDC, 0xDE, 0xE0, 0xE2, 0xE4, 0xE6, 0xE8,
                0xEA, 0xEC, 0xEE, 0xF0, 0xF2, 0xF4, 0xF6, 0xF8, 0xFA, 0xFC, 0xFE, 0x19, 0x1B,
                0x1D, 0x1F, 0x11, 0x13, 0x15, 0x17, 0x09, 0x0B, 0x0D, 0x0F, 0x01, 0x03, 0x05,
                0x07, 0x39, 0x3B, 0x3D, 0x3F, 0x31, 0x33, 0x35, 0x37, 0x29, 0x2B, 0x2D, 0x2F,
                0x21, 0x23, 0x25, 0x27, 0x59, 0x5B, 0x5D, 0x5F, 0x51, 0x53, 0x55, 0x57, 0x49,
                0x4B, 0x4D, 0x4F, 0x41, 0x43, 0x45, 0x47, 0x79, 0x7B, 0x7D, 0x7F, 0x71, 0x73,
                0x75, 0x77, 0x69, 0x6B, 0x6D, 0x6F, 0x61, 0x63, 0x65, 0x67, 0x99, 0x9B, 0x9D,
                0x9F, 0x91, 0x93, 0x95, 0x97, 0x89, 0x8B, 0x8D, 0x8F, 0x81, 0x83, 0x85, 0x87,
                0xB9, 0xBB, 0xBD, 0xBF, 0xB1, 0xB3, 0xB5, 0xB7, 0xA9, 0xAB, 0xAD, 0xAF, 0xA1,
                0xA3, 0xA5, 0xA7, 0xD9, 0xDB, 0xDD, 0xDF, 0xD1, 0xD3, 0xD5, 0xD7, 0xC9, 0xCB,
                0xCD, 0xCF, 0xC1, 0xC3, 0xC5, 0xC7, 0xF9, 0xFB, 0xFD, 0xFF, 0xF1, 0xF3, 0xF5,
                0xF7, 0xE9, 0xEB, 0xED, 0xEF, 0xE1, 0xE3, 0xE5, 0xE7]

# ########### start getdata - task ##############


def getdata_task(parameter):
    global port
    global buffer
    global crc_test
    
    buffer = [0 for x in range(50)]

    def crc_testen(length):
        global crc_test
        crc_test = True
        crc = 0 
        for i in range(0,length):
            crc = crc_table[crc] 
            crc ^= buffer[i]
        else:
            if crc == buffer[length]:
                crc_test = True
            else:
                crc_test = False         

    # ## Datum / Uhrzeit ##
    def DatumUhrzeitMsg():
        global g_info_datum
        global g_info_zeit

        for x in range (4,14):
            buffer[x] = ord(port.read())
        crc_testen(12)
        if crc_test:
            iyear = int(buffer[4]+2000)
            imonth = int(buffer[5])
            ihour = int(buffer[6])
            iday = int(buffer[7])
            iminute = int(buffer[8])
            isecond = int(buffer[9])
            idayofweek = int(buffer[10])
            g_info_datum = format(iday, "2d")+"."+format(imonth, "2d")+"."+format(iyear, "4d")
            g_info_zeit = format(ihour, "2d")+":"+format(iminute, "2d")+":"+format(isecond, "2d")

            if g_current_display=="system":
                temptext="DA:"
                for x in range (0,14):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext,"b_gray")
               
                g_thread_lock.acquire()
                global g_update_request
                global g_i_hexheader_counter
                g_update_request=True
                g_i_hexheader_counter+=1
                g_thread_lock.release()


    ### Heizgeraet ##            
    def HeizgeraetMsg():
        global g_heizgeraet_i_vorlauf_soll
        global g_heizgeraet_f_vorlauf_ist
        global g_heizgeraet_f_ruecklauf
        global g_heizgeraet_f_mischer
        global g_heizgeraet_i_betriebsmodus
        global g_heizgeraet_b_brenner
        global g_heizgeraet_i_leistung
        global g_heizgeraet_b_heizungspumpe
        global g_heizgeraet_b_zirkulationspumpe
        global g_heizgeraet_b_speicherladepumpe

        for x in range (4,31):
            buffer[x] = ord(port.read())
        crc_testen(29)
        if crc_test == True:
            g_heizgeraet_i_vorlauf_soll =int(buffer[4])
            g_heizgeraet_f_vorlauf_ist  =float(buffer[5]*256+ buffer[6])/10
            g_heizgeraet_i_leistung     =int(buffer[8])
            # Kesselbetriebsart Heizen:=0x5x, Warmwasser:=0x6x
            if (buffer[7] & 0x50) == 0x50:
                g_heizgeraet_i_betriebsmodus =1
            else:
                g_heizgeraet_i_betriebsmodus =0

            g_heizgeraet_f_mischer  = float(buffer[13]*256+ buffer[14])/10
            g_heizgeraet_f_ruecklauf= float(buffer[17]*256+ buffer[18])/10
                
            # Extract Bitfeld
            #
            #   Bitfeld: Bit7&8 nur fuer Warmwasser; (Bits von rechts gezaehlt - beginnt 1)
            #   Bit8: Zirkulationspumpe Warmwasser
            #   Bit7: Speicherladepumpe Warmwasser
            #   Bit6: immer 1
            #   Bit5: immer 0
            #   Bit4: Zuendung des Brenners
            #   Bit3: waehrend Verbrennung 1 mit etwas laengerem Vor- und Nachlauf vgl. Bit8
            #   Bit2: immer 0
            #   Bit1: waehrend Verbrennung 1 mit kurzem Vor- und Nachlauf

            g_heizgeraet_b_brenner       = int(buffer[11] & 0x01)
            g_heizgeraet_b_heizungspumpe = int(buffer[11] & 0x20)
            g_heizgeraet_b_speicherladepumpe= int(buffer[11] & 0x40)
            g_heizgeraet_b_zirkulationspumpe= int(buffer[11] & 0x80)

            if g_current_display=="heizgeraet" or g_current_display=="system":
                temptext="HG:"
                for x in range (0,31):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext,"b_or")

                g_thread_lock.acquire()
                global g_update_request
                global g_i_hexheader_counter
                g_update_request=True
                g_i_hexheader_counter+=1
                g_thread_lock.release()


    ### Heizkreismessage1 ##            
    def HeizkreisMsg():
        global g_heizkreis_f_Aussen
        global g_heizkreis_i_betriebtotal_minuten
        global g_heizkreis_i_betriebheizung_minuten
        global g_heizkreis_i_brenner_ein_counter

        for x in range (4,33):
            buffer[x] = ord(port.read())
        crc_testen(31)
        if crc_test == True:
            if buffer[4] != 255:
                g_heizkreis_f_Aussen=float(buffer[4]*256+buffer[5])/10
            else:
                g_heizkreis_f_Aussen=float(255-buffer[5])/-10

            g_heizkreis_i_betriebtotal_minuten  =int(buffer[17]*65536+ buffer[18]*256+ buffer[19])
            g_heizkreis_i_betriebheizung_minuten=int(buffer[23]*65536+ buffer[24]*256+ buffer[25])
            g_heizkreis_i_brenner_ein_counter   =int(buffer[14]*65536+ buffer[15]*256+ buffer[16])

            if g_current_display=="heizkreis" or g_current_display=="system":
                temptext="HK:"
                for x in range (0,33):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext,"b_mocca")
            
                g_thread_lock.acquire()
                global g_update_request
                global g_i_hexheader_counter
                g_update_request=True
                g_i_hexheader_counter+=1
                g_thread_lock.release()
 
            
    ### Heizkreismessage2 ##            
    def HeizkreisMsg_FW100_200Msg():
        global g_heizkreis_f_Soll_HK1
        global g_heizkreis_f_Ist_HK1
        global g_heizkreis_f_Steuer_FB
        global g_heizkreis_i_betriebsart

        for x in range (4,17):
            buffer[x] = ord(port.read())
        crc_testen(15)
        if crc_test == True:
            g_heizkreis_i_betriebsart   =int(buffer[6])
            # //6F
            if buffer[5] == 111:
                g_heizkreis_f_Soll_HK1  =float(buffer[8]*256+ buffer[9])/10
                g_heizkreis_f_Ist_HK1   =float(buffer[10]*256+ buffer[11])/10
                g_heizkreis_f_Steuer_FB =float(buffer[12]*256+ buffer[13])/10

            if g_current_display=="heizkreis" or g_current_display=="system":
                temptext="HK:"
                for x in range (0,17):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext,"b_mocca")

                g_thread_lock.acquire()
                global g_update_request
                global g_i_hexheader_counter
                g_update_request=True
                g_i_hexheader_counter+=1
                g_thread_lock.release()
     

    def WarmwasserMsg():
        global g_warmwasser_i_Soll
        global g_warmwasser_f_Ist
        global g_warmwasser_f_Speicheroben
        global g_warmwasser_i_betriebszeit


        for x in range (4,23):
            buffer[x] = ord(port.read())
        crc_testen(21)
        if crc_test == True:
            g_warmwasser_i_Soll         =int(buffer[4])
            g_warmwasser_f_Ist          =float(buffer[5]*256+ buffer[6])/10
            g_warmwasser_f_Speicheroben =float(buffer[7]*256+ buffer[8])/10
            g_warmwasser_i_betriebszeit =int(buffer[14]*65536+ buffer[15]*256+ buffer[16])

            if g_current_display=="warmwasser" or g_current_display=="system":
                temptext="WW:"
                for x in range (0,23):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext,"b_bl")
            
                g_thread_lock.acquire()
                global g_update_request
                global g_i_hexheader_counter
                g_update_request=True
                g_i_hexheader_counter+=1
                g_thread_lock.release()
            
 
    ### Solarmessage ##            
    def SolarMsg():
        global g_solar_f_kollektor
        global g_solar_f_speicherunten
        global g_solar_i_ertrag_letztestunde
        global g_solar_i_laufzeit_minuten
        global g_solar_i_laufzeit_stunden
        global g_solar_b_pumpe
        laenge = 21
        for x in range (4,laenge):
            buffer[x] = ord(port.read())
## not yet defined            
#        if buffer[5] == 1:
#            laenge = 21
#            for x in range (21, laenge):
#                buffer[x] = ord(port.read())
            
        crc_testen(laenge-2)
        if crc_test == True:
            if buffer[5] == 3:
                # Solarkreis1
                if buffer[10] != 255:
                    g_solar_f_kollektor     =float(buffer[10]*256+ buffer[11])/10
                    g_solar_f_speicherunten =float(buffer[12]*256+ buffer[13])/10
                else:
                    g_solar_f_kollektor     = float(255 - buffer[11])/(-10)
                    g_solar_f_speicherunten = float(buffer[12]*256+ buffer[13])/10

                g_solar_b_pumpe = (buffer[14] & 0x01)

            # Auswertung der Solarertrag letze Stunde Bytes: 8-9
            g_solar_i_ertrag_letztestunde =int(buffer[8]*256+ buffer[9])

            # Auswertung der Solarlaufzeiten
            g_solar_i_laufzeit_minuten =int(buffer[17]*256+buffer[18])
            g_solar_i_laufzeit_stunden =int(g_solar_i_laufzeit_minuten/60)

            if g_current_display=="solar" or g_current_display=="system":
                temptext="SO:"
                for x in range (0,21):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext,"b_gr")

                g_thread_lock.acquire()
                global g_update_request
                global g_i_hexheader_counter
                g_update_request=True
                g_i_hexheader_counter+=1
                g_thread_lock.release()

    # Requestmessage ##
    def RequestMsg():
        for x in range (4,21):
            buffer[x] = ord(port.read())
        crc_testen(19)
        if crc_test == True:
            # TBD, noch nicht ausgewertet
            
            if g_current_display=="system":
                temptext="RQ:"
                for x in range (0,21):
                    temptext = temptext+" "+format(buffer[x],"02x")
                temptext += "\n"
                hextext.insert("end",temptext)
                
                g_thread_lock.acquire()
                global g_i_hexheader_counter
                g_i_hexheader_counter += 1
                g_thread_lock.release()

    # check Msg-header and extract data
    def CheckMsgHeader(firstbyte):
        if firstbyte == 0x88:
            buffer[0] = firstbyte
            for x in range (1,4):
                buffer[x] = ord(port.read())
            if buffer[1] == 0:
                # Telegram: Heizgeraet (88001800) ##
                if buffer[2] == 0x18:
                    if buffer[3] == 0:
                        HeizgeraetMsg()
                # Telegram: Heizkreis1 (88001900) ##
                elif buffer[2] == 0x19:
                    if buffer[3] == 0:
                        HeizkreisMsg()
                # Telegram: Warmwasser (88003400) ##
                elif buffer[2] == 0x34:
                    if buffer[3] == 0:
                        WarmwasserMsg()
                # Telegram: Request    (88000700) ##
                elif buffer[2] == 0x07:
                    if buffer[3] == 0:
                        RequestMsg()

        # Telegram: HK2 / Datum ##
        if firstbyte == 0x90:
            buffer[0] = firstbyte
            for x in range(1, 4):
                buffer[x] = ord(port.read())
            if buffer[1] == 0:
                # Telegram: Heizkreis2 (9000FF00) ##
                if buffer[2] == 0xff:
                    if buffer[3] == 0:
                        HeizkreisMsg_FW100_200Msg()
                # Telegram: Datum / Uhrzeit (90000600) ##
                elif buffer[2] == 6:
                    if buffer[3] == 0:
                        DatumUhrzeitMsg()

        # Telegram: ISM Solarinfo (B000FF00) ##
        elif firstbyte == 0xb0:
            buffer[0] = firstbyte
            for x in range (1,4):
                buffer[x] = ord(port.read())
            if buffer[1] == 0:
                if buffer[2] == 0xff:
                    if buffer[3] == 0:
                        SolarMsg()

    # ####### endless - loop until end
    while g_thread_run:
        global g_update_request
        global g_i_hexheader_counter

        read_byte = ord(port.read())
        CheckMsgHeader(read_byte)
        
        g_thread_lock.acquire()
        if g_update_request:
            if (g_i_hexheader_counter % 40) == 0:
                Hextext_bytecomment()
            g_update_request=False
            anzeigesteuerung()
        g_thread_lock.release()
        
    
################################################

# ##### grafische anzeigeroutinen
def ende():
    g_thread_run=0
    sys.exit(0)


def Lokalezeit():
    text.insert("end", "                                 \n","u")
    text.insert("end", "Aktuelles Datum / Zeit           \n","u")
    datum = '        Datum: ' + time.strftime("%d:%m:%Y")+'\n'
    zeit = '        Zeit : ' + time.strftime("%H:%M:%S")+'\n'
    text.insert("end", datum)
    text.insert("end", zeit)


def system_button():
    global g_current_display
    g_current_display="system"
    clear()
    Lokalezeit()
    System()


def System():
    text.insert("end", "Systemstatus Junkers Heatronic3  \n", "b_ye")
    Info()
    Heizgeraet()
    Heizkreis()
    Warmwasser()
    Solar()
    text.insert("end", "                                 \n", "u")


def Info():
    text.insert("end", "System-Infos                     \n", "b_gray")
    datum = ' System-Datum: ' + g_info_datum+'\n'
    text.insert("end", datum)
    uhrzeit = ' System-Zeit : ' + g_info_zeit+'\n'
    text.insert("end", uhrzeit)


def Heizgeraet_button():
    global g_current_display
    g_current_display = "heizgeraet"
    clear()
    Lokalezeit()
    Heizgeraet()


def Heizgeraet():
    text.insert("end", "Heizgeraet                       \n", "b_or")
    temptext = " T-Vorlauf Soll       : "+format(g_heizgeraet_i_vorlauf_soll, "2d")+'   Grad\n'
    text.insert("end", temptext)
    temptext = " T-Vorlauf ist        : "+format(g_heizgeraet_f_vorlauf_ist, ".1f")+' Grad\n'
    text.insert("end", temptext)
    temptext = " T-Ruecklauf          : "+format(g_heizgeraet_f_ruecklauf, ".1f")+' Grad\n'
    text.insert("end", temptext)
    temptext = " T-Mischer            : "+format(g_heizgeraet_f_mischer, ".1f")+' Grad\n'
    text.insert("end", temptext)
    temptext=" Betriebsmodus        : "+GetStrBetriebsmodus(g_heizgeraet_i_betriebsmodus)+' (Heizen/Warmwasser)\n'
    text.insert("end", temptext)
    temptext=" Brenner              : "+GetStrOnOff(g_heizgeraet_b_brenner)+'\n'
    text.insert("end",temptext)
    temptext=" Leistung             : "+format(g_heizgeraet_i_leistung,"d")+'    %\n'
    text.insert("end",temptext)
    temptext=" Heizubgspumpe        : "+GetStrOnOff(g_heizgeraet_b_heizungspumpe)+'\n'
    text.insert("end",temptext)
    temptext=" Zirkulationspumpe    : "+GetStrOnOff(g_heizgeraet_b_zirkulationspumpe)+'\n'
    text.insert("end",temptext)
    temptext=" Speicherladepumpe    : "+GetStrOnOff(g_heizgeraet_b_speicherladepumpe)+'\n'
    text.insert("end",temptext)
    
    if g_current_display=="heizgeraet":
        text.insert("end","\n")
        text.insert("end","Byte-Nr  Wert(hex)      Bedeutung         \n","b_gray")
        text.insert("end"," 00-03   88 00 18 00    Telegram-Kennung \n")
        text.insert("end"," 04      xy             T-Vorlauf Soll \n")
        text.insert("end"," 05      Hi-Byte        T-Vorlauf Ist\n")
        text.insert("end"," 06      Lo-Byte        T-Vorlauf Ist\n")
        text.insert("end"," 07      5x/<>5x        Betriebsmodus: Heizen/Warmwasser\n")
        text.insert("end"," 08      xy             Brennerleistung\n")
        text.insert("end"," 09      01/09          ? \n")
        text.insert("end"," 10      xy             ? \n")
        text.insert("end"," 11      Bitfeld        87654321 BitNr\n")
        text.insert("end","                        8          Zirkulationspumpe WW\n")
        text.insert("end","                         7         Speicherladepumpe WW\n")
        text.insert("end","                          6        Heizungspumpe\n")
        text.insert("end","                           5       Immer 0 ?\n")
        text.insert("end","                            4      Zuendung des Brenner\n")
        text.insert("end","                             3     Brenner an mit Vor-Nachlauf\n")
        text.insert("end","                              2    Immer 0 ?\n")
        text.insert("end","                               1   Brenner an mit Vor-Nachlauf\n")
        
        text.insert("end"," 12      c0             ?\n")
        text.insert("end"," 13      Hi-Byte        T-Mischer\n")
        text.insert("end"," 14      Lo-Byte        T-Mischer\n")
        text.insert("end"," 15-16   80/00          ?\n")
        text.insert("end"," 17      Hi-Byte        T-Ruecklauf\n")
        text.insert("end"," 18      Lo-Byte        T-Ruecklauf\n")
        text.insert("end"," 19-28   xy             ?\n")
        text.insert("end"," 29      xy             CRC Wert\n")


def Heizkreis_button():
    global g_current_display
    g_current_display="heizkreis"
    clear()
    Lokalezeit()
    Heizkreis()

def Heizkreis():
    text.insert("end", "Heizkreis                        \n","b_mocca")
    temptext=" T-Aussen             : "+format(g_heizkreis_f_Aussen,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" T-Soll Heizkreis 1   : "+format(g_heizkreis_f_Soll_HK1,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" T-Ist  Heizkreis 1   : "+format(g_heizkreis_f_Ist_HK1,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" T-Steuer Fernbedien. : "+format(g_heizkreis_f_Steuer_FB,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" Betrieb Total        : "+format(g_heizkreis_i_betriebtotal_minuten,"d")+' Minuten := '+ \
                  format(g_heizkreis_i_betriebtotal_minuten/60,".0f")+' Stunden\n'
    text.insert("end",temptext)
    temptext=" Betrieb Heizung      : "+format(g_heizkreis_i_betriebheizung_minuten,"d")+' Minuten := '+ \
                  format(g_heizkreis_i_betriebheizung_minuten/60,".0f")+' Stunden\n'
    text.insert("end",temptext)
    temptext=" Brenner Ein Counter  : "+format(g_heizkreis_i_brenner_ein_counter,"d")+'\n'
    text.insert("end",temptext)
    temptext=" Betriebsart          : "+GetStrBetriebsart(g_heizkreis_i_betriebsart)+' (Heizen/Sparen/Frost)\n'
    text.insert("end",temptext)
    
    if g_current_display=="heizkreis":
        text.insert("end","\n")
        text.insert("end","Byte-Nr  Wert(hex)      Bedeutung         \n","b_gray")
        text.insert("end"," 00-03   88 00 19 00    Telegram-Kennung \n")
        text.insert("end"," 04      Hi-Byte        T-Aussen\n")
        text.insert("end"," 05      Lo-Byte        T-Aussen\n")
        text.insert("end"," 06-16   xy             ?\n")
        text.insert("end"," 17-19   B3 B2 B1       Betrieb Total   (Minuten)\n")
        text.insert("end"," 20-22   xy             ?\n")
        text.insert("end"," 23-25   B3 B2 B1       Betrieb Heizung (Minuten) \n")
        text.insert("end"," 26-30   xy             ?\n")
        text.insert("end"," 31      xy             CRC\n")

        text.insert("end","\n")
        text.insert("end","Byte-Nr  Wert(hex)      Bedeutung         \n","b_gray")
        text.insert("end"," 00-03   90 00 ff 00    Telegram-Kennung \n")
        text.insert("end"," 04      xy             ?\n")
        text.insert("end"," 05      6f/70/?        Heizkreis 1/2 ?\n")
        text.insert("end"," 06      01/02/03       Betriebsart (Frost/Sparen/Heizen)\n")
        text.insert("end"," 07      xy             ?\n")
        text.insert("end"," 08      Hi-Byte        T-Soll Heizkreis 1\n")
        text.insert("end"," 09      Lo-Byte        T-Soll Heizkreis 1\n")
        text.insert("end"," 10      Hi-Byte        T-Ist  Heizkreis 1\n")
        text.insert("end"," 11      Lo-Byte        T-Ist  Heizkreis 1\n")
        text.insert("end"," 12      Hi-Byte        T-Fernbedienung\n")
        text.insert("end"," 13      Lo-Byte        T-Fernbedienung\n")
        text.insert("end"," 14      xy             ?\n")
        text.insert("end"," 15      xy             CRC\n")

def Warmwasser_button():
    global g_current_display
    g_current_display="warmwasser"
    clear()
    Lokalezeit()
    Warmwasser()

def Warmwasser():
    text.insert("end", "Warmwasser                       \n","b_bl")
    temptext=" T-Soll               : "+format(g_warmwasser_i_Soll,"2d")+'   Grad\n'
    text.insert("end",temptext)
    temptext=" T-Ist (Mischer)      : "+format(g_warmwasser_f_Ist,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" T-Speicher           : "+format(g_warmwasser_f_Speicheroben,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" Betriebszeit         : "+format(g_warmwasser_i_betriebszeit,"d")+' Minuten := '+ \
                  format(g_warmwasser_i_betriebszeit/60,".0f")+' Stunden\n'
    text.insert("end",temptext)
    
    if g_current_display=="warmwasser":
        text.insert("end","\n")
        text.insert("end","Byte-Nr  Wert(hex)      Bedeutung         \n","b_gray")
        text.insert("end"," 00-03   88 00 34 00    Telegram-Kennung \n")
        text.insert("end"," 04      xy             T-Soll\n")
        text.insert("end"," 05      Hi-Byte        T-Ist (Mischer)\n")
        text.insert("end"," 06      Lo-Byte        T-Ist (Mischer)\n")
        text.insert("end"," 07      Hi-Byte        T-Speicher\n")
        text.insert("end"," 08      Lo-Byte        T-Speicher\n")
        text.insert("end"," 09-13   xy             ?\n")
        text.insert("end"," 14-16   B3 B2 B1       Betriebszeit (Minuten)\n")
        text.insert("end"," 17-20   xy             ?\n")
        text.insert("end"," 21      xy             CRC\n")

def Solar_button():
    global g_current_display
    g_current_display="solar"
    clear()
    Lokalezeit()
    Solar()

def Solar():
    text.insert("end", "Solar                            \n","b_gr")
    temptext=" T-Kollektor          : "+format(g_solar_f_kollektor,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" T-Speicher unten     : "+format(g_solar_f_speicherunten,".1f")+' Grad\n'
    text.insert("end",temptext)
    temptext=" Ertrag letzte Stunde : "+format(g_solar_i_ertrag_letztestunde,"d")+'\n'
    text.insert("end",temptext)
    g_solar_i_laufzeit_stunden=g_solar_i_laufzeit_minuten / 60
    temptext=" Laufzeit             : "+format(g_solar_i_laufzeit_minuten,"d")+' Minuten := '+ \
                  format(g_solar_i_laufzeit_stunden,".0f")+' Stunden\n'
    text.insert("end",temptext)
    temptext=" Solarpumpe           : "+GetStrOnOff(g_solar_b_pumpe)+'\n'
    text.insert("end",temptext)

    if g_current_display=="solar":
        text.insert("end","\n")
        text.insert("end","Byte-Nr  Wert(hex)      Bedeutung \n","b_gray")
        text.insert("end"," 00-03   b0 00 ff 00    Telegram-Kennung \n")
        text.insert("end"," 04      00             ? \n")
        text.insert("end"," 05      03             ? Solarkreis\n")
        text.insert("end"," 06,07   Bitfeld        ? \n")
        text.insert("end"," 08      Hi-Byte        Ertrag letzte Stunde \n")
        text.insert("end"," 09      Lo-Byte        Ertrag letzte Stunde\n")
        text.insert("end"," 10      Hi-Byte        T-Kollektor      \n")
        text.insert("end"," 11      Lo-Byte        T-Kollektor      \n")
        text.insert("end"," 12      Hi-Byte        T-Speicher unten \n")
        text.insert("end"," 13      Lo-Byte        T-Speicher unten \n")
        text.insert("end"," 14      Bitfeld        Solarpumpe 00/01:=aus/ein\n")
        text.insert("end"," 15-16   00/00          ?\n")
        text.insert("end"," 17      Hi-Byte        Laufzeit Solarpumpe (Minuten)\n")
        text.insert("end"," 18      Lo-Byte        Laufzeit Solarpumpe (Minuten)\n")
        text.insert("end"," 19      xy             CRC Wert\n")


def clear():
        text.delete(1.0,"end")

def hexclear():
        hextext.delete(1.0,"end")
        Hextext_bytecomment()
        global g_i_hexheader_counter
        g_i_hexheader_counter=0


def GetStrOnOff(bitvalue):
        if bitvalue == 0:
            return "Aus"
        else: return "An"

def GetStrBetriebsmodus(ivalue):
        if ivalue == 1:
            return "Heizen"
        elif  ivalue == 0:
            return "Warmwasser"
        else:
            return "--"

def GetStrBetriebsart(ivalue):
        if ivalue == 1:
            return "Frost"
        elif ivalue == 2:
            return "Sparen"
        elif ivalue == 3:
            return "Heizen"
        else:
            return "---"

def colourconfig(obj):
    obj.tag_config("f_bl", foreground="black")
    obj.tag_config("b_ye", background="yellow")
    obj.tag_config("b_bl", background="lightblue")
    obj.tag_config("b_gr", background="lightgreen")
    obj.tag_config("b_rd", background="red")
    obj.tag_config("b_mocca", background="moccasin")
    obj.tag_config("b_gray", background="lightgray")
    obj.tag_config("b_or", background="orange")
    obj.tag_config("u", underline=True)

def Hextext_bytecomment():
    global hextext
    temptext="BNr"
    for x in range (0,33):
        temptext = temptext+" "+format(x,"02d")
    hextext.insert("end",temptext+'\n',"b_ye")

def anzeigesteuerung():
    global g_current_display
    
    clear()
    Lokalezeit()
    if g_current_display=="system":
        System()
    elif g_current_display=="heizgeraet":
        Heizgeraet()
    elif g_current_display=="heizkreis":
        Heizkreis()
    elif g_current_display=="warmwasser":
        Warmwasser()
    elif g_current_display=="solar":
        Solar()
    else:
        System()


# #################################


def openport():
    global port
    try:
        port = serial.Serial("/dev/ttyUSB0", 9600)
    except:
        antwort = tkinter.messagebox.askokcancel("Fehler","Keine Verbindung mit USB-Port \
                     Versuch mit COM-Port ?")
        if antwort == 1:
            try:
                port = serial.Serial("/dev/ttyAMA0", 9600 )
            except:
                tkinter.messagebox.showerror("Fehler","Keine Verbindung mit COM-Port möglich!")
                ende()
        else:
            ende()


# ######### main block ############


openport()

main = tkinter.Tk()
main.geometry("1000x700+330+230")
main.title('Junkers CSW Heatronic3 Analyser')

# Frame 1,2,3 mit Buttons 
fr1 = tkinter.Frame(main, relief="sunken", bd=5)
fr1.pack(side="top")
fr2 = tkinter.Frame(fr1, relief="sunken", bd=2)
fr2.pack(side="left")
fr3 = tkinter.Frame(fr1, relief="sunken", bd=3)
fr3.pack(side="right")

bhexdclear = tkinter.Button(fr2, text="Hexdump clear", command = hexclear)
bhexdclear.pack(padx=5, pady=5, side="left")
bende = tkinter.Button(fr2, text = "Ende", command = ende)
bende.pack(padx=5, pady=5, side="right")

bsys = tkinter.Button(fr3, text="System", command = system_button)
bsys.pack(padx=5, pady=5, side="left")
bhge = tkinter.Button(fr3, text="Heizgeraet", command = Heizgeraet_button)
bhge.pack(padx=5, pady=5, side="left")
bhkr = tkinter.Button(fr3, text="Heizkreis", command = Heizkreis_button)
bhkr.pack(padx=5, pady=5, side="left")
bwwa = tkinter.Button(fr3, text="Warmwasser", command = Warmwasser_button)
bwwa.pack(padx=5, pady=5, side="left")
bsola = tkinter.Button(fr3, text="Solar", command = Solar_button)
bsola.pack(padx=5, pady=5, side="left")


# frame for hexdump
hexdumpfr = tkinter.Frame(main, width=1000, relief="sunken", bd=1)
hexdumpfr.pack(side="left", expand=1, fill="both")
global hextext
hextext = tkinter.Text(hexdumpfr)
hextext.pack(side="left", expand=1, fill="both")
colourconfig(hextext)
Hextext_bytecomment()

# frame for data
datafr = tkinter.Frame(main, width=1, relief="sunken", bd=4)
datafr.pack(side="left", fill="both")
text = tkinter.Text(datafr)
text.pack(side="left", expand=1, fill="both")
colourconfig(text)

getdata_threadID = _thread.start_new_thread(getdata_task, (0,))

main.mainloop()
# ########### end main - task ###############

