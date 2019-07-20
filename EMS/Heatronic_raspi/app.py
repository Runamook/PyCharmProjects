import serial
import sys
try:
    from Tkinter import *
except ModuleNotFoundError:
    from tkinter import *

mGui = Tk()

global crc_table
crc_table = [0x00, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x16, 0x18,
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
global buffer
buffer = [0 for x in range(34)]
port = serial.Serial("/dev/ttyUSB0", 9600)


def byte_holen():
    global byte
    rcv = port.read()
    byte = ord(rcv)


def crc_testen(leng):
    global crc_test
    crc_test = True
    crc = 0
    for i in range(0, leng):
        crc = crc_table[crc]
        crc ^= buffer[i]
    else:
        if crc == buffer[leng]:
            crc_test = True
        else:
            crc_test = False


def haupt():
    while True:

        byte_holen()
        if byte == 0xb0:
            buffer[0] = 0xb0

            for x in range(1, 3):
                byte_holen()
                buffer[x] = byte

            if buffer[1] == 0:
                if buffer[2] == 0xff:

                    for x in range(3, 20):
                        byte_holen()
                        buffer[x] = byte

                    if buffer[3] == 0:
                        if buffer[4] == 0:
                            if buffer[5] == 3:
                                crc_testen(19)
                                #                 print crc_test
                                if crc_test:
                                    if buffer[10] != 255:

                                        T1 = ('Kollektor:' + str('          '))
                                        Label(mGui, text=T1).grid(row=1, column=0, sticky=W)

                                        T1 = ('Kollektor:' + str(float(buffer[10] * 256 + buffer[11]) / 10))
                                        T2 = ('Solarspeicher:' + str(float(buffer[12] * 256 + buffer[13]) / 10))

                                        Label(mGui, text=T1).grid(row=1, column=0, sticky=W)
                                        Label(mGui, text=T2).grid(row=2, column=0, sticky=W)
                                        mGui.update_idletasks()
                                    else:
                                        T1 = ('Kollektor_Winter:' + str(float(255 - buffer[11]) / -10))
                                        T2 = ('Solarspeicher:' + str(float(buffer[12] * 256 + buffer[13]) / 10))

                                        Label(mGui, text=T1).grid(row=1, column=0, sticky=W)
                                        Label(mGui, text=T2).grid(row=2, column=0, sticky=W)
                                        mGui.update_idletasks()
        elif byte == 0x88:
            buffer[0] = 0x88

            for x in range(1, 3):
                byte_holen()
                buffer[x] = byte

            if buffer[1] == 0:
                if buffer[2] == 0x19:
                    for x in range(3, 33):
                        byte_holen()
                        buffer[x] = byte

                    if buffer[3] == 0:

                        crc_testen(31)
                        #                 print crc_test
                        if crc_test == True:
                            if buffer[4] != 255:

                                T3 = ('Aussentemperatur:' + str('          '))
                                Label(mGui, text=T3).grid(row=3, column=0, sticky=W)

                                T3 = ('Aussentemperatur:' + str(float(buffer[4] * 256 + buffer[5]) / 10))
                                Label(mGui, text=T3).grid(row=3, column=0, sticky=W)
                                mGui.update_idletasks()
                            else:
                                T3 = ('Aussentemperatur_Winter:' + str(float(255 - buffer[5]) / -10))
                                Label(mGui, text=T3).grid(row=3, column=0, sticky=W)
                                mGui.update_idletasks()

                elif buffer[2] == 0x18:

                    for x in range(3, 33):
                        byte_holen()
                        buffer[x] = byte

                    if buffer[3] == 0:

                        crc_testen(29)
                        #                print crc_test
                        if crc_test == True:

                            # Установленная температура теплоносителя
                            T4 = ('geforderte Vorlauftemperatur:' + str('     '))
                            #                             print T4
                            Label(mGui, text=T4).grid(row=4, column=0, sticky=W)

                            # Установленная температура теплоносителя
                            T4 = ('geforderte Vorlauftemperatur:' + str(int(buffer[4])))
                            Label(mGui, text=T4).grid(row=4, column=0, sticky=W)

                            # Текущая температура теплоносителя
                            T5 = ('aktuelle Vorlauftemperatur:' + str(float(buffer[5] * 256 + buffer[6]) / 10))
                            Label(mGui, text=T5).grid(row=5, column=0, sticky=W)

                            luefter = buffer[11] and 0xb0

                            if luefter == 0xb0:
                                # Вентилятор горелки ?
                                Label(mGui, text='Luefter Brenner an!').grid(row=8, column=0, sticky=W)
                                buffer[11] = 0
                            else:
                                Label(mGui, text='                                             ').grid(row=8, column=0,
                                                                                                       sticky=W)

                            mGui.update_idletasks()

        elif byte == 0x98:
            buffer[0] = 0x98

            for x in range(1, 3):
                byte_holen()
                buffer[x] = byte

            if buffer[1] == 0:
                if buffer[2] == 0xff:

                    for x in range(3, 23):
                        byte_holen()
                        buffer[x] = byte

                    if buffer[3] == 0:
                        if buffer[5] == 0x6f:

                            crc_testen(15)
                            #                print crc_test
                            if crc_test:
                                # Целевая комнатная температура
                                T6 = ('gewuenschte Raumtemperatur:' + str(float(buffer[8] * 256 + buffer[9]) / 10))
                                Label(mGui, text=T6).grid(row=6, column=0, sticky=W)

                                # Актуальная комнатная температура
                                T7 = ('aktuelle Raumtemperatur:' + str(float(buffer[10] * 256 + buffer[11]) / 10))
                                Label(mGui, text=T7).grid(row=7, column=0, sticky=W)
                                mGui.update_idletasks()


mGui.geometry("300x200")
mGui.title('Junkers CSW14')
haupt()
