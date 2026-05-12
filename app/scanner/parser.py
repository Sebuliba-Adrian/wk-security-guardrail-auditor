"""IaC file parser — normalises Terraform and CloudFormation into resource dicts."""

from __future__ import annotations

import os
from typing import Any


class FileParser:
    """Parse .tf, .json, .yaml/.yml files into a normalised resource list.

    Returns (resources, parse_error). Never raises except for unsupported extension.
    """

    SUPPORTED = {".tf", ".json", ".yaml", ".yml"}

    @staticmethod
    def parse(content: bytes, filename: str) -> tuple[list[dict[str, Any]], bool]:
        ext = os.path.splitext(filename.lower())[1]
        if ext not in FileParser.SUPPORTED:
            raise ValueError(f"unsupported extension: {ext}")
        try:
            if ext == ".tf":
                return FileParser._terraform(content)
            if ext == ".json":
                return FileParser._cfn_json(content)
            return FileParser._cfn_yaml(content)
        except ValueError:
            raise
        except Exception:
            return [], True

    @staticmethod
    def _terraform(content: bytes) -> tuple[list[dict[str, Any]], bool]:
        import io

        import hcl2

        try:
            data: Any = hcl2.load(  # type: ignore
                io.StringIO(content.decode("utf-8", errors="replace"))
            )
        except Exception:
            return [], True

        # hcl2 returns "resource" as a list of single-key dicts
        resources: list[dict[str, Any]] = []
        resource_blocks: Any = data.get("resource", [])
        for block in resource_blocks:
            if not isinstance(block, dict):
                continue
            for rtype, instances in block.items():
                if not isinstance(instances, dict):
                    continue
                for name, cfg in instances.items():
                    resources.append({
                        "type": rtype,
                        "name": name,
                        "config": cfg if isinstance(cfg, dict) else {},
                    })
        return resources, False

    @staticmethod
    def _cfn_json(content: bytes) -> tuple[list[dict[str, Any]], bool]:
        import json

        try:
            data: Any = json.loads(content)
        except json.JSONDecodeError:
            return [], True
        return FileParser._cfn_resources(data)

    @staticmethod
    def _cfn_yaml(content: bytes) -> tuple[list[dict[str, Any]], bool]:
        import yaml

        try:
            data: Any = yaml.safe_load(content)
        except yaml.YAMLError:
            return [], True
        if not isinstance(data, dict):
            return [], True
        return FileParser._cfn_resources(data)

    @staticmethod
    def _cfn_resources(data: Any) -> tuple[list[dict[str, Any]], bool]:
        resources: list[dict[str, Any]] = []
        cfn_resources: Any = data.get("Resources", {})
        for name, body in cfn_resources.items():
            if not isinstance(body, dict):
                continue
            resources.append({
                "type": body.get("Type", ""),
                "name": name,
                "config": body.get("Properties") or {},
            })
        return resources, False
