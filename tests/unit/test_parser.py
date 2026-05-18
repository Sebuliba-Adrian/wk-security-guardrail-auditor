"""
Unit tests — FileParser
Phase: RED — all tests must FAIL before implementation exists.

INTENT: As a DevOps engineer, I want to upload any IaC file so that the system
extracts its resources without me knowing which parser handles which format.

Spec: SPEC.md § file-parser
"""

import pytest

# ---------------------------------------------------------------------------
# AC-01: Valid Terraform — returns resource list
# ---------------------------------------------------------------------------
TERRAFORM_VALID = b"""
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-bucket"
  acl    = "private"
}

resource "aws_instance" "web" {
  ami           = "ami-123456"
  instance_type = "t3.micro"
}
"""


def test_given_valid_tf_when_parsed_then_returns_two_resources() -> None:
    from app.scanner.parser import FileParser
    resources, parse_error = FileParser.parse(TERRAFORM_VALID, "main.tf")
    assert parse_error is False
    assert len(resources) == 2


def test_given_valid_tf_when_parsed_then_resources_have_required_keys() -> None:
    from app.scanner.parser import FileParser
    resources, _ = FileParser.parse(TERRAFORM_VALID, "main.tf")
    for r in resources:
        assert "type" in r
        assert "name" in r
        assert "config" in r


def test_given_valid_tf_when_parsed_then_resource_types_are_correct() -> None:
    from app.scanner.parser import FileParser
    resources, _ = FileParser.parse(TERRAFORM_VALID, "main.tf")
    types = {r["type"] for r in resources}
    assert "aws_s3_bucket" in types
    assert "aws_instance" in types


# ---------------------------------------------------------------------------
# AC-02: Malformed Terraform — returns empty list, parse_error True
# ---------------------------------------------------------------------------
TERRAFORM_MALFORMED = b"resource { this is NOT valid hcl2 syntax !!! @#$"


def test_given_malformed_tf_when_parsed_then_returns_empty_list() -> None:
    from app.scanner.parser import FileParser
    resources, parse_error = FileParser.parse(TERRAFORM_MALFORMED, "bad.tf")
    assert parse_error is True
    assert resources == []


def test_given_malformed_tf_when_parsed_then_does_not_raise() -> None:
    from app.scanner.parser import FileParser
    # Must never raise — always returns (list, bool)
    result = FileParser.parse(TERRAFORM_MALFORMED, "bad.tf")
    assert isinstance(result, tuple)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# AC-03: Empty file — returns empty list, no error
# ---------------------------------------------------------------------------
def test_given_empty_file_when_parsed_then_returns_empty_no_error() -> None:
    from app.scanner.parser import FileParser
    resources, parse_error = FileParser.parse(b"", "empty.tf")
    assert parse_error is False
    assert resources == []


# ---------------------------------------------------------------------------
# AC-04: CloudFormation JSON — returns normalised resource list
# ---------------------------------------------------------------------------
CFN_JSON = b"""{
  "Resources": {
    "MyBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {
        "BucketName": "my-bucket"
      }
    }
  }
}"""


def test_given_valid_cfn_json_when_parsed_then_returns_one_resource() -> None:
    from app.scanner.parser import FileParser
    resources, parse_error = FileParser.parse(CFN_JSON, "template.json")
    assert parse_error is False
    assert len(resources) == 1


def test_given_valid_cfn_json_when_parsed_then_type_is_correct() -> None:
    from app.scanner.parser import FileParser
    resources, _ = FileParser.parse(CFN_JSON, "template.json")
    assert resources[0]["type"] == "aws_s3_bucket"
    assert resources[0]["name"] == "MyBucket"


def test_given_invalid_cfn_json_when_parsed_then_parse_error_true() -> None:
    from app.scanner.parser import FileParser
    _, parse_error = FileParser.parse(b"{ this is not json", "bad.json")
    assert parse_error is True


# ---------------------------------------------------------------------------
# AC-05: CloudFormation YAML — returns normalised resource list
# ---------------------------------------------------------------------------
CFN_YAML = b"""
Resources:
  MyInstance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: t3.micro
      ImageId: ami-12345
"""


