import json
import logging
import os
import pprint
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union
from urllib.parse import quote

import coloredlogs
import environ
import requests
import sh
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwcrypto import jwk

_logger = logging.getLogger(__name__)


class VerifiableCredential:
    def __init__(self, name: str, country_subdivision_code: str = "ES-AS") -> None:
        self.name = name
        self.country_subdivision_code = country_subdivision_code

    def to_json_dict(self) -> Dict[str, Any]:
        # Some fields are set to None because they will be
        # filled in later by the Issuer service.

        uid_lrn = uuid.uuid4().hex
        uid_tac = uuid.uuid4().hex

        return {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/suites/jws-2020/v1",
                "https://registry.lab.gaia-x.eu/development/api/trusted-shape-registry/v1/shapes/jsonld/trustframework#",
                "https://schema.org/version/latest/schemaorg-current-https.jsonld",
            ],
            "id": None,
            "type": ["VerifiableCredential", "DataCellarCredential"],
            "issuer": {"id": None},
            "issuanceDate": None,
            "credentialSubject": {
                "type": "gx:LegalParticipant",
                "gx:legalName": self.name,
                "gx:legalRegistrationNumber": {
                    "id": f"https://example.com/lrn/{uid_lrn}"
                },
                "gx:headquarterAddress": {
                    "gx:countrySubdivisionCode": self.country_subdivision_code
                },
                "gx:legalAddress": {
                    "gx:countrySubdivisionCode": self.country_subdivision_code
                },
                "gx-terms-and-conditions:gaiaxTermsAndConditions": f"https://example.com/tac/{uid_tac}",
                "id": None,
                "schema:description": (
                    "This field demonstrates the possibility of "
                    "using additional ontologies to add fields "
                    "that are not explicitly included in the "
                    "Trust Framework specification."
                ),
            },
        }


@environ.config(prefix="")
class AppConfig:
    issuer_api_base_url = environ.var()
    verifier_api_base_url = environ.var()

    did_web_domain = environ.var(converter=quote)
    did_web_webserver_base_path = environ.var(default=None)
    did_web_path_consumer = environ.var(default="consumer")
    did_web_path_provider = environ.var(default="provider")
    did_web_path_anchor = environ.var(default="anchor")

    wallet_anchor_api_base_url = environ.var()
    wallet_anchor_user_name = environ.var()
    wallet_anchor_user_password = environ.var()
    wallet_anchor_user_email = environ.var()

    wallet_consumer_api_base_url = environ.var()
    wallet_consumer_user_name = environ.var()
    wallet_consumer_user_password = environ.var()
    wallet_consumer_user_email = environ.var()

    wallet_provider_api_base_url = environ.var()
    wallet_provider_user_name = environ.var()
    wallet_provider_user_password = environ.var()
    wallet_provider_user_email = environ.var()


def auth_login_wallet(wallet_api_base_url: str, email: str, password: str) -> str:
    url = wallet_api_base_url + "/wallet-api/auth/login"
    data = {"type": "email", "email": email, "password": password}
    response = requests.post(url, json=data)
    response.raise_for_status()
    res_json = response.json()
    _logger.info(res_json)
    return res_json["token"]


def get_first_wallet_id(wallet_api_base_url: str, wallet_token: str) -> str:
    headers = {"Authorization": "Bearer " + wallet_token}
    url_accounts = wallet_api_base_url + "/wallet-api/wallet/accounts/wallets"
    res_accounts = requests.get(url_accounts, headers=headers)
    res_accounts.raise_for_status()
    res_accounts_json = res_accounts.json()
    _logger.info(res_accounts_json)
    return res_accounts_json["wallets"][0]["id"]


