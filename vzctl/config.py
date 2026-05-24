from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class NodeConfig:
    id: int
    nickname: str


@dataclass
class EnvironmentConfig:
    name: str
    nodes: list[NodeConfig]
    variables: dict[str, str]
    api_url: str
    api_token: str


@dataclass
class Config:
    environments: dict[str, EnvironmentConfig]


def load(path: Path = Path("config.yaml")) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Copy example-config.yaml to config.yaml and fill in your values."
        )

    raw = yaml.safe_load(path.read_text())

    global_api_url = raw.get("api_url", "")
    global_api_token = raw.get("api_token", "")

    environments: dict[str, EnvironmentConfig] = {}
    for env_key, env_data in raw.get("environments", {}).items():
        nodes = [
            NodeConfig(id=n["id"], nickname=n.get("nickname", str(n["id"])))
            for n in env_data.get("nodes", [])
        ]
        environments[env_key] = EnvironmentConfig(
            name=env_data["name"],
            nodes=nodes,
            variables={str(k): str(v) for k, v in env_data.get("variables", {}).items()},
            api_url=env_data.get("api_url", global_api_url),
            api_token=env_data.get("api_token", global_api_token),
        )

    return Config(environments=environments)


def get_env(config: Config, env_key: str) -> EnvironmentConfig:
    if env_key not in config.environments:
        available = ", ".join(config.environments.keys())
        raise KeyError(f"Environment '{env_key}' not found in config. Available: {available}")
    return config.environments[env_key]
