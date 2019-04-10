from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Date, Time, SmallInteger, Numeric
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('postgres://serp:serpserpserpserpserp@rpi.zvez.ga:5432/postgres', echo=True)
Base = declarative_base()


########################################################################
class Zabtest(Base):
    """"""
    __tablename__ = "zabtest"

    IdentificationNumber = Column(Integer, primary_key=True)
    MeterId = Column(String)
    Date = Column(Date)
    Year = Column(SmallInteger)
    Month = Column(SmallInteger)
    Day = Column(SmallInteger)
    Time = Column(Time)
    Hour = Column(SmallInteger)
    Minute = Column(SmallInteger)
    Second = Column(SmallInteger)
    WirkleistungP1 = Column(Numeric)
    WirkleistungP2 = Column(Numeric)
    WirkleistungP3 = Column(Numeric)
    WirkleistungGesamt = Column(Numeric)
    BlindleistungP1 = Column(Numeric)
    BlindleistungP2 = Column(Numeric)
    BlindleistungP3 = Column(Numeric)
    BlindleistungGesamt = Column(Numeric)
    ScheinleistungP1 = Column(Numeric)
    ScheinleistungP2 = Column(Numeric)
    ScheinleistungP3 = Column(Numeric)
    ScheinleistungGesamt = Column(Numeric)
    StromP1 = Column(Numeric)
    StromP2 = Column(Numeric)
    StromP3 = Column(Numeric)
    StromNeutralleiter = Column(Numeric)
    SpannungP1 = Column(Numeric)
    SpannungP2 = Column(Numeric)
    SpannungP3 = Column(Numeric)
    LeistungsfaktorP1 = Column(Numeric)
    LeistungsfaktorP2 = Column(Numeric)
    LeistungsfaktorP3 = Column(Numeric)
    LeistungsfaktorGesamt = Column(Numeric)
    Frequenz = Column(Numeric)
    EinAusgangsSteuerSignal = Column(Numeric)
    InternalSteuerSignal = Column(String)               # Correct?
    Betriebszustand = Column(String)                    # Correct?
    PhasenAusfalleCounterGesamt = Column(Numeric)
    PhasenAusfalleCounterP1 = Column(Numeric)
    PhasenAusfalleCounterP2 = Column(Numeric)
    PhasenAusfalleCounterP3 = Column(Numeric)
    DCFLastSync = Column(Numeric)
    PhaseInformation = Column(Numeric)
    InstallationsKontrol = Column(Numeric)

    # ----------------------------------------------------------------------
    def __init__(self, IdentificationNumber, MeterId, Date, Year, Month, Day, Time, Hour, Minute, Second,
                 WirkleistungP1, WirkleistungP2, WirkleistungP3, WirkleistungGesamt, BlindleistungP1,
                 BlindleistungP2, BlindleistungP3, BlindleistungGesamt, ScheinleistungP1,
                 ScheinleistungP2, ScheinleistungP3, ScheinleistungGesamt, StromP1, StromP2, StromP3,
                 StromNeutralleiter, SpannungP1, SpannungP2, SpannungP3, LeistungsfaktorP1, LeistungsfaktorP2,
                 LeistungsfaktorP3, LeistungsfaktorGesamt, Frequenz, EinAusgangsSteuerSignal, InternalSteuerSignal,
                 Betriebszustand, PhasenAusfalleCounterGesamt, PhasenAusfalleCounterP1, PhasenAusfalleCounterP2,
                 PhasenAusfalleCounterP3, DCFLastSync, PhaseInformation, InstallationsKontrol
                 ):

        self.IdentificationNumber = IdentificationNumber
        self.MeterId = MeterId
        self.Date = Date
        self.Year = Year
        self.Month = Month
        self.Day = Day
        self.Time = Time
        self.Hour = Hour
        self.Minute = Minute
        self.Second = Second
        self.WirkleistungP1 = WirkleistungP1
        self.WirkleistungP2 = WirkleistungP2
        self.WirkleistungP3 = WirkleistungP3
        self.WirkleistungGesamt = WirkleistungGesamt
        self.BlindleistungP1 = BlindleistungP1
        self.BlindleistungP2 = BlindleistungP2
        self.BlindleistungP3 = BlindleistungP3
        self.BlindleistungGesamt = BlindleistungGesamt
        self.ScheinleistungP1 = ScheinleistungP1
        self.ScheinleistungP2 = ScheinleistungP2
        self.ScheinleistungP3 = ScheinleistungP3
        self.ScheinleistungGesamt = ScheinleistungGesamt
        self.StromP1 = StromP1
        self.StromP2 = StromP2
        self.StromP3 = StromP3
        self.StromNeutralleiter = StromNeutralleiter
        self.SpannungP1 = SpannungP1
        self.SpannungP2 = SpannungP2
        self.SpannungP3 = SpannungP3
        self.LeistungsfaktorP1 = LeistungsfaktorP1
        self.LeistungsfaktorP2 = LeistungsfaktorP2
        self.LeistungsfaktorP3 = LeistungsfaktorP3
        self.LeistungsfaktorGesamt = LeistungsfaktorGesamt
        self.Frequenz = Frequenz
        self.EinAusgangsSteuerSignal = EinAusgangsSteuerSignal
        self.InternalSteuerSignal = InternalSteuerSignal
        self.Betriebszustand = Betriebszustand
        self.PhasenAusfalleCounterGesamt = PhasenAusfalleCounterGesamt
        self.PhasenAusfalleCounterP1 = PhasenAusfalleCounterP1
        self.PhasenAusfalleCounterP2 = PhasenAusfalleCounterP2
        self.PhasenAusfalleCounterP3 = PhasenAusfalleCounterP3
        self.DCFLastSync = DCFLastSync
        self.PhaseInformation = PhaseInformation
        self.InstallationsKontrol = InstallationsKontrol


# create tables
Base.metadata.create_all(engine)




