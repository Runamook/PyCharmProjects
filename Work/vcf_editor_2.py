import re
import codecs
import nltk
import pymorphy2
s = '''
BEGIN:VCARD
VERSION:2.1
N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=A1=D0=B0=D0=BD=D1=82=D0=B5=D1=85=D0=BD=D0=B8=D0=BA;=D0=96=D0=B5=D0=BD=D1=8F;;;
FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=96=D0=B5=D0=BD=D1=8F=20=D0=A1=D0=B0=D0=BD=D1=82=D0=B5=D1=85=D0=BD=D0=B8=D0=BA
TEL;PREF:+791123123
END:VCARD

N разбивается на поля через ; и заносится в название контакта. имя;фамилия;отчество
N заносится в поля контакта

FN разбивается на поля через пробел (0x20) и заносится в детали контакта (строка отображения):
Фамилия =D0=A1=D0=B0=D0=BD=D1=82=D0=B5=D1=85=D0=BD=D0=B8=D0=BA
пробел =20
Женя =D0=96=D0=B5=D0=BD=D1=8F

Отображается как
"Имя - Женя Фамилия - Сантехник"


BEGIN:VCARD
VERSION:3.0
N:FirstName;LastName;;;
FN:First Last
TEL;TYPE=CELL;TYPE=PREF:9999999999
END:VCARD

мих вик шепиль N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=92=D0=B8=D0=BA;=D0=9C=D0=B8=D1=85;=D0=A8=D0=B5=D0=BF=D0=B8=D0=BB=D1=8C;;
тестовый контакт FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=A2=D0=B5=D1=81=D1=82=D0=BE=D0=B2=D1=8B=D0=B9=20=D0=BA=D0=BE=D0=BD=D1=82=D0=B0=D0=BA=D1=82
Такой контакт на ксиаоми отображается следующим образом:
В списке - "мих вик шепиль"
В деталях контакта - "тестовый контакт"
При раскрытии деталей - "мих вик шепиль"  

a = 'ф'
b = a.encode('utf-8')
c = f'={str(b)[4:6].upper()}={str(b)[8:10]}'
'''

'''
d0,d1,d2,d3 -  кириллица
'''
cyrillic = ['D0', 'D1', 'D2', 'D3', ';=D0', ';=D1', ';=D2', ';=D3']
order = {0: 'Имя', 1: 'Фамилия', 2: 'Отчество', 3: 'Обращение', 4: 'Прочее'}
fn_order = {0: 'Фамилия', 1: 'Имя', 2: 'Отчество'}


def string_encoder(in_str):
    encoded_str = in_str.encode('utf-8')
    vcf_string = f'={str(encoded_str)[4:6].upper()}={str(encoded_str)[8:10]}'
    return vcf_string


def string_decoder(rec_type, in_str):
    result = {'rec_type': rec_type}
    if rec_type == 'n':
        result = {'original_line': f'N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:{in_str}'}
    elif rec_type == 'fn':
        result = {'original_line': f'FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:{in_str}'}

    in_str = in_str.strip(';')
    in_str = in_str.lstrip('=')

    if in_str[0:2] not in cyrillic:
        print(f'Wrong string {in_str}')

    result['decoded'] = []
    if rec_type == 'n':
        elements = in_str.split(';')
    elif rec_type == 'fn':
        elements = in_str.split('=20=')
    for i in range(len(elements)):
        orig_string = elements[i].strip('=')
        decoded_str = codecs.decode(''.join(elements[i].split('=')), 'hex').decode('utf-8')
        result['decoded'].append({orig_string: decoded_str})
    return result


def string_decoder_2(in_str):
    results = dict()

    elements = in_str.split(';')
    for i in range(len(elements)):
        if elements[i]:
            vcard_data = codecs.decode(''.join(elements[i].strip('=').split('=')), 'hex').decode('utf-8')
        else:
            # vcard_data = 'Отсутствует'
            vcard_data = None
        results[order[i]] = vcard_data

    return results


def parse_card(card):
    print(f'Card: {card}')
    new_card = ''
    for line in card:
        if re.match(r'^N;CHARSET', line):
            # Отображение контакта
            n_pers_data = string_decoder('n', line[42:])
            print(f'F: {n_pers_data}')
        elif re.match(r'^FN;CHARSET', line):
            # Даные контакта - через пробел (0x20), "фамилия имя"
            fn_pers_data = string_decoder('fn', line[43:])
            print(f'FN: {fn_pers_data}')
        else:
            new_card += line
    return new_card


def last_name_checker(in_str):
    in_str = in_str.strip()
    last_names = ['ов', 'ова', 'ев', 'ева', 'ский', 'ская', 'ин', 'ина']
    black_list = ['Ирина', 'Марина']

    if in_str in black_list:
        return False
    elif in_str[-2:] in last_names or in_str[-3:] in last_names or in_str[-4:] in last_names:
        return True


def printer(in_dict):
    result = ''
    proposed_result = ''
    analyzer = dict()
    for key in in_dict.keys():
        if in_dict[key]:
            result += f'{key}: {in_dict[key]}{" " * 6}'
            if last_name_checker(in_dict[key]):
                # Похоже, что это фамилия
                if key == 'Фамилия':
                    pass
                else:
                    analyzer['Возможная_фамилия'] = in_dict[key]
                    analyzer['Поле_с_возможной_фамилией'] = key

    if analyzer.get('Возможная_фамилия'):
        if in_dict.get('Фамилия'):
            # Swap
            old_last_name = in_dict['Фамилия']
            in_dict['Фамилия'] = analyzer['Возможная_фамилия']
            in_dict[analyzer['Поле_с_возможной_фамилией']] = old_last_name

        else:
            # Move
            in_dict['Фамилия'] = analyzer['Возможная_фамилия']
            in_dict[analyzer['Поле_с_возможной_фамилией']] = None

        for key in in_dict.keys():
            if in_dict[key]:
                proposed_result += f'{key}: {in_dict[key]}{" " * 6}'

    if proposed_result != '':
        print(f'{result}\nПРЕДСКАЗАНИЕ: {proposed_result}')
    else:
        print(result)



def parse_card_2(card):
    # print(f'Card: {card}')
    new_card = ''
    for line in card:
        if re.match(r'^N;CHARSET', line):
            # Отображение контакта
            n_pers_data = string_decoder_2(line[42:])
            printer(n_pers_data)
            # new_n_nf_linse = get_new_lines(n_pers_data)
        else:
            new_card += line
    return new_card


try:
    in_f = open('/media/storage/egk/Pile/Contacts/Copy_Original_Контакты.vcf', 'r')
    out_f = open('/media/storage/egk/Pile/Contacts/Copy_Original_Контакты-decoded.vcf', 'w')
    lines = in_f.read().split('\n')

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
            new_card = parse_card_2(card)
            card = []

finally:
    in_f.close()
    out_f.close()