def test_given_valid_cfn_yaml_when_parsed_then_returns_one_resource() -> None:
    from app.scanner.parser import FileParser
    resources, parse_error = FileParser.parse(CFN_YAML, "template.yaml")
    assert parse_error is False
    assert len(resources) == 1
    assert resources[0]["type"] == "aws_instance"


def test_given_valid_cfn_yml_extension_when_parsed_then_works() -> None:
    from app.scanner.parser import FileParser
    resources, parse_error = FileParser.parse(CFN_YAML, "template.yml")
    assert parse_error is False
    assert len(resources) == 1


def test_given_invalid_cfn_yaml_when_parsed_then_parse_error_true() -> None:
    from app.scanner.parser import FileParser
    _, parse_error = FileParser.parse(b":\n  - bad: [yaml", "bad.yaml")
    assert parse_error is True


# ---------------------------------------------------------------------------
# AC-06: Unsupported extension — raises ValueError
# ---------------------------------------------------------------------------
def test_given_unsupported_extension_when_parsed_then_raises_value_error() -> None:
    from app.scanner.parser import FileParser
    with pytest.raises(ValueError, match="unsupported extension"):
        FileParser.parse(b"print('hello')", "script.py")


# ---------------------------------------------------------------------------
# Edge cases beyond acceptance criteria
# ---------------------------------------------------------------------------
def test_given_tf_with_no_resources_when_parsed_then_empty_list() -> None:
    from app.scanner.parser import FileParser
    terraform_no_resources = b'variable "env" { default = "prod" }'
    resources, parse_error = FileParser.parse(terraform_no_resources, "vars.tf")
    assert parse_error is False
    assert resources == []


def test_given_resource_with_no_properties_when_parsed_then_config_is_dict() -> None:
    from app.scanner.parser import FileParser
    minimal = b'resource "aws_s3_bucket" "bare" {}'
    resources, _ = FileParser.parse(minimal, "bare.tf")
    if resources:
        assert isinstance(resources[0]["config"], dict)


def test_given_linux_style_quoted_terraform_scalars_when_normalised_then_quotes_removed() -> None:
    from app.scanner.parser import _normalise_terraform_value

    normalised = _normalise_terraform_value({
        "acl": '"public-read"',
        "cidr_blocks": ['"0.0.0.0/0"'],
        "__is_block__": True,
        "tags": {
            '"Name"': '"bucket"',
            '"Environment"': '"prod"',
            "__is_block__": True,
        },
    })
    assert normalised == {
        "acl": "public-read",
        "cidr_blocks": ["0.0.0.0/0"],
        "tags": {"Name": "bucket", "Environment": "prod"},
    }


@pytest.mark.parametrize("filename,expected_count", [
    ("main.tf", 1),
    ("template.json", 1),
    ("template.yaml", 1),
])
def test_given_single_resource_files_when_parsed_then_correct_count(
    filename: str, expected_count: int
) -> None:
    from app.scanner.parser import FileParser
    contents = {
        "main.tf": b'resource "aws_s3_bucket" "b" { acl = "private" }',
        "template.json": b'{"Resources": {"B": {"Type": "AWS::S3::Bucket", "Properties": {}}}}',
        "template.yaml": b"Resources:\n  B:\n    Type: AWS::S3::Bucket\n    Properties: {}",
    }
    resources, parse_error = FileParser.parse(contents[filename], filename)
    assert parse_error is False
    assert len(resources) == expected_count


# ---------------------------------------------------------------------------
# AC-07: Pulumi state JSON — detected and parsed via content-sniffing
# ---------------------------------------------------------------------------

PULUMI_STATE = b"""{
  "version": 3,
  "deployment": {
    "resources": [
      {
        "urn": "urn:pulumi:dev::proj::aws:s3/bucket:Bucket::bad-bucket",
        "type": "aws:s3/bucket:Bucket",
        "inputs": {
          "acl": "public-read",
          "bucket": "bad-bucket"
        }
      },
      {
        "urn": "urn:pulumi:dev::proj::aws:ebs/volume:Volume::my-vol",
        "type": "aws:ebs/volume:Volume",
        "inputs": {
          "encrypted": false
        }
      }
    ]
  }
}"""


def test_given_pulumi_state_json_when_parsed_then_returns_two_resources() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(PULUMI_STATE, "stack.json")
    assert parse_error is False
    assert len(resources) == 2


