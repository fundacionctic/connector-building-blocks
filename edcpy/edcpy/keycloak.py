"""
Utilities to create the Keycloak entities (e.g. clients, client scopes)
that the EDC OAuth2 extension depends on (if enabled).
"""

import argparse
import logging
import pprint
import time

import coloredlogs
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

from edcpy.utils import join_url

_DEFAULT_KEYCLOAK_URL = "http://keycloak.local:8080"
_DEFAULT_KEYCLOAK_REALM = "edc"
_DEFAULT_KEYCLOAK_ADMIN_USER = "admin"
_DEFAULT_KEYCLOAK_ADMIN_PASS = "admin"

_SCOPE_NBF = "edc-nbf"
_SCOPE_AUD = "edc-aud"

_logger = logging.getLogger(__name__)


def build_headers(admin_token: str) -> dict:
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }


def get_admin_token(keycloak_url: str, admin_user: str, admin_pass: str) -> str:
    token_url = join_url(keycloak_url, "realms/master/protocol/openid-connect/token")

    token_data = {
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": admin_user,
        "password": admin_pass,
    }

    response = requests.post(token_url, data=token_data)
    access_token = response.json()["access_token"]

    return access_token


def get_realm(keycloak_url: str, admin_token: str, realm_name: str) -> dict:
    headers = build_headers(admin_token)
    url = join_url(keycloak_url, "admin/realms", realm_name)
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def create_realm(keycloak_url: str, admin_token: str, realm_name: str) -> dict:
    headers = build_headers(admin_token)

    realm_data = {
        "realm": realm_name,
        "enabled": True,
        "sslRequired": "external",
        "userManagedAccessAllowed": True,
    }

    url = join_url(keycloak_url, "admin/realms")
    response = requests.post(url, json=realm_data, headers=headers)
    response.raise_for_status()

    return get_realm(
        keycloak_url=keycloak_url, admin_token=admin_token, realm_name=realm_name
    )


def get_client(
    keycloak_url: str, realm_name: str, admin_token: str, client_id: str
) -> dict:
    headers = build_headers(admin_token)
    url = join_url(keycloak_url, "admin/realms", realm_name, "clients")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    clients = response.json()

    return next(item for item in clients if item["clientId"] == client_id)


def create_client(
    keycloak_url: str,
    realm_name: str,
    admin_token: str,
    client_id: str,
    client_data: dict,
) -> dict:
    headers = build_headers(admin_token)

    client_data = {
        "clientId": client_id,
        "name": f"EDC {client_id} client",
        "enabled": True,
        "protocol": "openid-connect",
        **client_data,
    }

    url = join_url(keycloak_url, "admin/realms", realm_name, "clients")
    response = requests.post(url, json=client_data, headers=headers)
    response.raise_for_status()

    return get_client(
        keycloak_url=keycloak_url,
        realm_name=realm_name,
        admin_token=admin_token,
        client_id=client_id,
    )


def create_nbf_scope(
    keycloak_url: str, realm_name: str, admin_token: str, scope_name: str
):
    now = int(time.time())

    data = {
        "name": scope_name,
        "description": "Scope to add the nbf claim for the EDC OAuth2 extension",
        "protocol": "openid-connect",
        "attributes": {
            "include.in.token.scope": "true",
            "display.on.consent.screen": "true",
        },
        "protocolMappers": [
            {
                "name": "Not Before",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-hardcoded-claim-mapper",
                "consentRequired": False,
                "config": {
                    "claim.value": f"{now}",
                    "userinfo.token.claim": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "claim.name": "nbf",
                    "jsonType.label": "long",
                    "access.tokenResponse.claim": "true",
                },
            }
        ],
    }

    headers = build_headers(admin_token)
    url = join_url(keycloak_url, "admin/realms", realm_name, "client-scopes")
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()


def create_aud_scope(
    keycloak_url: str,
    realm_name: str,
    admin_token: str,
    scope_name: str,
    custom_audience: str,
):
    data = {
        "name": scope_name,
        "description": "Scope to update the Audience claim for the EDC OAuth2 extension",
        "protocol": "openid-connect",
        "attributes": {
            "include.in.token.scope": "true",
            "display.on.consent.screen": "true",
        },
        "protocolMappers": [
            {
                "name": "audience-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper",
                "consentRequired": False,
                "config": {
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "included.custom.audience": custom_audience,
                },
            }
        ],
    }

    headers = build_headers(admin_token)
    url = join_url(keycloak_url, "admin/realms", realm_name, "client-scopes")
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()


