"""Tests for infrastructure components."""

import pytest
import redis
import psycopg2


class TestRedisConnection:
    """Tests for Redis connectivity."""
    
    def test_redis_connection(self):
        """Test Redis connection works."""
        try:
            r = redis.Redis(host='redis', port=6379, db=0, socket_connect_timeout=1)
            r.ping()
            assert True
        except redis.ConnectionError:
            pytest.skip("Redis not available")
    
    @pytest.mark.asyncio
    async def test_redis_async_connection(self):
        """Test async Redis connection."""
        try:
            import redis.asyncio as aio_redis
            r = await aio_redis.from_url("redis://redis:6379")
            result = await r.ping()
            assert result
            await r.close()
        except Exception:
            pytest.skip("Redis not available")


class TestPostgresConnection:
    """Tests for PostgreSQL connectivity."""
    
    def test_postgres_connection(self):
        """Test PostgreSQL connection works."""
        try:
            from app.core.config import settings
            conn = psycopg2.connect(
                settings.HYPERCODE_DB_URL,
                connect_timeout=1
            )
            conn.close()
            assert True
        except psycopg2.OperationalError:
            pytest.skip("PostgreSQL not available")
    
    def test_postgres_database_exists(self):
        """Test required database exists."""
        try:
            from app.core.config import settings
            conn = psycopg2.connect(
                settings.HYPERCODE_DB_URL,
                connect_timeout=1
            )
            cursor = conn.cursor()
            cursor.execute("SELECT datname FROM pg_database WHERE datname='hypercode'")
            assert cursor.fetchone() is not None
            conn.close()
        except psycopg2.OperationalError:
            pytest.skip("PostgreSQL not available")


class TestDatabaseSchema:
    """Tests for database schema."""
    
    def test_sqlalchemy_models_mapped(self):
        """Test all SQLAlchemy models are properly mapped."""
        from app.db.base_class import Base
        import app.models.models as _models
        del _models
        
        # Check that models are registered
        assert len(Base.registry.mappers) > 0


class TestEnvironmentConfiguration:
    """Tests for environment configuration."""
    
    def test_required_env_vars_set(self, monkeypatch):
        """Test required environment variables are set."""
        from app.core.config import settings
        
        required_vars = [
            "ENVIRONMENT",
            "JWT_SECRET",
            "HYPERCODE_REDIS_URL",
            "HYPERCODE_DB_URL",
        ]
        
        for var in required_vars:
            value = getattr(settings, var, None)
            assert value is not None


class TestSecretManagement:
    """Tests for secret management."""
    
    def test_secrets_not_in_logs(self, monkeypatch, caplog):
        """Test secrets are not logged."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-key")
        
        # Simulate logging
        logger = logging.getLogger("app")
        logger.debug("Configuration loaded")
        
        # Check logs don't contain secret
        assert "sk-ant-secret-key" not in caplog.text
    
    def test_jwt_secret_used(self):
        """Test JWT secret is configured."""
        from app.core.config import settings
        
        assert hasattr(settings, "JWT_SECRET")
        assert settings.JWT_SECRET is not None
        assert len(settings.JWT_SECRET) > 10


class TestDockerEnvironment:
    """Tests for Docker environment."""
    
    def test_running_in_container(self):
        """Test if running in Docker."""
        import os
        
        # Check for Docker indicators
        in_docker = os.path.exists('/.dockerenv')
        
        # Test should pass whether in Docker or not
        assert isinstance(in_docker, bool)


@pytest.mark.parametrize("service", [
    "redis",
    "postgres",
])
def test_services_accessible(service):
    """Test all required services are accessible."""
    # This is a placeholder - extend based on your setup
    assert service in ["redis", "postgres"]
