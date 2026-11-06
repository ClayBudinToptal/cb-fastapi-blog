#
# application configuration file
#
# parsed with pydantic-settings, which allows for environment variable overrides and validation
# see https://pydantic-docs.helpmanual.io/usage/settings/
#

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings (BaseSettings):
	# configuration for pydantic-settings
	model_config = SettingsConfigDict(
		env_file=".env",			# load environment variables from .env file
		env_file_encoding="utf-8",	# encoding for .env file
	)

	# application settings
	#app_name: str = "FastAPI Blog"
	#debug: bool = False
	#database_url: str = "sqlite:///./blog.db"	# default to sqlite database in current directory

	# authentication settings - these map to environment variables in .env file - type insensitive SECRET_KEY - if no .env will use system environment variables if set, otherwise will use default values below
	secret_key: SecretStr = SecretStr("default-secret-key")	# secret key for signing JWT tokens - pydantic won't leak this
	algorithm: str = "HS256"	# algorithm for signing JWT tokens
	access_token_expire_minutes: int = 30	# access token expiration time in minutes

	max_upload_size_bytes: int = 5 * 1024 * 1024	# maximum upload size in bytes (5 MB)

	posts_per_page: int = 10	# pagination

	reset_token_expire_minutes: int = 60

	## Email Configuration Settings
	mail_server: str = "localhost"
	mail_port: int = 587			# standard port for SMTP with Start TLS (encryption)
	mail_username: str = ""
	mail_password: SecretStr = SecretStr("")
	mail_from: str = "noreply@example.com"
	mail_use_tls: bool = True

	frontend_url: str = "http://localhost:8000"


settings = Settings()	# create a global settings object that can be imported and used throughout the application



