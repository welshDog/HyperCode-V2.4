"""
Role-Based Access Control (RBAC) utility.
Defines roles and permissions for secure orchestration endpoints.
"""
from enum import Enum
from typing import Dict, Set

from src.config.logging import get_logger
from src.core.exceptions import BroskiBotException

logger = get_logger(__name__)


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    BOT = "bot"


class Permission(str, Enum):
    """Permissions for RBAC."""
    QUEST_CREATE = "quest:create"
    QUEST_UPDATE = "quest:update"
    QUEST_DELETE = "quest:delete"
    AGENT_ORCHESTRATE = "agent:orchestrate"
    SYSTEM_CONFIG = "system:config"


class RBACError(BroskiBotException):
    """Raised when access is denied by RBAC."""
    pass


class RBACManager:
    """
    Manages roles and permissions.
    Securely checks access for orchestration endpoints.
    """
    
    # Role to Permissions mapping
    ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
        UserRole.ADMIN: {
            Permission.QUEST_CREATE,
            Permission.QUEST_UPDATE,
            Permission.QUEST_DELETE,
            Permission.AGENT_ORCHESTRATE,
            Permission.SYSTEM_CONFIG,
        },
        UserRole.MODERATOR: {
            Permission.QUEST_UPDATE,
            Permission.AGENT_ORCHESTRATE,
        },
        UserRole.USER: set(),
        UserRole.BOT: {
            Permission.AGENT_ORCHESTRATE,
        },
    }
    
    @classmethod
    def check_access(cls, user_role: UserRole, required_permission: Permission) -> None:
        """
        Check if a user role has the required permission.
        
        Args:
            user_role: Role of the user
            required_permission: Permission required for the operation
            
        Raises:
            RBACError: If access is denied
        """
        permissions = cls.ROLE_PERMISSIONS.get(user_role, set())
        if required_permission not in permissions:
            logger.warning(
                "Access denied by RBAC",
                role=user_role,
                required=required_permission,
            )
            raise RBACError(
                f"Role {user_role} does not have required permission {required_permission}"
            )
            
    @classmethod
    def has_permission(cls, user_role: UserRole, required_permission: Permission) -> bool:
        """Check if role has permission without raising exception."""
        permissions = cls.ROLE_PERMISSIONS.get(user_role, set())
        return required_permission in permissions
