from dataclasses import dataclass

from edcpy.utils import join_url


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