def get_openid4vc_credential_offer_url(
    jwk: dict,
    vc: dict,
    issuer_api_base_url: str,
    issuer_did: str,
    credential_configuration_id: str = "VerifiableId_jwt_vc_json",
) -> str:
    issuance_key = {"type": "jwk", "jwk": jwk}

    mapping = {
        "id": "<uuid>",
        "issuer": {"id": "<issuerDid>"},
        "credentialSubject": {"id": "<subjectDid>"},
        "issuanceDate": "<timestamp>",
        "expirationDate": "<timestamp-in:365d>",
    }

    data = {
        "credentialConfigurationId": credential_configuration_id,
        "issuerKey": issuance_key,
        "credentialData": vc,
        "mapping": mapping,
        "issuerDid": issuer_did,
    }

    _logger.debug(pprint.pformat(data))

    url_issue = issuer_api_base_url + "/openid4vc/jwt/issue"
    res_issue = requests.post(url_issue, headers={"Accept": "text/plain"}, json=data)
    res_issue.raise_for_status()
    credential_offer_url = res_issue.text
    _logger.info("Credential Offer URL:\n%s", credential_offer_url)

    return credential_offer_url


def accept_credential_offer(
    wallet_api_base_url: str,
    wallet_id: str,
    user_did_key: str,
    wallet_token: str,
    credential_offer_url: str,
) -> dict:
    url_use_offer_request = (
        wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/exchange/useOfferRequest"
    )

    headers = {"Authorization": "Bearer " + wallet_token}

    res_use_offer_request = requests.post(
        url_use_offer_request,
        headers={**headers, **{"Accept": "*/*", "Content-Type": "text/plain"}},
        params={"did": user_did_key},
        data=credential_offer_url,
    )

    try:
        res_use_offer_request.raise_for_status()
    except requests.exceptions.HTTPError:
        _logger.error(res_use_offer_request.text)
        raise

    res_use_offer_request_json = res_use_offer_request.json()
    _logger.info(pprint.pformat(res_use_offer_request_json))

    return res_use_offer_request_json


