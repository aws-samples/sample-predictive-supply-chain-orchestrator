"""Application settings loaded from environment variables."""

import os


class Settings:
    """Simple settings object backed by env vars with sensible defaults."""

    def __init__(self):
        self.flask_env = os.environ.get("FLASK_ENV", "development")
        self.flask_port = int(os.environ.get("FLASK_PORT", "5000"))
        self.flask_debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
        self.cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        self.data_path = os.environ.get("DATA_PATH", os.environ.get("DATA_DIR", "../data"))
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")

    @property
    def cors_origins_list(self):
        origins = self.cors_origins
        if origins == "*":
            return ["*"]
        return [o.strip() for o in origins.split(",") if o.strip()]


settings = Settings()