def test_given_pulumi_state_json_when_parsed_then_types_are_normalised() -> None:
    from app.scanner.parser import FileParser

    resources, _ = FileParser.parse(PULUMI_STATE, "stack.json")
    types = {r["type"] for r in resources}
    assert "aws_s3_bucket" in types
    assert "aws_ebs_volume" in types


def test_given_pulumi_state_json_when_parsed_then_config_contains_inputs() -> None:
    from app.scanner.parser import FileParser

    resources, _ = FileParser.parse(PULUMI_STATE, "stack.json")
    bucket = next(r for r in resources if r["type"] == "aws_s3_bucket")
    assert bucket["config"].get("acl") == "public-read"


def test_given_pulumi_state_when_scanned_then_s3_public_acl_fires() -> None:
    """End-to-end: Pulumi state → scanner picks up violation."""
    from app.scanner.engine import ScannerEngine
    from app.scanner.parser import FileParser

    resources, _ = FileParser.parse(PULUMI_STATE, "stack.json")
    findings = ScannerEngine().scan(resources)
    assert any(f.rule_id == "S3_PUBLIC_ACL" for f in findings)
    assert any(f.rule_id == "UNENCRYPTED_EBS" for f in findings)


def test_given_cfn_json_when_parsed_then_still_routes_correctly() -> None:
    """Regression: CFN JSON must still be detected after content-sniffer added."""
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b'{"Resources": {"B": {"Type": "AWS::S3::Bucket", "Properties": {}}}}',
        "template.json",
    )
    assert parse_error is False
    assert resources[0]["type"] == "aws_s3_bucket"


def test_given_cfn_json_public_bucket_when_scanned_then_public_acl_finding_fires() -> None:
    """CloudFormation resources must normalise cleanly into the shared rule engine."""
    from app.scanner.engine import ScannerEngine
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "BadBucket": {
              "Type": "AWS::S3::Bucket",
              "Properties": {
                "AccessControl": "PublicRead"
              }
            }
          }
        }""",
        "bad.json",
    )
    assert parse_error is False
    findings = ScannerEngine().scan(resources)
    assert any(f.rule_id == "S3_PUBLIC_ACL" for f in findings)


def test_given_cfn_bucket_tags_and_versioning_when_parsed_then_properties_are_normalised() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "Bucket": {
              "Type": "AWS::S3::Bucket",
              "Properties": {
                "AccessControl": "Private",
                "VersioningConfiguration": {"Status": "Enabled"},
                "Tags": [
                  {"Key": "Name", "Value": "prod-bucket"},
                  {"Key": "Environment", "Value": "prod"}
                ]
              }
            }
          }
        }""",
        "bucket.json",
    )
    assert parse_error is False
    config = resources[0]["config"]
    assert config["acl"] == "private"
    assert config["versioning"] == {"enabled": True}
    assert config["tags"] == {"Name": "prod-bucket", "Environment": "prod"}


def test_given_cfn_iam_policy_when_parsed_then_policy_document_is_normalised() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "Policy": {
              "Type": "AWS::IAM::Policy",
              "Properties": {
                "PolicyDocument": {
                  "Statement": {
                    "Effect": "Allow",
                    "Action": "*"
                  }
                }
              }
            }
          }
        }""",
        "policy.json",
    )
    assert parse_error is False
    assert resources[0]["type"] == "aws_iam_policy"
    assert resources[0]["config"]["statement"] == [{"actions": ["*"]}]


def test_given_cfn_security_group_ingress_when_parsed_then_ports_and_cidrs_are_normalised() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "IngressRule": {
              "Type": "AWS::EC2::SecurityGroupIngress",
              "Properties": {
                "FromPort": 22,
                "ToPort": 22,
                "CidrIp": "0.0.0.0/0"
              }
            }
          }
        }""",
        "sg.json",
    )
    assert parse_error is False
    config = resources[0]["config"]
    assert resources[0]["type"] == "aws_security_group_rule"
    assert config["from_port"] == 22
    assert config["to_port"] == 22
    assert config["cidr_blocks"] == ["0.0.0.0/0"]
    assert config["type"] == "ingress"