def create_wallet_user(wallet_api_base_url: str, name: str, email: str, password: str):
    url = wallet_api_base_url + "/wallet-api/auth/register"

    data = {
        "name": name,
        "email": email,
        "password": password,
        "type": "email",
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        _logger.info(response.text)
    except requests.exceptions.HTTPError:
        _logger.warning("Request failed, this is expected if the user already exists.")


def export_key_jwk(
    wallet_api_base_url: str, wallet_id: str, key_id: str, wallet_token: str
) -> dict:
    headers = {"Authorization": "Bearer " + wallet_token}

    url_export_key = (
        wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/keys/{key_id}/export"
    )

    res_export_key_jwk = requests.get(
        url_export_key,
        headers=headers,
        params={"format": "JWK", "loadPrivateKey": True},
    )

    try:
        res_export_key_jwk.raise_for_status()
    except:
        _logger.error(res_export_key_jwk.text)
        raise

    key_jwk = res_export_key_jwk.json()
    _logger.debug(pprint.pformat(key_jwk))

    return key_jwk


@dataclass
class WalletUser:
    wallet_api_base_url: str
    token: str
    wallet_id: str
    key_id: str
    did: str
    did_document: Dict[str, Any]

    def export_key_jwk(self) -> dict:
        return export_key_jwk(
            wallet_api_base_url=self.wallet_api_base_url,
            wallet_id=self.wallet_id,
            key_id=self.key_id,
            wallet_token=self.token,
        )

    @property
    def did_document_dict(self) -> Dict[str, Any]:
        return json.loads(self.did_document)

    @property
    def did_document_formatted_json(self, indent=2) -> str:
        return json.dumps(self.did_document_dict, indent=indent)

    def register_did_web(
        self, webserver_base_path: Union[str, None], did_filename: str = "did.json"
    ):
        if not webserver_base_path:
            _logger.warning(
                "Skipping DID registration (%s) because no web server path was provided",
                self.did,
            )

            return

        if not self.did.startswith("did:web:"):
            raise ValueError(f"This is not a DID Web: {self.did}")

        hostname = self.did.split(":")[2]

        remote_path = os.path.join(
            webserver_base_path, *self.did.split(":")[3:], "did.json"
        )

        _logger.info(
            (
                "Attempting to register DID (hostname=%s) (remote_path=%s). "
                "Please note that this requires SSH access to the server (%s) "
                "via the default SSH key with the current user. "
                "Make sure that your key is in the authorized_keys file of the server."
            ),
            hostname,
            remote_path,
            hostname,
        )

        temp_file_path = os.path.join(
            tempfile.gettempdir(), f"{uuid.uuid4().hex}-{did_filename}"
        )

        try:
            with open(temp_file_path, "w") as fh:
                fh.write(self.did_document_formatted_json)

            mkdir_args = (hostname, "mkdir", "-p", os.path.dirname(remote_path))
            sh.ssh(*mkdir_args)
            scp_args = (temp_file_path, f"{hostname}:{remote_path}")
            sh.scp(*scp_args)
        finally:
            try:
                os.remove(temp_file_path)
            # trunk-ignore(ruff/E722)
            except:
                pass


def generate_wallet_key(
    wallet_api_base_url: str,
    wallet_token: str,
    wallet_id: str,
    algorithm: str = "RSA",
) -> str:
    url_create_key = (
        wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/keys/generate"
    )

    headers = {"Authorization": "Bearer " + wallet_token}

    res_create_key = requests.post(
        url_create_key, headers=headers, params={"type": algorithm}
    )

    try:
        res_create_key.raise_for_status()
    except:
        _logger.error(res_create_key.text)
        raise

    key_id = res_create_key.text
    _logger.debug("Generate key response: %s", key_id)

    return key_id


def generate_rsa_jwk_keypair(key_size: int = 2048) -> Dict[str, Any]:
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=key_size, backend=default_backend()
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    jwk_key = jwk.JWK.from_pem(private_pem)

    return jwk_key.export(private_key=True, as_dict=True)


def list_keys(
    wallet_api_base_url: str, wallet_token: str, wallet_id: str
) -> List[Dict]:
    url_list = wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/keys"
    headers = {"Authorization": "Bearer " + wallet_token}
    res_list = requests.get(url_list, headers=headers)
    res_list.raise_for_status()
    return res_list.json()


def import_key(
    wallet_api_base_url: str, wallet_token: str, wallet_id: str, jwk: Dict[str, Any]
) -> str:
    key_id = jwk["kid"]

    keys_list_before = list_keys(
        wallet_api_base_url=wallet_api_base_url,
        wallet_token=wallet_token,
        wallet_id=wallet_id,
    )

    if any([item["keyId"]["id"] == key_id for item in keys_list_before]):
        raise ValueError("Key (kid=%s) already exists in the wallet", key_id)

    url_import_key = wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/keys/import"

    headers = {"Authorization": "Bearer " + wallet_token}

    _logger.debug(
        "Importing key to wallet (%s):\n%s", url_import_key, pprint.pformat(jwk)
    )

    res_import_key = requests.post(url_import_key, headers=headers, json=jwk)

    try:
        res_import_key.raise_for_status()
    except:
        _logger.error(res_import_key.text)
        raise

    keys_list_after = list_keys(
        wallet_api_base_url=wallet_api_base_url,
        wallet_token=wallet_token,
        wallet_id=wallet_id,
    )

    if not any([item["keyId"]["id"] == key_id for item in keys_list_after]):
        raise RuntimeError("Imported key (kid=%s) not found in the list", key_id)

    _logger.info("Imported key (kid=%s) into wallet: %s", key_id, url_import_key)

    return key_id


def create_did_web(
    wallet_api_base_url: str,
    wallet_token: str,
    did_web_domain: str,
    did_web_path: str,
    algorithm: str = "RSA",
    wallet_id: str = None,
    alias: str = None,
    generate_key_outside_wallet: bool = False,
) -> Tuple[str, str, str]:
    wallet_id = wallet_id or get_first_wallet_id(wallet_api_base_url, wallet_token)

    headers = {"Authorization": "Bearer " + wallet_token}

    if generate_key_outside_wallet:
        _logger.debug(
            "Generating key outside wallet to validate that the wallet plays well with external keys"
        )

        key_id = import_key(
            wallet_api_base_url=wallet_api_base_url,
            wallet_token=wallet_token,
            wallet_id=wallet_id,
            jwk=generate_rsa_jwk_keypair(),
        )
    else:
        key_id = generate_wallet_key(
            wallet_api_base_url=wallet_api_base_url,
            wallet_token=wallet_token,
            wallet_id=wallet_id,
            algorithm=algorithm,
        )

    _logger.info("Creating DID for key %s (wallet=%s)", key_id, wallet_id)

    url_create_did = (
        wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/dids/create/web"
    )

    params = {"keyId": key_id, "domain": did_web_domain, "path": did_web_path}

    if alias:
        params["alias"] = alias

    res_create_did = requests.post(url_create_did, headers=headers, params=params)

    try:
        res_create_did.raise_for_status()
    except:
        _logger.error(res_create_did.text)
        raise

    did_web = res_create_did.text
    _logger.debug("Create DID web response: %s", did_web)

    return (wallet_id, key_id, did_web)


def find_did_by_alias(
    wallet_api_base_url: str, wallet_token: str, wallet_id: str, alias: str
) -> Union[Dict, None]:
    url_dids = wallet_api_base_url + f"/wallet-api/wallet/{wallet_id}/dids"
    headers = {"Authorization": "Bearer " + wallet_token}
    res_dids = requests.get(url_dids, headers=headers)
    res_dids.raise_for_status()
    dids = res_dids.json()
    return next((item for item in dids if item["alias"] == alias), None)


def build_wallet_user(
    wallet_api_base_url: str,
    email: str,
    password: str,
    did_web_domain: str,
    did_web_path: str,
    alias: str = "datacellar",
    generate_key_outside_wallet: bool = False,
) -> WalletUser:
    """Build a wallet user object with a token and wallet ID."""

    token = auth_login_wallet(
        wallet_api_base_url=wallet_api_base_url, email=email, password=password
    )

    wallet_id = get_first_wallet_id(wallet_api_base_url, token)

    did_dict = find_did_by_alias(
        wallet_api_base_url=wallet_api_base_url,
        wallet_token=token,
        wallet_id=wallet_id,
        alias=alias,
    )

    if not did_dict:
        _logger.info(
            "Generating new key for alias '%s' (url=%s)", alias, wallet_api_base_url
        )

        create_did_web(
            wallet_api_base_url=wallet_api_base_url,
            wallet_token=token,
            wallet_id=wallet_id,
            alias=alias,
            did_web_domain=did_web_domain,
            did_web_path=did_web_path,
            generate_key_outside_wallet=generate_key_outside_wallet,
        )

    did_dict = find_did_by_alias(
        wallet_api_base_url=wallet_api_base_url,
        wallet_token=token,
        wallet_id=wallet_id,
        alias=alias,
    )

    _logger.debug("DID (alias=%s):\n%s", alias, pprint.pformat(did_dict))

    key_id = did_dict["keyId"]
    did = did_dict["did"]
    did_document = did_dict["document"]

    wallet_user = WalletUser(
        wallet_api_base_url=wallet_api_base_url,
        token=token,
        wallet_id=wallet_id,
        key_id=key_id,
        did=did,
        did_document=did_document,
    )

    _logger.debug("Wallet user (%s): %s", wallet_api_base_url, wallet_user)

    return wallet_user


def issue_vc(
    issuer_key_jwk: dict,
    issuer_did: str,
    vc_template: dict,
    issuer_api_base_url: str,
    recipient_wallet_user: WalletUser,
):
    _logger.info("Creating credential offer signed by: %s", issuer_did)

    credential_offer_url = get_openid4vc_credential_offer_url(
        jwk=issuer_key_jwk,
        vc=vc_template,
        issuer_api_base_url=issuer_api_base_url,
        issuer_did=issuer_did,
    )

    _logger.info(
        "Accepting credential offer with recipient user: %s", recipient_wallet_user.did
    )

    accept_credential_offer(
        wallet_api_base_url=recipient_wallet_user.wallet_api_base_url,
        wallet_id=recipient_wallet_user.wallet_id,
        user_did_key=recipient_wallet_user.did,
        wallet_token=recipient_wallet_user.token,
        credential_offer_url=credential_offer_url,
    )


def main():
    cfg = environ.to_config(AppConfig)
    _logger.info(cfg)

    for item in [
        (
            cfg.wallet_anchor_api_base_url,
            cfg.wallet_anchor_user_name,
            cfg.wallet_anchor_user_email,
            cfg.wallet_anchor_user_password,
        ),
        (
            cfg.wallet_consumer_api_base_url,
            cfg.wallet_consumer_user_name,
            cfg.wallet_consumer_user_email,
            cfg.wallet_consumer_user_password,
        ),
        (
            cfg.wallet_provider_api_base_url,
            cfg.wallet_provider_user_name,
            cfg.wallet_provider_user_email,
            cfg.wallet_provider_user_password,
        ),
    ]:
        _logger.info("Creating wallet user: %s", item[2])
        create_wallet_user(*item)

    authenticated_users = []
    register_error = False

    for kwargs in [
        {
            "wallet_api_base_url": cfg.wallet_anchor_api_base_url,
            "email": cfg.wallet_anchor_user_email,
            "password": cfg.wallet_anchor_user_password,
            "did_web_domain": cfg.did_web_domain,
            "did_web_path": cfg.did_web_path_anchor,
            "generate_key_outside_wallet": True,
        },
        {
            "wallet_api_base_url": cfg.wallet_consumer_api_base_url,
            "email": cfg.wallet_consumer_user_email,
            "password": cfg.wallet_consumer_user_password,
            "did_web_domain": cfg.did_web_domain,
            "did_web_path": cfg.did_web_path_consumer,
            "generate_key_outside_wallet": True,
        },
        {
            "wallet_api_base_url": cfg.wallet_provider_api_base_url,
            "email": cfg.wallet_provider_user_email,
            "password": cfg.wallet_provider_user_password,
            "did_web_domain": cfg.did_web_domain,
            "did_web_path": cfg.did_web_path_provider,
            "generate_key_outside_wallet": True,
        },
    ]:
        _logger.info("Logging in wallet user: %s", kwargs["email"])
        the_user = build_wallet_user(**kwargs)

        try:
            the_user.register_did_web(
                webserver_base_path=cfg.did_web_webserver_base_path
            )
        # trunk-ignore(ruff/E722)
        except:
            register_error = True
            _logger.warning("DID (%s) registration failed", the_user.did, exc_info=True)

        authenticated_users.append(the_user)

    anchor_wallet_user, consumer_wallet_user, provider_wallet_user = authenticated_users

    _logger.log(
        logging.WARNING if register_error else logging.DEBUG,
        "📣 Registering these DIDs is a requirement for completing this process:\n%s",
        "\n\n".join(
            [
                f"🪪 {did}\n\n{doc}\n"
                for did, doc in [
                    (
                        anchor_wallet_user.did,
                        anchor_wallet_user.did_document_formatted_json,
                    ),
                    (
                        consumer_wallet_user.did,
                        consumer_wallet_user.did_document_formatted_json,
                    ),
                    (
                        provider_wallet_user.did,
                        provider_wallet_user.did_document_formatted_json,
                    ),
                ]
            ]
        ),
    )

    vc_consumer = VerifiableCredential(name="Consumer").to_json_dict()
    vc_provider = VerifiableCredential(name="Provider").to_json_dict()

    issuer_key_jwk = anchor_wallet_user.export_key_jwk()

    issue_vc(
        issuer_key_jwk=issuer_key_jwk,
        issuer_did=anchor_wallet_user.did,
        vc_template=vc_consumer,
        issuer_api_base_url=cfg.issuer_api_base_url,
        recipient_wallet_user=consumer_wallet_user,
    )

    issue_vc(
        issuer_key_jwk=issuer_key_jwk,
        issuer_did=anchor_wallet_user.did,
        vc_template=vc_provider,
        issuer_api_base_url=cfg.issuer_api_base_url,
        recipient_wallet_user=provider_wallet_user,
    )


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")
    main()
