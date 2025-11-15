import json
import logging
import os

from dotenv import load_dotenv

# Set up logging - Modified to only log to file, not console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("config.log")
        # StreamHandler removed to prevent console output
    ],
)
logger = logging.getLogger("config")

# Ensure no handlers are outputting to console
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and not isinstance(
        handler, logging.FileHandler
    ):
        logger.removeHandler(handler)


class Config:
    """Configuration manager for the Portfolio application."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Load .env file for environment variables
        load_dotenv()

        # Default configuration values
        self.default_config = {
            "database": {"pool_size": 5, "timeout": 30, "retry_attempts": 3},
            "ui": {
                "theme": "default",
                "date_format": "%Y-%m-%d",
                "currency_symbol": "$",
            },
            "analysis": {
                "default_ma_period": 20,
                "default_rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
            },
            "watchlist": {"auto_refresh": True, "refresh_interval_minutes": 30},
            "logging": {"level": "INFO", "log_to_file": True, "log_path": "logs"},
            "chart": {
                "default_theme": "dark",
                "auto_save": True,
                "save_path": "charts",
            },
        }

        # User's configuration file path
        self.config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "user_config.json",
        )

        # Load or create configuration
        self.config = self._load_config()
        self._initialized = True

    def _load_config(self):
        """Load configuration from file or create default if not exists."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    user_config = json.load(f)
                    logger.info(f"Loaded configuration from {self.config_file}")
                    # Merge with defaults for any missing values
                    return self._merge_config(self.default_config, user_config)
            else:
                # Create default config file
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                with open(self.config_file, "w") as f:
                    json.dump(self.default_config, f, indent=4)
                logger.info(f"Created default configuration at {self.config_file}")
                return self.default_config
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return self.default_config

    def _merge_config(self, default_config, user_config):
        """Recursively merge user config with default config."""
        result = default_config.copy()

        for key, value in user_config.items():
            if (
                key in result
                and isinstance(value, dict)
                and isinstance(result[key], dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False

    def get(self, section, key=None):
        """Get a configuration value or section."""
        try:
            if section in self.config:
                if key is not None:
                    if key in self.config[section]:
                        return self.config[section][key]
                    else:
                        logger.warning(
                            f"Configuration key '{key}' not found in section '{section}'"
                        )
                        return None
                else:
                    return self.config[section]
            else:
                logger.warning(f"Configuration section '{section}' not found")
                return None
        except Exception as e:
            logger.error(f"Error getting configuration: {str(e)}")
            return None

    def set(self, section, key, value):
        """Set a configuration value."""
        try:
            if section not in self.config:
                self.config[section] = {}

            self.config[section][key] = value
            logger.info(f"Configuration updated: {section}.{key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting configuration: {str(e)}")
            return False

    def get_database_config(self):
        """Get database configuration with environment variables."""
        db_config = {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "database": os.getenv("DB_NAME"),
            "pool_size": self.get("database", "pool_size"),
            "timeout": self.get("database", "timeout"),
            "retry_attempts": self.get("database", "retry_attempts"),
        }
        return db_config

    def get_bedrock_config(self):
        """Get AWS Bedrock configuration from environment variables."""
        bedrock_config = {
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "model": os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
            "embed_model": os.getenv("BEDROCK_EMBED_MODEL", "amazon.titan-embed-text-v2:0"),
        }
        return bedrock_config
    
    def get_all(self):
        """Get the entire configuration."""
        return self.config
