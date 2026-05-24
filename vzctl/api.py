from __future__ import annotations

import json

import httpx

from vzctl.config import EnvironmentConfig, NodeConfig

_SYNC_ENDPOINT = "/1.0/environment/control/rest/addcontainerenvvars"
_DELETE_ENDPOINT = "/1.0/environment/control/rest/removecontainerenvvars"
_LIST_ENDPOINT = "/1.0/environment/control/rest/getcontainerenvvars"
_RESTART_ENDPOINT = "/1.0/environment/control/rest/restartnodes"
_READLOG_ENDPOINT = "/1.0/environment/control/rest/readlog"
_REDEPLOY_ENDPOINT = "/1.0/environment/control/rest/redeploycontainers"


class APIError(Exception):
    def __init__(self, node: NodeConfig, message: str):
        self.node = node
        super().__init__(message)


def _base_url(env: EnvironmentConfig) -> str:
    return env.api_url.rstrip("/")


def _check_response(resp: httpx.Response, node: NodeConfig) -> dict:
    resp.raise_for_status()
    body = resp.json()
    if body.get("result") != 0:
        raise APIError(node, f"API error (result={body.get('result')}): {body}")
    return body


def sync_vars(env: EnvironmentConfig, node: NodeConfig, variables: dict[str, str]) -> dict:
    with httpx.Client() as client:
        resp = client.post(
            f"{_base_url(env)}{_SYNC_ENDPOINT}",
            data={
                "session": env.api_token,
                "envName": env.name,
                "nodeId": node.id,
                "vars": json.dumps(variables),
            },
        )
    return _check_response(resp, node)


def list_vars(env: EnvironmentConfig, node: NodeConfig) -> dict[str, str]:
    with httpx.Client() as client:
        resp = client.post(
            f"{_base_url(env)}{_LIST_ENDPOINT}",
            data={
                "session": env.api_token,
                "envName": env.name,
                "nodeId": node.id,
            },
        )
    body = _check_response(resp, node)
    return body.get("object", {})


def delete_var(env: EnvironmentConfig, node: NodeConfig, key: str) -> dict:
    with httpx.Client() as client:
        resp = client.post(
            f"{_base_url(env)}{_DELETE_ENDPOINT}",
            data={
                "session": env.api_token,
                "envName": env.name,
                "nodeId": node.id,
                "vars": json.dumps([key]),
            },
        )
    return _check_response(resp, node)


def restart_node(env: EnvironmentConfig, node: NodeConfig) -> dict:
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{_base_url(env)}{_RESTART_ENDPOINT}",
            data={
                "session": env.api_token,
                "envName": env.name,
                "nodeId": node.id,
            },
        )
    return _check_response(resp, node)


def redeploy_node(env: EnvironmentConfig, node: NodeConfig, tag: str = "latest") -> dict:
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(
            f"{_base_url(env)}{_REDEPLOY_ENDPOINT}",
            data={
                "session": env.api_token,
                "envName": env.name,
                "nodeId": node.id,
                "tag": tag,
                "useExistingVolumes": "true",
            },
        )
    return _check_response(resp, node)


def read_log(env: EnvironmentConfig, node: NodeConfig, path: str, count: int | None = None) -> str:
    data: dict = {
        "session": env.api_token,
        "envName": env.name,
        "nodeId": node.id,
        "path": path,
    }
    if count is not None:
        data["count"] = count
    with httpx.Client() as client:
        resp = client.post(f"{_base_url(env)}{_READLOG_ENDPOINT}", data=data)
    body = _check_response(resp, node)
    return body.get("body", "")