def test_given_cfn_rds_cloudtrail_and_ssm_when_scanned_then_rules_fire() -> None:
    from app.scanner.engine import ScannerEngine
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "Db": {
              "Type": "AWS::RDS::DBInstance",
              "Properties": {
                "StorageEncrypted": false,
                "PubliclyAccessible": true,
                "Tags": [{"Key": "Name", "Value": "db"}, {"Key": "Environment", "Value": "prod"}]
              }
            },
            "Trail": {
              "Type": "AWS::CloudTrail::Trail",
              "Properties": {
                "IsLogging": false
              }
            },
            "Secret": {
              "Type": "AWS::SSM::Parameter",
              "Properties": {
                "Name": "db_password",
                "Value": "super-secret"
              }
            }
          }
        }""",
        "controls.json",
    )
    assert parse_error is False
    findings = {f.rule_id for f in ScannerEngine().scan(resources)}
    assert "UNENCRYPTED_RDS" in findings
    assert "PUBLIC_RDS" in findings
    assert "CLOUDTRAIL_DISABLED" in findings
    assert "HARDCODED_SECRET" in findings


def test_given_cfn_security_group_egress_when_scanned_then_unrestricted_egress_fires() -> None:
    from app.scanner.engine import ScannerEngine
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "EgressRule": {
              "Type": "AWS::EC2::SecurityGroupEgress",
              "Properties": {
                "FromPort": 0,
                "ToPort": 0,
                "CidrIp": "0.0.0.0/0"
              }
            }
          }
        }""",
        "egress.json",
    )
    assert parse_error is False
    findings = {f.rule_id for f in ScannerEngine().scan(resources)}
    assert "UNRESTRICTED_EGRESS" in findings


def test_given_cfn_with_intrinsic_functions_when_parsed_then_no_crash_and_safe_config() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "ParamSecret": {
              "Type": "AWS::SSM::Parameter",
              "Properties": {
                "Name": {"Fn::Sub": "${Env}-db-password"},
                "Value": {"Ref": "SecretValue"}
              }
            },
            "Bucket": {
              "Type": "AWS::S3::Bucket",
              "Properties": {
                "Tags": [
                  {"Key": "Name", "Value": {"Fn::Sub": "${Env}-bucket"}},
                  {"Key": "Environment", "Value": "prod"}
                ]
              }
            }
          }
        }""",
        "intrinsics.json",
    )
    assert parse_error is False
    assert len(resources) == 2
    assert resources[0]["config"]["name"] == {"Fn::Sub": "${Env}-db-password"}
    assert resources[0]["config"]["value"] == {"Ref": "SecretValue"}
    assert resources[1]["config"]["tags"] == {"Environment": "prod"}


def test_given_cfn_with_intrinsic_functions_when_scanned_then_no_false_positive_secret() -> None:
    from app.scanner.engine import ScannerEngine
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b"""{
          "Resources": {
            "ParamSecret": {
              "Type": "AWS::SSM::Parameter",
              "Properties": {
                "Name": {"Fn::Sub": "${Env}-db-password"},
                "Value": {"Ref": "SecretValue"}
              }
            }
          }
        }""",
        "intrinsics.json",
    )
    assert parse_error is False
    findings = {f.rule_id for f in ScannerEngine().scan(resources)}
    assert "HARDCODED_SECRET" not in findings


def test_given_cfn_with_non_dict_resources_shape_when_parsed_then_returns_parse_error() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b'{"Resources": ["not", "a", "mapping"]}',
        "broken.json",
    )
    assert parse_error is True
    assert resources == []


def test_given_unknown_json_when_parsed_then_returns_empty_no_error() -> None:
    from app.scanner.parser import FileParser

    resources, parse_error = FileParser.parse(
        b'{"arbitrary": "json", "no_known_keys": true}',
        "unknown.json",
    )
    assert parse_error is False
    assert resources == []


def test_given_pulumi_state_with_unmapped_type_when_parsed_then_uses_fallback() -> None:
    """Fallback heuristic: aws:newservice/resource:Resource → aws_newservice_resource."""
    from app.scanner.parser import FileParser

    state = b"""{
      "deployment": {
        "resources": [{
          "urn": "urn:pulumi:dev::proj::aws:newservice/resource:Resource::my-res",
          "type": "aws:newservice/resource:Resource",
          "inputs": {"key": "value"}
        }]
      }
    }"""
    resources, parse_error = FileParser.parse(state, "stack.json")
    assert parse_error is False
    assert len(resources) == 1
    assert resources[0]["type"] == "aws_newservice_resource"
