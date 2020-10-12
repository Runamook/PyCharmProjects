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


class WordChecker:
    def __init__(self, in_str):
        self.in_str = in_str

    @staticmethod
    def last_name_checker(in_str):
        in_str = in_str.strip()
        last_names = ['ов', 'ова', 'ев', 'ева', 'ский', 'ская', 'ин', 'ина', 'цко', 'шко']
        black_list = ['Ирина', 'Марина']

        if in_str in black_list:
            return False
        elif in_str[-2:] in last_names or in_str[-3:] in last_names or in_str[-4:] in last_names:
            return True

    @staticmethod
    def par_name_checker(in_str):
        in_str = in_str.strip()
        last_names = ['евич', 'овна', 'ович', 'евна']
        black_list = []

        if in_str in black_list:
            return False
        elif in_str[-4:]:
            return True


class VCFFile:
    cyrillic = ['D0', 'D1', 'D2', 'D3', ';=D0', ';=D1', ';=D2', ';=D3']
    order = {0: 'Имя', 1: 'Фамилия', 2: 'Отчество', 3: 'Обращение', 4: 'Прочее'}
    fn_order = {0: 'Фамилия', 1: 'Имя', 2: 'Отчество'}

    n_header = 'N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:'
    fn_header = 'FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:'

    def __init__(self, in_file, out_file):
        self.in_f = open(in_file, 'r')
        self.out_f = open(out_file, 'w')

        self.card = []
        self.new_card = []

        self.analyzer = dict()
        self.flush_analyzer()

    def flush_analyzer(self):
        self.analyzer = {
            'Original': {
                'Имя': None,
                'Фамилия': None,
                'Отчество': None,
                'Обращение': None,
                'Прочее': None
            },
            'Found': {
                'Имя': None,
                'Фамилия': None,
                'Отчество': None,
                'Обращение': None,
                'Прочее': None,
                'name_field': None,
                'surn_field': None,
                'parn_field': None,
                'mr_field': None,
                'other_field': None
            },
            'Final': {
                'Имя': None,
                'Фамилия': None,
                'Отчество': None,
                'Обращение': None,
                'Прочее': None
            },
            'Modified': False
        }

    def debug(self, in_str):
        if self.debug:
            print(f'DEBUG: {in_str}')

    def pretty_print(self):
        # '''
        if self.analyzer['Modified']:
            self.debug(f'MOD: {self.analyzer["Original"]} {self.analyzer["Final"]}')
        else:
            self.debug(f'UNMOD: {self.analyzer["Original"]} {self.analyzer["Final"]}')
        # '''
        # print(self.card)

    def card_fixer(self):
        """
            [
            'BEGIN:VCARD',
            'VERSION:2.1',
            'N;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:;=D0=AA=D1=8A=D1=A7=D0=B5=D0=B2;;;',
            'FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=D0=AA=D1=8A=D1=A7=D0=B5=D0=B2',
            'TEL;CELL:+734592700',
            'END:VCARD'
            ]
            Нужно менять позиции 2 и 3 в листе
        """
        for line in self.card:
            if re.match(r'^N;CHARSET', line):
                # Отображение контакта
                self.string_decoder(line[42:])
                self.analyzer_function()
                self.pretty_print()
        self.new_card = self.card[:]
        self.new_card[2], self.new_card[3] = self.vcf_encoder()
        self.new_card.append('\n')
        self.debug(f'New card: {self.new_card}')

    def analyzer_function(self):
        for key in self.analyzer['Original'].keys():

            if self.analyzer['Original'][key]:
                # Если какое-то поле заполнено в оригинале
                if WordChecker.last_name_checker(self.analyzer['Original'][key]):
                    # Похоже, что это фамилия
                    if key == 'Фамилия':
                        pass
                    else:
                        # Похоже, что фамилия записана не как фамилия
                        self.analyzer['Found']['Фамилия'] = self.analyzer['Original'][key]
                        self.analyzer['Found']['surn_field'] = key
                        self.analyzer['Modified'] = True
        if self.analyzer['Found'].get('Фамилия'):
            # Анализатор нашел фамилию в данных
            if self.analyzer['Original'].get('Фамилия'):
                # Она была записана как что-то другое. В поле "Фамилия" было что-то еще
                self.analyzer['Final']['Фамилия'] = self.analyzer['Found']['Фамилия']
                self.analyzer['Final'][self.analyzer['Found']['surn_field']] = self.analyzer['Original']['Фамилия']

            else:
                # Она была записана как что-то другое в единственное поле
                self.analyzer['Final']['Фамилия'] = self.analyzer['Found']['Фамилия']
                self.analyzer['Final'][self.analyzer['Found']['surn_field']] = None

    def vcf_encoder(self):
        """
            {'Имя': None, 'Фамилия': 'Петров', 'Отчество': None, 'Обращение': None, 'Прочее': None}
        """
        n_result = []
        fn_result = f'{self.fn_header}'
        for key in self.analyzer['Final']:
            # self.debug(n_result)
            if self.analyzer['Final'][key]:
                # self.debug(f'{key, self.analyzer["Final"][key]}')
                vcf_encoded_value = self.string_encoder(self.analyzer['Final'][key])
                n_result.append(vcf_encoded_value)
                fn_result += f'{vcf_encoded_value}=20'
            else:
                # self.debug(f'{key} None')
                n_result.append('')
        fn_result.rstrip('=20')
        n_result = ';'.join(n_result)
        n_result = f'{self.n_header}{n_result}'
        return n_result, fn_result

    def string_encoder(self, in_str):
        result = ''
        for letter in in_str:
            if letter == ' ':
                result += '=20'
            elif letter in ['0', '1,', '2', '3', '4', '5', '6', '7', '8', '9']:
                result += f'={int(letter) + 30}'
            else:
                encoded_str = letter.encode('utf-8')
                vcf_string = f'={str(encoded_str)[4:6].upper()}={str(encoded_str)[8:10]}'
                result += vcf_string.upper()
        self.debug(f'{in_str}: {result}')
        return result

    def string_decoder(self, in_str):
        elements = in_str.split(';')
        for i in range(len(elements)):
            if elements[i]:
                try:
                    vcard_data = codecs.decode(''.join(elements[i].strip('=').strip().split('=')), 'hex').decode('utf-8')
                    self.analyzer['Original'][VCFFile.order[i]] = vcard_data
                    self.analyzer['Final'][VCFFile.order[i]] = vcard_data
                except Exception as e:
                    self.debug(f'ERROR: {e} while processing {in_str}')

    def run(self):
        try:
            lines = self.in_f.read().split('\n')

            for line in lines:
                if line == '':
                    continue
                if re.match(r'^;+$', line):
                    continue
                if line.startswith('='):
                    line = line.lstrip('=')
                    self.card[-1] += line
                    continue
                if 1 < len(line) < 6:
                    self.card[-1] += line
                    continue
                self.card.append(line)
                if 'END:VCARD' in line:
                    self.card_fixer()
                    self.out_f.write('\n'.join(self.new_card))
                    self.card = []
                    self.new_card = []
                    self.flush_analyzer()
        finally:
            self.in_f.close()
            self.out_f.close()


if __name__ == '__main__':
    a = '/media/storage/egk/Pile/Contacts/Copy_Original_Контакты.vcf'
    # a = '/media/storage/egk/Pile/Contacts/test2.vcf'
    b = '/media/storage/egk/Pile/Contacts/Copy_Original_Контакты-decoded3.vcf'
    v = VCFFile(a, b)
    v.run()
