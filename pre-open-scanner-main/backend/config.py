"""
Configuration loading for Pre-Open Scanner.

Loads settings from .env (python-dotenv) and config.yaml (PyYAML).
"""

# TODO: Load env vars with pydantic-settings or python-dotenv
# TODO: Load config.yaml for Fyers credentials, Redis URL, scanner options
# from pydantic_settings import BaseSettings
# import yaml

# class Settings(BaseSettings):
#     redis_url: str = "redis://localhost:6379"
#     fyers_app_id: str = ""
#     fyers_secret: str = ""
#     class Config:
#         env_file = ".env"
