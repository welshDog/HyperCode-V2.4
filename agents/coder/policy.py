import logging

logger = logging.getLogger("security-policy")

ALLOWED_IMAGES = {
    "python:3.10", "python:3.11", "python:3.9-slim",
    "node:18", "node:20",
    "postgres:14", "postgres:15", "postgres:alpine",
    "redis:7", "redis:alpine",
    "nginx:alpine"
}

class SecurityPolicy:
    @staticmethod
    def check_image(image_name: str) -> bool:
        # Check exact match
        if image_name in ALLOWED_IMAGES:
            return True
        # Check if it starts with allowed prefix (e.g. library images)
        # For now, we keep it strict or allow "latest" versions of allowed
        base_name = image_name.split(":")[0]
        if f"{base_name}:alpine" in ALLOWED_IMAGES: # Allow alpine if listed
             return True
             
        return False

    @staticmethod
    def validate_tool_call(tool_name: str, arguments: dict) -> bool:
        """
        Intercepts tool calls and validates them against security policy.
        Returns True if allowed, False otherwise.
        """
        if tool_name in ["docker_container_create", "docker_container_run", "docker_run"]:
            image = arguments.get("image") or arguments.get("Image")
            if image:
                if not SecurityPolicy.check_image(image):
                    logger.warning(f"SECURITY ALERT: Blocked attempt to use disallowed image '{image}'")
                    return False
        return True
