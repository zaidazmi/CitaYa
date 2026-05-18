from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocType(str, Enum):
    DNI = "dni"
    NIE = "nie"
    PASSPORT = "passport"


class OperationType(str, Enum):
    # --- Police procedures (Trámites Policía Nacional) ---
    ASIGNACION_NIE = "4031"
    ASIGNACION_NIE_NO_RESIDENTE = "4130"
    ASILO_INFORMACION = "4089"
    ASILO_PRIMERA_CITA = "4104"
    AUTORIZACION_DE_REGRESO = "20"
    BREXIT = "4094"
    CARTA_INVITACION = "4037"
    CEDULA_DE_INSCRIPCION = "4099"
    CERTIFICADO_RESIDENTE = "4032"
    CERTIFICADOS_CONCORDANCIA = "4118"
    CERTIFICADOS_NIE = "4096"
    CERTIFICADOS_NIE_NO_COMUN = "4079"
    CERTIFICADOS_RESIDENCIA = "4049"
    CERTIFICADOS_RESIDENCIA_CONCORDANCIA = "4131"
    CERTIFICADOS_UE = "4038"
    DECLARACION_ENTRADA = "4084"
    DOCUMENTOS_ASILO = "4067"
    EXPEDICION_TARJETAS_DGGM = "4047"
    PRORROGA_ESTANCIA = "4124"
    PRORROGA_ESTANCIA_CON_VISADO = "4090"
    PRORROGA_ESTANCIA_SIN_VISADO = "4091"
    PROTECCION_TEMPORAL_UCRANIA = "4111"
    RECOGIDA_CERTIFICADO_REGRESO = "4087"
    RECOGIDA_DE_TARJETA = "4036"
    RECOGIDA_TARJETA_ROJA = "4086"
    RECOGIDA_TIE_DGGM = "4088"
    SOLICITUD_APATRIDA = "4103"
    SOLICITUD_ASILO = "4078"
    TARJETA_ROJA = "4082"
    TARJETA_UCRANIA = "4112"
    TITULOS_DE_VIAJE = "4092"
    TOMA_HUELLAS = "4010"
    INFORMACION_COMISARIA = "4097"

    # --- Extranjería procedures (Oficinas de Extranjería) ---
    ARRAIGO_RESIDENCIA = "4012"
    AUTORIZACION_REGRESO_EXTRANJERIA = "4058"
    AUTORIZACIONES_TRABAJO = "11"
    CIRCUNSTANCIAS_EXCEPCIONALES = "10"
    DOCUMENTACION_BRITANICOS = "4069"
    ESTANCIA_ESTUDIOS = "4016"
    FAMILIAR_CIUDADANO_ESPAÑOL = "4114"
    FAMILIAR_ESPAÑOL_RESIDENCIA = "4128"
    INFORMACION = "4009"
    MENORES_NACIDOS_ESPAÑA = "15"
    MENORES_NO_NACIDOS_ESPAÑA = "28"
    MODIFICACION_SITUACIONES = "4030"
    REAGRUPACION_FAMILIAR = "3"
    REAGRUPACION_MENORES_ESTUDIOS = "4113"
    RECUPERACION_LARGA_DURACION = "4034"
    REGISTRO = "4081"
    RENOVACIONES_PRORROGAS = "4059"
    RENOVACIONES_RESIDENCIA = "4023"
    TARJETAS_FAMILIAR_UE = "7"


class Office(str, Enum):
    BADALONA = "18"
    BARCELONA = "16"
    BARCELONA_MALLORCA = "14"
    CASTELLDEFELS = "19"
    CERDANYOLA = "20"
    CORNELLA = "21"
    ELPRAT = "23"
    GRANOLLERS = "28"
    HOSPITALET = "17"
    IGUALADA = "26"
    MANRESA = "38"
    MATARO = "27"
    MONTCADA = "31"
    RIPOLLET = "32"
    RUBI = "29"
    SABADELL = "30"
    SANTACOLOMA = "35"
    SANTADRIA = "33"
    SANTBOI = "24"
    SANTCUGAT = "34"
    SANTFELIU = "22"
    TERRASSA = "36"
    VIC = "37"
    VILADECANS = "25"
    VILAFRANCA = "46"
    VILANOVA = "39"
    OUE_SANTA_CRUZ = "1"
    PLAYA_AMERICAS = "2"
    PUERTO_CRUZ = "3"


class Province(str, Enum):
    A_CORUÑA = "15"
    ALBACETE = "2"
    ALICANTE = "3"
    ALMERÍA = "4"
    ARABA = "1"
    ASTURIAS = "33"
    ÁVILA = "5"
    BADAJOZ = "6"
    BARCELONA = "8"
    BIZKAIA = "48"
    BURGOS = "9"
    CÁCERES = "10"
    CÁDIZ = "11"
    CANTABRIA = "39"
    CASTELLÓN = "12"
    CEUTA = "51"
    CIUDAD_REAL = "13"
    CÓRDOBA = "14"
    CUENCA = "16"
    GIPUZKOA = "20"
    GIRONA = "17"
    GRANADA = "18"
    GUADALAJARA = "19"
    HUELVA = "21"
    HUESCA = "22"
    ILLES_BALEARS = "7"
    JAÉN = "23"
    LA_RIOJA = "26"
    LAS_PALMAS = "35"
    LEÓN = "24"
    LLEIDA = "25"
    LUGO = "27"
    MADRID = "28"
    MÁLAGA = "29"
    MELILLA = "52"
    MURCIA = "30"
    NAVARRA = "31"
    ORENSE = "32"
    PALENCIA = "34"
    PONTEVEDRA = "36"
    SALAMANCA = "37"
    S_CRUZ_TENERIFE = "38"
    SEGOVIA = "40"
    SEVILLA = "41"
    SORIA = "42"
    TARRAGONA = "43"
    TERUEL = "44"
    TOLEDO = "45"
    VALENCIA = "46"
    VALLADOLID = "47"
    ZAMORA = "49"
    ZARAGOZA = "50"


@dataclass
class CustomerProfile:
    name: str
    doc_type: DocType
    doc_value: str
    phone: str
    email: str
    province: Province = Province.BARCELONA
    operation_code: OperationType = OperationType.TOMA_HUELLAS
    country: str = ""
    year_of_birth: Optional[str] = None
    offices: Optional[list] = field(default_factory=list)
    except_offices: Optional[list] = field(default_factory=list)

    chrome_path: Optional[str] = None
    capsolver_api_key: Optional[str] = None
    auto_captcha: bool = True
    auto_office: bool = True
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    min_time: Optional[str] = None
    max_time: Optional[str] = None
    save_screenshots: bool = False
    sms_webhook_token: Optional[str] = None
    wait_exact_time: Optional[list] = None

    booked: bool = False

    def __post_init__(self):
        if not self.country:
            raise ValueError("country is required (e.g. 'INDIA', 'MARRUECOS')")
        if self.operation_code == OperationType.RECOGIDA_DE_TARJETA:
            assert len(self.offices) == 1, "Indicate the office where you need to pick up the card"
