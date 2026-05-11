# VISION.md — Enterprise Security Guardrail Auditor

## Problem

Infrastructure-as-code (Terraform, CloudFormation) files ship with security
misconfigurations that are cheap to fix before deployment and expensive after.
Manual security reviews are slow, inconsistent, and catch only the patterns
the reviewer happens to know. Teams merge insecure IaC because no automated
gate exists in their workflow.

## Users

**Primary:** DevOps and Platform engineers who write and review Terraform or
CloudFormation before deployment.

**Secondary:** Security and compliance teams who audit infrastructure
configurations against organisational baselines.

## Success Criteria

1. Upload a `.tf`, `.json`, or `.yaml` IaC file → risk score + findings
   returned in under 5 seconds
2. Risk score is a single integer (0–100) with a clear colour-coded severity band
3. Every finding includes a specific remediation — not just a warning
4. Zero unhandled exceptions on any input (empty, malformed, oversized, wrong type)
5. Dashboard renders correctly with scan history, risk gauge, and findings breakdown
6. 12 security rules covering CRITICAL, HIGH, and MEDIUM severity patterns
7. Test coverage ≥ 85% with unit, integration, contract, and smoke tests

## Non-Goals

- Real-time or continuous scanning of live cloud infrastructure
- Multi-user authentication or team workspaces
- Cloud deployment of scanner results to external services
- Paid tier or billing integration
- Support for file formats beyond `.tf`, `.json`, `.yaml`
- Custom rule authoring by end users at runtime
