from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    FINANCE = "finance"
    PURCHASER = "purchaser"
    TESTER = "tester"
    VIEWER = "viewer"


class SupplierType(StrEnum):
    ACCOUNT = "account"
    SERVER = "server"
    PROXY = "proxy"
    PHONE_CODE = "phone_code"
    EMAIL = "email"
    SHIELD = "shield"
    DOMAIN = "domain"
    OTHER = "other"


class SupplierStatus(StrEnum):
    NORMAL = "normal"
    OBSERVING = "observing"
    PAUSED = "paused"
    BLOCKED = "blocked"


class PurchaseType(StrEnum):
    ACCOUNT = "account"
    SERVER = "server"
    PROXY = "proxy"
    DOMAIN = "domain"
    SOFTWARE = "software"
    OTHER = "other"


class CostStatus(StrEnum):
    TESTING = "testing"
    VALID = "valid"
    PARTIAL_VALID = "partial_valid"
    INVALID = "invalid"
    REFUNDED = "refunded"
    SCRAPPED = "scrapped"


class AccountStatus(StrEnum):
    PENDING_TEST = "pending_test"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RISK_CONTROL = "risk_control"
    BANNED = "banned"
    REFUNDED = "refunded"
    ABANDONED = "abandoned"


class EvaluationConclusion(StrEnum):
    RECOMMENDED = "recommended"
    CAUTIOUS = "cautious"
    NOT_RECOMMENDED = "not_recommended"
    BLOCKED = "blocked"


class RevenueSource(StrEnum):
    RECHARGE = "recharge"
    SUBSCRIPTION = "subscription"
    MANUAL_PAYMENT = "manual_payment"
    OTHER = "other"


class CostType(StrEnum):
    ACCOUNT = "account"
    SERVER = "server"
    PROXY = "proxy"
    DOMAIN = "domain"
    FEE = "fee"
    TEST_LOSS = "test_loss"
    REFUND_LOSS = "refund_loss"
    SOFTWARE = "software"
    LABOR = "labor"
    OTHER = "other"
