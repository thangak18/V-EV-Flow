from enum import StrEnum


class Scenario(StrEnum):
    NORMAL = "normal"
    HOLIDAY_30_4 = "holiday_30_4"
    TET = "tet"


class DataType(StrEnum):
    MOCK = "mock"
    SIMULATED = "simulated"
    REAL = "real"
    MIXED = "mixed"


class Strategy(StrEnum):
    NEAREST = "nearest"
    CURRENTLY_AVAILABLE = "currently_available"
    AI_ALLOCATION = "ai_allocation"