def create_connector_client(
    keycloak_url: str,
    realm_name: str,
    admin_token: str,
    client_id: str,
    scope_name_nbf: str,
    scope_name_aud: str,
    cert_pem_path: str,
) -> dict:
    with open(cert_pem_path, "rb") as fh:
        cert_str = fh.read()
        cert_obj = load_pem_x509_certificate(cert_str, default_backend())
        cert_bytes = cert_obj.public_bytes(encoding=serialization.Encoding.PEM)

    cert_clean = (
        cert_bytes.decode("utf-8")
        .replace("-----BEGIN CERTIFICATE-----", "")
        .replace("-----END CERTIFICATE-----", "")
        .replace("\n", "")
    )

    client_data = {
        "clientId": client_id,
        "enabled": True,
        "clientAuthenticatorType": "client-jwt",
        "notBefore": 0,
        "bearerOnly": False,
        "consentRequired": False,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": True,
        "authorizationServicesEnabled": True,
        "publicClient": False,
        "protocol": "openid-connect",
        "attributes": {
            "oidc.ciba.grant.enabled": "false",
            "x509.subjectdn": "(.*?)(?:$)",
            "backchannel.logout.session.required": "true",
            "display.on.consent.screen": "false",
            "oauth2.device.authorization.grant.enabled": "false",
            "x509.allow.regex.pattern.comparison": "false",
            "backchannel.logout.revoke.offline.tokens": "false",
            "jwt.credential.certificate": cert_clean,
        },
        "fullScopeAllowed": True,
        "defaultClientScopes": [
            "web-origins",
            "acr",
            "profile",
            "roles",
            "email",
            scope_name_nbf,
            scope_name_aud,
        ],
    }

    return create_client(
        keycloak_url=keycloak_url,
        realm_name=realm_name,
        admin_token=admin_token,
        client_id=client_id,
        client_data=client_data,
    )


def build_base_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--log-level", type=str, default="DEBUG")
    parser.add_argument("--keycloak-url", type=str, default=_DEFAULT_KEYCLOAK_URL)
    parser.add_argument("--keycloak-realm", type=str, default=_DEFAULT_KEYCLOAK_REALM)

    parser.add_argument(
        "--keycloak-admin-user",
        type=str,
        default=_DEFAULT_KEYCLOAK_ADMIN_USER,
    )

    parser.add_argument(
        "--keycloak-admin-pass",
        type=str,
        default=_DEFAULT_KEYCLOAK_ADMIN_PASS,
    )

    return parser


def cli_create_connector_client():
    parser = build_base_parser()
    parser.add_argument("--connector-id", type=str, required=True)
    parser.add_argument("--connector-cert-path", type=str, required=True)
    args = parser.parse_args()

    coloredlogs.install(level=args.log_level.upper())

    _logger.debug("Args:\n%s", pprint.pformat(args))

    admin_token = get_admin_token(
        args.keycloak_url, args.keycloak_admin_user, args.keycloak_admin_pass
    )

    get_realm_kwargs = {
        "keycloak_url": args.keycloak_url,
        "realm_name": args.keycloak_realm,
        "admin_token": admin_token,
    }

    try:
        realm = get_realm(**get_realm_kwargs)
    except:
        create_realm(
            keycloak_url=args.keycloak_url,
            realm_name=args.keycloak_realm,
            admin_token=admin_token,
        )

        realm = get_realm(**get_realm_kwargs)

    _logger.debug("Realm:\n%s", pprint.pformat(realm))

    try:
        create_nbf_scope(
            keycloak_url=args.keycloak_url,
            realm_name=args.keycloak_realm,
            admin_token=admin_token,
            scope_name=_SCOPE_NBF,
        )
    except Exception as ex:
        _logger.debug("Scope '%s' creation exception: %s", _SCOPE_NBF, ex)

    try:
        custom_audience = join_url(args.keycloak_url, "realms", args.keycloak_realm)

        create_aud_scope(
            keycloak_url=args.keycloak_url,
            realm_name=args.keycloak_realm,
            admin_token=admin_token,
            scope_name=_SCOPE_AUD,
            custom_audience=custom_audience,
        )
    except Exception as ex:
        _logger.debug("Scope '%s' creation exception: %s", _SCOPE_AUD, ex)

    get_client_kwargs = {
        "keycloak_url": args.keycloak_url,
        "realm_name": args.keycloak_realm,
        "admin_token": admin_token,
        "client_id": args.connector_id,
    }

    try:
        client = get_client(**get_client_kwargs)
    except:
        create_connector_client(
            keycloak_url=args.keycloak_url,
            realm_name=args.keycloak_realm,
            admin_token=admin_token,
            client_id=args.connector_id,
            scope_name_nbf=_SCOPE_NBF,
            scope_name_aud=_SCOPE_AUD,
            cert_pem_path=args.connector_cert_path,
        )

        client = get_client(**get_client_kwargs)

    _logger.debug("Connector client:\n%s", pprint.pformat(client))
