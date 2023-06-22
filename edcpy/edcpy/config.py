from dataclasses import dataclass

import environ

from edcpy.utils import join_url

PREFIX = "EDC"


@environ.config(prefix=PREFIX)
class AppConfig:
    cert_path = environ.var(default=None)
    rabbit_url = environ.var(default=None)
    http_api_port = environ.var(converter=int, default=8000)

    @environ.config
    class ConsumerProviderPair:
        provider_host = environ.var("provider")
        consumer_host = environ.var("consumer")
        provider_connector_id = environ.var("urn:connector:provider")
        consumer_connector_id = environ.var("urn:connector:consumer")
        provider_participant_id = environ.var(provider_connector_id)
        consumer_participant_id = environ.var(consumer_connector_id)
        provider_management_port = environ.var(converter=int)
        consumer_management_port = environ.var(converter=int)
        provider_control_port = environ.var(converter=int)
        consumer_control_port = environ.var(converter=int)
        provider_public_port = environ.var(converter=int)
        consumer_public_port = environ.var(converter=int)
        provider_protocol_port = environ.var(converter=int)
        consumer_protocol_port = environ.var(converter=int)

    orchestrator = environ.group(ConsumerProviderPair, optional=True)


@dataclass
class ConsumerProviderPairConfig:
    provider_host: str
    consumer_host: str
    provider_connector_id: str
    consumer_connector_id: str
    provider_participant_id: str
    consumer_participant_id: str
    provider_management_port: int
    consumer_management_port: int
    provider_control_port: int
    consumer_control_port: int
    provider_public_port: int
    consumer_public_port: int
    provider_protocol_port: int
    consumer_protocol_port: int
    scheme: str = "http"
    provider_management_path: str = "/management"
    consumer_management_path: str = "/management"
    provider_control_path: str = "/control"
    consumer_control_path: str = "/control"
    provider_public_path: str = "/public"
    consumer_public_path: str = "/public"
    provider_protocol_path: str = "/protocol"
    consumer_protocol_path: str = "/protocol"

    @classmethod
    def from_env(cls):
        app_config = AppConfig.from_environ()
        assert app_config.orchestrator, "ConsumerProviderPair not configured"
        cnf = app_config.orchestrator

        return cls(
            provider_host=cnf.provider_host,
            consumer_host=cnf.consumer_host,
            provider_connector_id=cnf.provider_connector_id,
            consumer_connector_id=cnf.consumer_connector_id,
            provider_participant_id=cnf.provider_participant_id,
            consumer_participant_id=cnf.consumer_participant_id,
            provider_management_port=cnf.provider_management_port,
            consumer_management_port=cnf.consumer_management_port,
            provider_control_port=cnf.provider_control_port,
            consumer_control_port=cnf.consumer_control_port,
            provider_public_port=cnf.provider_public_port,
            consumer_public_port=cnf.consumer_public_port,
            provider_protocol_port=cnf.provider_protocol_port,
            consumer_protocol_port=cnf.consumer_protocol_port,
        )

    @property
    def provider_management_url(self):
        return join_url(
            f"{self.scheme}://{self.provider_host}:{self.provider_management_port}",
            self.provider_management_path,
        )

    @property
    def consumer_management_url(self):
        return join_url(
            f"{self.scheme}://{self.consumer_host}:{self.consumer_management_port}",
            self.consumer_management_path,
        )

    @property
    def provider_control_url(self):
        return join_url(
            f"{self.scheme}://{self.provider_host}:{self.provider_control_port}",
            self.provider_control_path,
        )

    @property
    def consumer_control_url(self):
        return join_url(
            f"{self.scheme}://{self.consumer_host}:{self.consumer_control_port}",
            self.consumer_control_path,
        )

    @property
    def provider_public_url(self):
        return join_url(
            f"{self.scheme}://{self.provider_host}:{self.provider_public_port}",
            self.provider_public_path,
        )

    @property
    def consumer_public_url(self):
        return join_url(
            f"{self.scheme}://{self.consumer_host}:{self.consumer_public_port}",
            self.consumer_public_path,
        )

    @property
    def provider_protocol_url(self):
        return join_url(
            f"{self.scheme}://{self.provider_host}:{self.provider_protocol_port}",
            self.provider_protocol_path,
        )

    @property
    def consumer_protocol_url(self):
        return join_url(
            f"{self.scheme}://{self.consumer_host}:{self.consumer_protocol_port}",
            self.consumer_protocol_path,
        )
