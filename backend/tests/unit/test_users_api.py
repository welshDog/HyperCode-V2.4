from app.core.config import settings
from app.models.models import User

def test_create_user(client, db):
    """
    Test creating a user via the /users endpoint.
    Verifies the response and the database state.
    """
    user_data = {
        "email": "test@example.com",
        "password": "password12345",
        "full_name": "Test User",
        "role": "developer"
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        json=user_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "id" in data
    assert data["full_name"] == user_data["full_name"]
    
    # Verify in DB
    user = db.query(User).filter(User.email == user_data["email"]).first()
    assert user is not None
    assert user.email == user_data["email"]
    assert user.full_name == user_data["full_name"]

def test_get_user_me_unauthorized(client):
    """
    Test getting current user without authentication token.
    Should fail with 401 Unauthorized.
    """
    response = client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 401
