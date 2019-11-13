import nfc
#import ndef

clf = nfc.ContactlessFrontend()
clf.open('tty:USB0:pn532')
clf.close()

