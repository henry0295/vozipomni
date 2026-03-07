"""
Custom exceptions for VoziPOmni
"""


# ============= Base Exceptions =============

class VoziPOmniException(Exception):
    """Base exception for all VoziPOmni errors"""
    default_message = "An error occurred"
    
    def __init__(self, message=None, **kwargs):
        self.message = message or self.default_message
        self.extra_data = kwargs
        super().__init__(self.message)


# ============= Campaign Exceptions =============

class CampaignError(VoziPOmniException):
    """Base exception for campaign-related errors"""
    pass


class CampaignAlreadyActiveError(CampaignError):
    default_message = "Campaign is already active"


class CampaignNotFoundError(CampaignError):
    default_message = "Campaign not found"


class NoContactsError(CampaignError):
    default_message = "Campaign has no contacts to process"


class InvalidCampaignStateError(CampaignError):
    default_message = "Campaign is in an invalid state for this operation"


# ============= Agent Exceptions =============

class AgentError(VoziPOmniException):
    """Base exception for agent-related errors"""
    pass


class AgentNotAvailableError(AgentError):
    default_message = "Agent is not available"


class AgentNotFoundError(AgentError):
    default_message = "Agent not found"


class AgentAlreadyLoggedInError(AgentError):
    default_message = "Agent is already logged in"


# ============= Telephony Exceptions =============

class TelephonyError(VoziPOmniException):
    """Base exception for telephony-related errors"""
    pass


class AMIConnectionError(TelephonyError):
    default_message = "Failed to connect to Asterisk AMI"


class AMICommandError(TelephonyError):
    default_message = "AMI command failed"


class InvalidExtensionError(TelephonyError):
    default_message = "Invalid extension"


class TrunkNotFoundError(TelephonyError):
    default_message = "SIP trunk not found"


class TrunkRegistrationError(TelephonyError):
    default_message = "Failed to register SIP trunk"


# ============= Contact Exceptions =============

class ContactError(VoziPOmniException):
    """Base exception for contact-related errors"""
    pass


class InvalidContactError(ContactError):
    default_message = "Invalid contact data"


class ContactNotFoundError(ContactError):
    default_message = "Contact not found"


class DuplicateContactError(ContactError):
    default_message = "Contact already exists"


# ============= Call Exceptions =============

class CallError(VoziPOmniException):
    """Base exception for call-related errors"""
    pass


class CallOriginationError(CallError):
    default_message = "Failed to originate call"


class CallNotFoundError(CallError):
    default_message = "Call not found"


class CallAlreadyActiveError(CallError):
    default_message = "Call is already active"


# ============= Queue Exceptions =============

class QueueError(VoziPOmniException):
    """Base exception for queue-related errors"""
    pass


class QueueNotFoundError(QueueError):
    default_message = "Queue not found"


class QueueFullError(QueueError):
    default_message = "Queue is full"


# ============= Configuration Exceptions =============

class ConfigurationError(VoziPOmniException):
    """Base exception for configuration-related errors"""
    pass


class InvalidConfigurationError(ConfigurationError):
    default_message = "Invalid configuration"


class MissingConfigurationError(ConfigurationError):
    default_message = "Required configuration is missing"


# ============= External Service Exceptions =============

class ExternalServiceError(VoziPOmniException):
    """Base exception for external service errors"""
    pass


class RedisConnectionError(ExternalServiceError):
    default_message = "Failed to connect to Redis"


class DatabaseConnectionError(ExternalServiceError):
    default_message = "Failed to connect to database"


# ============= Validation Exceptions =============

class ValidationError(VoziPOmniException):
    """Base exception for validation errors"""
    default_message = "Validation failed"


class InvalidPhoneNumberError(ValidationError):
    default_message = "Invalid phone number format"


class InvalidDateRangeError(ValidationError):
    default_message = "Invalid date range"


# ============= Permission Exceptions =============

class PermissionError(VoziPOmniException):
    """Base exception for permission errors"""
    default_message = "Permission denied"


class InsufficientPermissionsError(PermissionError):
    default_message = "Insufficient permissions for this operation"
