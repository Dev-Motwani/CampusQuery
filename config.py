"""
Root configuration redirector.
Re-exports configuration classes and helpers from app.config.
"""
from app.config import (
    BASE_DIR,
    Config,
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
    config_by_name,
)

__all__ = [
    "BASE_DIR",
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "config_by_name",
]
