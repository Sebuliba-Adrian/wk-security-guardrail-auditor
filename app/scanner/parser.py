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

_CFN_TYPE_MAP: dict[str, str] = {
    "AWS::S3::Bucket": "aws_s3_bucket",
    "AWS::EC2::SecurityGroupIngress": "aws_security_group_rule",
    "AWS::EC2::SecurityGroupEgress": "aws_security_group_rule",
    "AWS::IAM::Policy": "aws_iam_policy",
    "AWS::EBS::Volume": "aws_ebs_volume",
    "AWS::RDS::DBInstance": "aws_db_instance",
    "AWS::CloudTrail::Trail": "aws_cloudtrail",
    "AWS::SSM::Parameter": "aws_ssm_parameter",
    "AWS::EC2::Instance": "aws_instance",
}

_CFN_ACL_MAP: dict[str, str] = {
    "PublicRead": "public-read",
    "PublicReadWrite": "public-read-write",
    "Private": "private",
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


def _normalise_cfn_type(cfn_type: str) -> str:
    return _CFN_TYPE_MAP.get(cfn_type, cfn_type)


def _normalise_cfn_tags(value: Any) -> dict[str, str] | Any:
    if not isinstance(value, list):
        return value

    tags: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        key = item.get("Key")
        tag_value = item.get("Value")
        if isinstance(key, str) and isinstance(tag_value, str):
            tags[key] = tag_value
    return tags


def _normalise_cfn_policy_document(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    statements = value.get("Statement", [])
    if isinstance(statements, dict):
        statements = [statements]

    normalised: list[dict[str, Any]] = []
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        actions = stmt.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        normalised.append({"actions": actions})
    return normalised


def _normalise_cfn_properties(cfn_type: str, properties: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(properties)

    if "Tags" in cfg:
        cfg["tags"] = _normalise_cfn_tags(cfg["Tags"])

    if cfn_type == "AWS::S3::Bucket":
        acl = cfg.get("AccessControl")
        if isinstance(acl, str):
            cfg["acl"] = _CFN_ACL_MAP.get(acl, acl)
        versioning = cfg.get("VersioningConfiguration")
        if isinstance(versioning, dict):
            cfg["versioning"] = {"enabled": versioning.get("Status") == "Enabled"}

    if cfn_type in {"AWS::EC2::SecurityGroupIngress", "AWS::EC2::SecurityGroupEgress"}:
        cidr_blocks: list[str] = []
        if isinstance(cfg.get("CidrIp"), str):
            cidr_blocks.append(cfg["CidrIp"])
        if isinstance(cfg.get("CidrIpv6"), str):
            cidr_blocks.append(cfg["CidrIpv6"])
        cfg["cidr_blocks"] = cidr_blocks
        cfg["from_port"] = cfg.get("FromPort", -1)
        cfg["to_port"] = cfg.get("ToPort", -1)
        cfg["type"] = "egress" if cfn_type.endswith("Egress") else "ingress"

    if cfn_type == "AWS::IAM::Policy":
        cfg["statement"] = _normalise_cfn_policy_document(cfg.get("PolicyDocument"))

    if cfn_type == "AWS::EBS::Volume":
        cfg["encrypted"] = cfg.get("Encrypted")

    if cfn_type == "AWS::RDS::DBInstance":
        cfg["storage_encrypted"] = cfg.get("StorageEncrypted")
        cfg["publicly_accessible"] = cfg.get("PubliclyAccessible")

    if cfn_type == "AWS::CloudTrail::Trail":
        cfg["enable_logging"] = cfg.get("IsLogging")

    if cfn_type == "AWS::SSM::Parameter":
        if "Name" in cfg:
            cfg["name"] = cfg["Name"]
        if "Value" in cfg:
            cfg["value"] = cfg["Value"]

    return cfg


def _normalise_terraform_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        return value
    if isinstance(value, list):
        return [_normalise_terraform_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(k).strip('"'): _normalise_terraform_value(v)
            for k, v in value.items()
            if str(k) != "__is_block__"
        }
    return value


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
                        "config": _normalise_terraform_value(cfg) if isinstance(cfg, dict) else {},
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
            cfn_type = body.get("Type", "")
            properties = body.get("Properties") or {}
            resources.append({
                "type": _normalise_cfn_type(cfn_type),
                "name": name,
                "config": (
                    _normalise_cfn_properties(cfn_type, properties)
                    if isinstance(properties, dict)
                    else {}
                ),
            })
        return resources, False
