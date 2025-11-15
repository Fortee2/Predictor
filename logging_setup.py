import logging
import logging.config


def setup_logging():
    """
    Set up logging configuration with timed rotating file handler.
    """
    config = {
        "version": 1,
        "handlers": {
            "timed_rotating": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "analysis.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,
                "formatter": "standard",
            }
        },
        "formatters": {
            "standard": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
        },
        "loggers": {
            "moving_averages": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "news_sentiment": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "portfolio_cli": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "bollinger_bands": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "data_retrieval_consolidated": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "config": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "rsi_calculations": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "macd": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "options_data": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            "ticker_dao": {
                "handlers": ["timed_rotating"],
                "level": "INFO",
                "propagate": False,
            },
            # ... other loggers
        },
    }
    logging.config.dictConfig(config)
