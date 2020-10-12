import vobject
import re
s = '''
BEGIN:VCARD
VERSION:2.1
N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=A1=D0=B0=D0=BD=D1=82=D0=B5=D1=85=D0=BD=D0=B8=D0=BA;=D0=96=D0=B5=D0=BD=D1=8F;;;
FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=96=D0=B5=D0=BD=D1=8F=20=D0=A1=D0=B0=D0=BD=D1=82=D0=B5=D1=85=D0=BD=D0=B8=D0=BA
TEL;PREF:+791123123
END:VCARD
'''

def parse_card(card):
    v = vobject.readOne(card)
    # v.add('sn').value = 'тест'
    v.prettyPrint()
    return


contacts_parsed = 0
blacklist = ''
try:
    f = open('/media/storage/egk/Pile/Contacts/Copy_Original_Контакты.vcf', 'r')
    lines = f.read().split('\n')
    card = []
    for line in lines:
        if re.match(r'^;+$', line):
            continue
        if line.startswith('='):
            line = line.lstrip('=')
            card[-1] += line
            continue

        card.append(line)

        if 'END:VCARD' in line:
            contacts_parsed += 1
            print('\n'.join(card))
            parse_card('\n'.join(card))
            card = []

finally:
    f.close()



