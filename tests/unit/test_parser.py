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
    assert resources[0]["type"] == "AWS::S3::Bucket"
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
    assert resources[0]["type"] == "AWS::EC2::Instance"


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
