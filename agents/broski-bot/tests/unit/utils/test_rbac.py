import pytest
from src.utils.rbac import RBACManager, UserRole, Permission, RBACError


def test_rbac_admin_access():
    """Test that Admin has all permissions."""
    RBACManager.check_access(UserRole.ADMIN, Permission.QUEST_CREATE)
    RBACManager.check_access(UserRole.ADMIN, Permission.AGENT_ORCHESTRATE)
    RBACManager.check_access(UserRole.ADMIN, Permission.SYSTEM_CONFIG)
    assert RBACManager.has_permission(UserRole.ADMIN, Permission.QUEST_DELETE) is True


def test_rbac_moderator_access():
    """Test Moderator permissions."""
    RBACManager.check_access(UserRole.MODERATOR, Permission.QUEST_UPDATE)
    RBACManager.check_access(UserRole.MODERATOR, Permission.AGENT_ORCHESTRATE)
    
    # Moderator should NOT have system config
    with pytest.raises(RBACError):
        RBACManager.check_access(UserRole.MODERATOR, Permission.SYSTEM_CONFIG)
    
    assert RBACManager.has_permission(UserRole.MODERATOR, Permission.QUEST_CREATE) is False


def test_rbac_user_access():
    """Test that standard User has no restricted permissions."""
    with pytest.raises(RBACError):
        RBACManager.check_access(UserRole.USER, Permission.QUEST_UPDATE)
    
    assert RBACManager.has_permission(UserRole.USER, Permission.AGENT_ORCHESTRATE) is False


def test_rbac_bot_access():
    """Test Bot permissions."""
    RBACManager.check_access(UserRole.BOT, Permission.AGENT_ORCHESTRATE)
    
    with pytest.raises(RBACError):
        RBACManager.check_access(UserRole.BOT, Permission.QUEST_CREATE)
