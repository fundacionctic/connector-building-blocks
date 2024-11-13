# pylint: disable=no-member,too-few-public-methods

from dataclasses import dataclass

import environ

from edcpy.utils import join_url

PREFIX = "EDC"


@environ.config(prefix=PREFIX)
class AppConfig:
    """Configuration class for the application."""

    cert_path: str = environ.var(default=None)
    rabbit_url: str = environ.var(default=None)
    http_api_port: int = environ.var(converter=int, default=8000)

    @environ.config
    class Connector:
        """The connection details for the Management and Control APIs of the instance
        of the EDC Connector that the current program is interacting with."""

        scheme: str = environ.var(default="http")
        host: str = environ.var()
        connector_id: str = environ.var()
        participant_id: str = environ.var()
        management_port: int = environ.var(default=9193, converter=int)
        management_path: str = environ.var(default="/management")
        control_port: int = environ.var(default=9192, converter=int)
        control_path: str = environ.var(default="/control")
        public_port: int = environ.var(default=9291, converter=int)
        public_path: str = environ.var(default="/public")
        protocol_port: int = environ.var(default=9194, converter=int)
        protocol_path: str = environ.var(default="/protocol")
        api_key: str = environ.var(default=None)
        api_key_header: str = environ.var(default="X-API-Key")

    connector: Connector = environ.group(Connector, optional=True)


def get_config() -> AppConfig:
    return AppConfig.from_environ()


@dataclass
class ConnectorUrls:
    conf: AppConfig

    @property
    def scheme_host(self) -> str:
        return f"{self.conf.connector.scheme}://{self.conf.connector.host}"

    @property
    def management_url(self) -> str:
        return join_url(
            f"{self.scheme_host}:{self.conf.connector.management_port}",
            self.conf.connector.management_path,
        )

    @property
    def control_url(self) -> str:
        return join_url(
            f"{self.scheme_host}:{self.conf.connector.control_port}",
            self.conf.connector.control_path,
        )

    @property
    def public_url(self) -> str:
        return join_url(
            f"{self.scheme_host}:{self.conf.connector.public_port}",
            self.conf.connector.public_path,
        )

    @property
    def protocol_url(self) -> str:
        return join_url(
            f"{self.scheme_host}:{self.conf.connector.protocol_port}",
            self.conf.connector.protocol_path,
        )
