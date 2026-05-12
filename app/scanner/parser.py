"""IaC file parser — normalises Terraform, CloudFormation, and Pulumi state into resource dicts."""

from __future__ import annotations

import os
from typing import Any

# Known Pulumi → Terraform type mappings for the 12 security rules
_PULUMI_TYPE_MAP: dict[str, str] = {
    "aws:s3/bucket:Bucket": "aws_s3_bucket",
    "aws:ec2/instance:Instance": "aws_instance",
    "aws:ebs/volume:Volume": "aws_ebs_volume",
    "aws:rds/instance:Instance": "aws_db_instance",
    "aws:iam/policy:Policy": "aws_iam_policy",
    "aws:iam/policyDocument:PolicyDocument": "aws_iam_policy_document",
    "aws:cloudtrail/trail:Trail": "aws_cloudtrail",
    "aws:ec2/securityGroup:SecurityGroup": "aws_security_group",
    "aws:ec2/securityGroupRule:SecurityGroupRule": "aws_security_group_rule",
    "aws:ssm/parameter:Parameter": "aws_ssm_parameter",
}


def _normalise_pulumi_type(pulumi_type: str) -> str:
    if pulumi_type in _PULUMI_TYPE_MAP:
        return _PULUMI_TYPE_MAP[pulumi_type]
    # Fallback heuristic: aws:s3/bucket:Bucket → aws_s3_bucket
    parts = pulumi_type.split(":")
    if len(parts) == 3:
        provider = parts[0]
        module = parts[1].replace("/", "_")
        return f"{provider}_{module}"
    return pulumi_type


class FileParser:
    """Parse .tf, .json, .yaml/.yml files into a normalised resource list.

    Supports Terraform HCL2, CloudFormation JSON/YAML, and Pulumi state JSON.
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
                return FileParser._dispatch_json(content)
            return FileParser._cfn_yaml(content)
        except ValueError:
            raise
        except Exception:
            return [], True

    @staticmethod
    def _dispatch_json(content: bytes) -> tuple[list[dict[str, Any]], bool]:
        """Content-sniff JSON to route between CFN, Pulumi state, and unknown formats."""
        import json

        try:
            data: Any = json.loads(content)
        except json.JSONDecodeError:
            return [], True

        if not isinstance(data, dict):
            return [], True

        # Pulumi state: has "deployment.resources" array
        deployment = data.get("deployment", {})
        if isinstance(deployment, dict) and "resources" in deployment:
            return FileParser._pulumi_state(data)

        # CloudFormation: has top-level "Resources" dict
        if "Resources" in data:
            return FileParser._cfn_resources(data)

        # Unknown JSON format — return empty, no error
        return [], False

    @staticmethod
    def _pulumi_state(data: Any) -> tuple[list[dict[str, Any]], bool]:
        resources: list[dict[str, Any]] = []
        for entry in data.get("deployment", {}).get("resources", []):
            if not isinstance(entry, dict):
                continue
            pulumi_type: str = entry.get("type", "")
            urn: str = entry.get("urn", "")
            name = urn.split("::")[-1] if "::" in urn else urn
            cfg: Any = entry.get("inputs", {})
            resources.append({
                "type": _normalise_pulumi_type(pulumi_type),
                "name": name,
                "config": cfg if isinstance(cfg, dict) else {},
            })
        return resources, False

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
                # hcl2 on some platforms/versions includes surrounding quotes in the key
                rtype = rtype.strip('"')
                for name, cfg in instances.items():
                    resources.append({
                        "type": rtype,
                        "name": name.strip('"'),
                        "config": cfg if isinstance(cfg, dict) else {},
                    })
        return resources, False

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
