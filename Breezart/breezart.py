import socket
import syslog
import time


class Vent:

    program_name = 'Breezart-python'
    version = 0.1
    BUFFER_SIZE = 128

    def __init__(self, **kwargs):
        self.ip_address = kwargs.get('ip')
        self.port = kwargs.get('port') or 1560
        self.password = kwargs.get('password') or None
        self.query_interval = kwargs.get('interval') or 10
        self.debug = kwargs.get('debug') or False         # reserved for future use
        self.sock = self.connect()

        self.status = dict()

    @staticmethod
    def log(severity, message):
        message = f'{Vent.program_name} {Vent.version}: {message}'
        #  print(message)
        syslog.syslog(severity, message)

    def connect(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((self.ip_address, self.port))
            self.log(syslog.LOG_INFO, f'Connected to {self.ip_address}:{self.port}')
            return s
        except Exception as e:
            self.log(syslog.LOG_EMERG, f'Unable to connect to {self.ip_address}:{self.port} - {e}')
            raise e

    def send_request(self, request):
        try:
            self.log(syslog.LOG_DEBUG, f'Sending {request}')
            self.sock.send(request.encode())
            data = self.sock.recv(Vent.BUFFER_SIZE).decode()
            self.log(syslog.LOG_DEBUG, f'Received {data}')
            return data
        except socket.error as e:
            self.log(syslog.LOG_ERR, 'Network error: {0}'.format(e))
            raise e

    def split_data(self, data, array_len=0):
        data_array = data.split('_')
        if len(data_array) != array_len:
            self.log(syslog.LOG_ERR, f'{data_array} len = {len(data_array)} != expected len {array_len}')
            raise
        return data_array

    def get_vent_status(self):
        """
        Запрос: VSt07_Pass
        Ответ: VSt07_bitState_bitMode_bitTempr_bitHumid_bitSpeed_bitMisc_bitTime_bitDate_bitYear_Msg
        """
        self.status['Temperature'] = dict()
        self.status['Humidity'] = dict()
        self.status['Speed'] = dict()
        self.status['DateTime'] = dict()
        self.status['Scene'] = dict()
        self.status['Settings'] = dict()
        self.status['State'] = dict()
        self.status['Sensors'] = dict()

        data = self.send_request('{0}_{1:X}'.format('VSt07', self.password))
        # "b'VSt07_1841_2005_1616_0_ff33_2280_1028_405_1407_\\xd0\\xa0\\xd0\\xb0\\xd0\\xb1\\xd0\\xbe\\xd1\\x82\\xd0\\xb0   '"
        if data:
            data_array = self.split_data(data, 11)
        else:
            self.log(syslog.LOG_ERR, 'Can\'t connect to vent')
            raise

        """
        bitState:
            Bit 0 – PwrBtnState – состояние кнопки питания (вкл / выкл).
            Bit 1 – IsWarnErr – есть предупреждение. В Msg содержится текст сообщения.
            Bit 2 – IsFatalErr – есть критическая ошибка. В Msg содержится текст сообщения.
            Bit 3 – DangerOverheat – угроза перегрева калорифера (для установки с электрокалорифером).
            Bit 4 – AutoOff – установка автоматически выключена на 5 минут для автоподстройки нуля
            датчика давления.
            Bit 5 – ChangeFilter – предупреждение о необходимости замены фильтра.
            Bit 8-6 – ModeSet – установленный режим работы.
                1 – Обогрев
                2 – Охлаждение
                3 – Авто
                4 – Отключено (вентиляция без обогрева и охлаждения)
            Bit 9 – HumidMode – селектор Увлажнитель активен (стоит галочка).
            Bit 10 – SpeedIsDown – скорость вентилятора автоматически снижена.
            Bit 11 – FuncRestart – включена функция Рестарт при сбое питания.
            Bit 12 – FuncComfort – включена функция Комфорт.
            Bit 13 – HumidAuto – увлажнение включено (в режиме Авто).
            Bit 14 – ScenBlock – сценарии заблокированы режимом ДУ.
            Bit 15 – BtnPwrBlock – кнопка питания заблокирована режимом ДУ.
        """
        # self.log(syslog.LOG_DEBUG, f'Data array = {data_array}')
        self.status['State']['Power'] = 1 if int(data_array[1], 16) & 0x01 else 0
        self.status['State']['Warning'] = 1 if int(data_array[1], 16) & 0x02 else 0
        self.status['State']['Critical'] = 1 if int(data_array[1], 16) & 0x04 else 0
        self.status['State']['Overheat'] = 1 if int(data_array[1], 16) & 0x08 else 0
        self.status['State']['AutoOff'] = 1 if int(data_array[1], 16) & 0x10 else 0
        self.status['State']['ChangeFilter'] = 1 if int(data_array[1], 16) & 0x20 else 0
        self.status['Settings']['Mode'] = (int(data_array[1], 16) & 0x1C0) >> 6              # 1, 2, 3, 4
        self.status['Humidity']['Mode'] = 1 if int(data_array[1], 16) & 0x200 else 0
        self.status['Speed']['SpeedIsDown'] = 1 if int(data_array[1], 16) & 0x400 else 0
        self.status['State']['AutoRestart'] = 1 if int(data_array[1], 16) & 0x800 else 0
        self.status['State']['Comfort'] = 1 if int(data_array[1], 16) & 0x1000 else 0
        self.status['Humidity']['Auto'] = 1 if int(data_array[1], 16) & 0x2000 else 0
        self.status['Scene']['Block'] = 1 if int(data_array[1], 16) & 0x4000 else 0
        self.status['State']['PowerBlock'] = 1 if int(data_array[1], 16) & 0x8000 else 0
        """
        bitMode:
        Bit 1, 0 – UnitState – состояние установки:
            0 – Выключено.
            1 – Включено.
            2 – Выключение (переходный процесс перед отключением).
            3 – Включение (переходный процесс перед включением).
        Bit 2 – ScenAllow – разрешена работа по сценариям.
        Bit 5-3 – Mode – режим работы:
            0 – Обогрев
            1 – Охлаждение
            2 – Авто-Обогрев
            3 – Авто-Охлаждение
            4 – Отключено (вентиляция без обогрева и охлаждения)
            5 – Нет (установка выключена)
        Bit 9-6 – NumActiveScen – номер активного сценария (от 1 до 8), 0 если нет.
        Bit 12-10 – WhoActivateScen – кто запустил (активировал) сценарий:
            0 – активного сценария нет и запущен не будет
            1 – таймер1
            2 – таймер2
            3 – пользователь вручную
            4 – сценарий будет запущен позднее (сейчас активного сценария нет)
        Bit 13-15 – NumIcoHF – номер иконки Влажность / фильтр.
        """
        unitstate = {0: 'Выключено', 1: 'Включено', 2: 'Выключение', 3: 'Включение'}
        # self.status['State']['Unit'] = unitstate[(int(data_array[2], 16) & 0x03)]
        self.status['State']['Unit'] = (int(data_array[2], 16) & 0x03)
        self.status['Scene']['SceneState'] = 1 if int(data_array[2], 16) & 0x04 else 0
        unitmode = {0: 'Обогрев', 1: 'Охлаждение', 2: 'Авто-Обогрев', 3: 'Авто-Охлаждение', 4: 'Вентиляция',
                    5: 'Выключено'}
        # self.status['State']['Mode'] = unitmode[(int(data_array[2], 16) & 0x38) >> 3]
        self.status['State']['Mode'] = (int(data_array[2], 16) & 0x38) >> 3
        self.status['Scene']['Number'] = (int(data_array[2], 16) & 0x3C0) >> 6
        self.status['Scene']['WhoActivate'] = (int(data_array[2], 16) & 0x1C00) >> 10
        self.status['State']['IconHF'] = (int(data_array[2], 16) & 0xE000) >> 13
        """
        bitTempr:
            Bit 7-0 – Tempr signed char – текущая температура, °С. Диапазон значений от -50 до 70.
            Bit 15-8 – TemperTarget – заданная температура, °С. Диапазон значений от 0 до 50.
        """
        self.status['Temperature']['Current'] = int(data_array[3], 16) & 0xFF
        self.status['Temperature']['Target'] = (int(data_array[3], 16) & 0xFF00) >> 8
        """
        bitHumid:
        Bit 7-0 – Humid – текущая влажность (при наличии увлажнители или датчика влажности). Диапазон
        значений от 0 до 100. При отсутствии данных значение равно 255.
        Bit 15-8 – HumidTarget – заданная влажность. Диапазон значений от 0 до 100.
        """
        self.status['Humidity']['Current'] = int(data_array[4], 16) & 0xFF
        self.status['Humidity']['Target'] = (int(data_array[4], 16) & 0xFF00) >> 8
        """
        bitSpeed:
        Bit 3-0 – Speed – текущая скорость вентилятора, диапазон от 0 до 10.
        Bit 7-4 – SpeedTarget – заданная скорость вентилятора, диапазон от 0 до 10.
        Bit 15-8 – SpeedFact – фактическая скорость вентилятора 0 – 100%. Если не определено, то 255.
        """
        self.status['Speed']['Current'] = int(data_array[5], 16) & 0x0F
        self.status['Speed']['Target'] = (int(data_array[5], 16) & 0xF0) >> 4
        self.status['Speed']['Actual'] = (int(data_array[5], 16) & 0xFF00) >> 8
        """
        bitMisc:
            Bit 3-0 – TempMin – минимально допустимая заданная температура (от 5 до 15). Может изменяться
            в зависимости от режима работы вентустановки
            Bit 5, 4 – ColorMsg – иконка сообщения Msg для различных состояний установки:
                0 – Нормальная работа (серый)
                1 – Предупреждение (желтый)
                2 – Ошибка (красный)
            Bit 7, 6 – ColorInd – цвет индикатора на кнопке питания для различных состояний установки:
                0 – Выключено (серый)
                1 – Переходный процесс включения / отключения (желтый)
                2 – Включено (зеленый)
            Bit 15-8 – FilterDust – загрязненность фильтра 0 - 250%, если не определено, то 255.
        """
        self.status['Temperature']['Minimum'] = int(data_array[6], 16) & 0x0F
        self.status['State']['ColorMsg'] = (int(data_array[6], 16) & 0x30) >> 4
        self.status['State']['ColorInd'] = (int(data_array[6], 16) & 0xC0) >> 6
        self.status['State']['FilterDust'] = (int(data_array[6], 16) & 0xFF00) >> 8
        """
        bitTime:
            Bit 7-0 – nn – минуты (от 00 до 59)
            Bit 15-8 – hh – часы (от 00 до 23)
        """
        self.status['DateTime']['Time'] = '{0:02d}:{1:02d}'.format((int(data_array[7], 16) & 0xFF00) >> 8,
                                                              int(data_array[7], 16) & 0xFF)
        """
        bitDate:
            Bit 7-0 – dd – день месяца (от 1 до 31)
            Bit 15-8 – mm – месяц (от 1 до 12)
        bitYear:
            Bit 7-0 – dow – день недели (от 1-Пн до 7-Вс)
            Bit 15-8 – yy – год (от 0 до 99, последние две цифры года).
        """
        self.status['DateTime']['Date'] = '{0:02d}-{1:02d}-20{2:02d}'.format(int(data_array[8], 16) & 0xFF,
                                                                        (int(data_array[8], 16) & 0xFF00) >> 8,
                                                                        (int(data_array[9], 16) & 0xFF00) >> 8)
        """
        Msg - текстовое сообщение о состоянии установки длиной от 5 до 70 символов.
        """
        self.status['Msg'] = data_array[10].strip()

    def run(self):
        """
        Runs queries in a loop, evey self.query_interval, prints result in the screen
        :return: None
        """
        while True:
            self.get_vent_status()
            print(self.status)
            time.sleep(self.query_interval)


if __name__ == '__main__':
    data = {'ip': '192.168.1.11', 'password': 21579}
    my_vent = Vent(**data)
    my_vent.run()