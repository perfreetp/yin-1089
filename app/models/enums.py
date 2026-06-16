from enum import Enum


class HospitalZone(str, Enum):
    MAIN = "main"
    EAST = "east"
    WEST = "west"
    SOUTH = "south"
    NORTH = "north"


class PatientType(str, Enum):
    OSA = "osa"
    INSOMNIA = "insomnia"
    RESTLESS_LEG = "restless_leg"
    NARCOLEPSY = "narcolepsy"
    CIRCADIAN = "circadian"
    PARASOMNIA = "parasomnia"
    OTHER = "other"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REASSIGNED = "reassigned"


class QueueStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    REASSIGNED = "reassigned"


class ContactChannel(str, Enum):
    PHONE = "phone"
    SMS = "sms"
    WECHAT = "wechat"
    APP = "app"
    IN_PERSON = "in_person"


class ContactResult(str, Enum):
    SUCCESS = "success"
    NO_ANSWER = "no_answer"
    PATIENT_BUSY = "patient_busy"
    WRONG_NUMBER = "wrong_number"
    REFUSED = "refused"
    DISCONNECTED = "disconnected"
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    CALL_BACK_LATER = "call_back_later"


class AlertLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"


class AlertType(str, Enum):
    OVERDUE = "overdue"
    ESCALATION = "escalation"
    REASSIGN = "reassign"
    HIGH_PRIORITY = "high_priority"
    SCORE_ABNORMAL = "score_abnormal"


class PSQIComponent(str, Enum):
    SLEEP_QUALITY = "sleep_quality"
    SLEEP_LATENCY = "sleep_latency"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_EFFICIENCY = "sleep_efficiency"
    SLEEP_DISTURBANCES = "sleep_disturbances"
    USE_OF_MEDICATION = "use_of_medication"
    DAYTIME_DYSFUNCTION = "daytime_dysfunction"


class AssignmentStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCE = "load_balance"
    SKILL_BASED = "skill_based"
    PRIORITY = "priority"


class ScoreChangeType(str, Enum):
    IMPROVED = "improved"
    STABLE = "stable"
    WORSENED = "worsened"
    SIGNIFICANT_IMPROVEMENT = "significant_improvement"
    SIGNIFICANT_WORSENING = "significant_worsening"
