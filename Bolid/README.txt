
"""
Зона типа 6 позволяет получать числовое значение.

На рисунке 7 зона No11 имеет код типа равный 6. Запрос состояния этой зоны – чтение регистра Modbus с адресом 40010.
Но эту же зону можно опросить и как «числовое значения параметра» – записать в регистр Modbus с адресом 46179 номер зоны (в данном случае No зоны = 11) и
затем получить числовое значение параметра – прочитать регистр Modbus с адресом 46328.
"""


"""
Получение информации от приборов системы «Орион»

SCADA может получать информацию от приборов системы «Орион» двумя способами:
• запрос состояния зоны (реле);
• запрос события.
Запрос состояния зон (реле) целесообразен при старте системы для определения «текущего» состояния зон.
Этот способ неэффективно использует трафик, так как запрашиваются и передаются состояния всех зон, в том числе и тех, состояние которых не изменилось.
Запрос событий позволяет оптимизировать трафик и быстрее получать изменения в состоянии зон.
«С2000-ПП» поддерживает два способа запроса событий:
• запрос самого «старого» события;
• запрос события, номер которого был предварительно установлен.

«С2000-ПП» осуществляет диспетчеризацию событий по следующим правилам:
− после заполнения кольцевого буфера событий (ёмкость буфера = 256) «С2000-ПП» размещает очередное событие на месте самого «старого» по времени события;
− на запрос события (адрес Modbus = 46264) «С2000-ПП» возвращает самое старое непрочитанное событие;
− событие считается прочитанным только после того, как для него будет установлен признак «Событие прочитано» (адрес Modbus = 46163);
− если у «С2000-ПП» нет непрочитанных событий, то на запрос события он возвращает событие со всеми байтами равными 0.

1. Читаем самое старое, если не 0 -> #2
2. Помечаем как прочитанное
3. Goto #1
"""
# Состояние зона [40000]: 6332 == 3f20


"""
**Тепловик**
Запрос первой зоны Modbus (40000 = 9c40)
0:35:37 -> 02 03 9C 40 00 01 AB BD
Ответ
0:35:37 <- 02 03 02 18 BC F7 F5  [CRC OK]
02 - адрес С2000ПП
03 - Операция modbus
02 - счетчик байтов
18bc - 6332 или 24+188

24 Взятие входа на охрану
Вход взят на охрану
Поля: (1), (2), 3, 11

188 Восстановление связи со входом
Подключен извещатель: восстановлена связь «С2000-КДЛ» с потерянным ранее адресным извещателем или расширителем, либо восстановлена связь «С2000-АСПТ» с «С2000-КПБ»
Поля (2), 3, 11

f7f5 - CRC



**Дымовик**
0:55:17 -> 02 03 9C 41 00 01 FA 7D
0:55:17 <- 02 03 02 18 BC F7 F5  [CRC OK]
 24+188

**КДЛ**
0:55:32 -> 02 03 9C 42 00 01 0A 7D
0:55:33 <- 02 03 02 C7 2F EF A8  [CRC OK]
C7 2F = 199 47
47 Восстановление ДПЛС
Восстановление двухпроводной линии после обрыва или КЗ
Поля (2), 3, 11

199 Восстановление источника питания
Напряжение питания прибора пришло в норму после аварии
Поля (2), 3, 11

**С2000М**
0:55:42 -> 02 03 9C 43 00 01 5B BD
0:55:42 <- 02 03 02 FA BB FE 97  [CRC OK]
FA BB = 250 187
250 Потеряна связь с прибором
Поля (2), (3), 11

187 Потеря связи со входом
Отключен извещатель: потеряна связь контроллера «С2000-КДЛ» с адресным извещателем или расширителем, либо потеряна связь «С2000-АСПТ» с подключенными
к нему «С2000-КПБ»
Поля (2), 3, 11

**Опросник (пульт)**
0:55:47 -> 02 03 9C 44 00 01 EA 7C
0:55:47 <- 02 03 02 FB 00 BF 74  [CRC OK]
FB 00 = 251 0

251 Восстановлена связь с прибором
Поля (2), (3), 11

**Окно**
0:55:52 -> 02 03 9C 45 00 01 BB BC
0:55:52 <- 02 03 02 6D BC D1 65  [CRC OK]
6D BC = 109 188
109 Снятие входа с охраны
Вход снят с охраны!»
Поля (1), (2), 3, 11

188 Восстановление связи со входом
Подключен извещатель: восстановлена связь «С2000-КДЛ» с потерянным ранее адресным извещателем или расширителем, либо восстановлена связь «С2000-АСПТ» с «С2000-КПБ»
Поля (2), 3, 11

**СМК**
0:55:56 -> 02 03 9C 46 00 01 4B BC
0:55:56 <- 02 03 02 6D BC D1 65  [CRC OK]

109 188


0:56:01 -> 02 03 9C 47 00 01 1A 7C
0:56:01 <- 02 83 03 F1 31  <ILLEGAL DATA VALUE> [CRC OK]

83 = ошибка в запросе
Величина, содержащаяся в поле данных запроса, является недопустимой величиной для ведомого


Запросить сразу несколько полей - зон (если больше 8 - ответит ошибкой, так как сейчас всего 8 зон)
1:28:30 -> 02 03 9C 40 00 07 2B BF
1:28:30 <- 02 03 0E 18 BC 18 BC C7 2F FA BB FB 00 6D BC 6D BC EC B7  [CRC OK]

0e - 14 байт в ответе (соответствуют байтам из отдельных ответов выше)
18 BC
18 BC
C7 2F
FA BB
FB 00
6D BC
6D BC
"""


"""
События

"Запрос номера самого нового события": 46160, b450
2:27:52 -> 02 03 B4 50 00 03 22 19
2:27:52 <- 02 03 06 00 A0 00 01 00 A0 E4 24  [CRC OK]
2:27:38 -> 02 03 B4 50 00 01 A3 D8
2:27:39 <- 02 03 02 00 A0 FC 3C  [CRC OK]
00 A0
Событие 160 (А0)

"Запрос номера самого старого события": 46161, b451

2:36:02 -> 02 03 B4 51 00 01 F2 18
2:36:02 <- 02 03 02 00 01 3D 84  [CRC OK]

"Запрос количества непрочитанных событий": 46162, b452

2:35:25 -> 02 03 B4 52 00 01 02 18
2:35:25 <- 02 03 02 00 A0 FC 3C  [CRC OK]
"Установка признака «Событие прочитано»": 46163, b453
"Запрос события": 46264, b4b8

2:34:47 -> 02 03 B4 B8 00 0E 63 E8
2:34:47 <- 02 03 1C 00 01 09 CB 0B 06 C0 00 01 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 B9 8A  [CRC OK]


"Запрос номера самого старого события"
2:36:02 -> 02 03 B4 51 00 01 F2 18
2:36:02 <- 02 03 02 00 01 3D 84  [CRC OK]
"Запрос события #1"
2:36:44 -> 02 03 B4 B8 00 01 23 EC
2:36:45 <- 02 03 02 00 01 3D 84  [CRC OK]

"""