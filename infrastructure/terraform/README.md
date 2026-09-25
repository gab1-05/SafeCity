# SafeCity — Terraform (AWS)

Infrastructure as code for deploying SafeCity to AWS: VPC, ECR, EKS, RDS
PostgreSQL, ElastiCache Redis, S3, IAM, ALB and CloudWatch.

> **Nothing in this directory has been applied.** These modules are written and
> reviewed but no AWS resource exists. Creating resources costs real money —
> read [Cost](#cost-warning) below before running `apply`.

---

## Layout

```
terraform/
├── versions.tf                 Project-wide version constraints (see note below)
├── backend.tf.example          S3 + DynamoDB remote-state backend
├── modules/                    Reusable, environment-agnostic building blocks
│   ├── network/                VPC, subnets, NAT, route tables, security groups
│   ├── ecr/                    Container registries with scan-on-push
│   ├── eks/                    Cluster, node group, OIDC provider, addons
│   ├── rds/                    PostgreSQL instance, parameter and subnet groups
│   ├── elasticache/            Redis replication group
│   ├── s3/                     Media bucket, encryption, lifecycle, CORS
│   ├── iam/                    Cluster, node, IRSA and CI roles
│   ├── cloudwatch/             Log groups, alarms, alert topic, dashboard
│   ├── alb/                    Load balancer, target groups, listeners, DNS
│   └── secrets/                Secrets Manager entries
└── environments/
    ├── dev/                    Disposable, cheapest viable settings
    ├── staging/                Mirrors production durability, smaller scale
    └── prod/                   Multi-AZ, deletion protection, 30-day backups
```

Each module has `main.tf`, `variables.tf` and `outputs.tf`.

### Two-phase IAM

The `iam` module is called **twice** per environment. The EKS control plane and
node roles must exist before the cluster, but the IRSA role needs the cluster's
OIDC provider, which only exists after it. `create_eks_roles` and `enable_irsa`
gate the two halves so this is not a circular dependency:

```
network → ecr → s3 → secrets → rds → elasticache
       → iam (create_eks_roles = true, enable_irsa = false)
       → eks
       → iam (create_eks_roles = false, enable_irsa = true)
       → alb → cloudwatch
```

### Why is there a `versions.tf` in the root *and* in each environment?

Terraform only reads `.tf` files in the working directory. The root file
documents project-wide constraints; the per-environment files are what
`terraform init` actually enforces, so both are required.

---

## Usage

Run everything from an environment directory.

```bash
cd infrastructure/terraform/environments/dev

cp terraform.tfvars.example terraform.tfvars   # then edit it
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -out=dev.tfplan                 # always inspect the plan
```

Only after reading the plan:

```bash
terraform apply dev.tfplan
```

### Remote state

Local state is fine for a first look but will corrupt as soon as two people
apply. Enable remote state before any shared deployment:

```bash
# One-time bootstrap (run once per AWS account, not per environment).
aws s3api create-bucket --bucket YOUR-TFSTATE-BUCKET --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api put-bucket-versioning --bucket YOUR-TFSTATE-BUCKET \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket YOUR-TFSTATE-BUCKET \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws dynamodb create-table --table-name safecity-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region ap-south-1

cp ../../backend.tf.example backend.tf        # set the key for this env
terraform init                                # accept the state migration
```

State contains generated database passwords. The state bucket must not be
public, and access to it should be limited to the CI role and operators.

### Destroy

`terraform destroy` is destructive and irreversible. Show the plan first, and
understand that production has `deletion_protection` and `prevent_destroy` set
on the database and media bucket, so those two must be handled deliberately:

```bash
cd infrastructure/terraform/environments/dev
terraform plan -destroy          # review
terraform destroy                # only for dev
```

Production teardown steps, including the order to remove guards, are in
[`../../docs/COST-CONTROL.md`](../../docs/COST-CONTROL.md).

---

## Cost warning

Approximate **monthly** cost in `ap-south-1` if left running. These are order-of-
magnitude figures for an academic project, not a quote.

| Component | dev | prod |
|---|---|---|
| EKS control plane | ~$73 | ~$73 |
| Worker nodes (EKS) | ~$60 (2× t3.medium spot) | ~$180 (3× on-demand) |
| NAT gateway | ~$32 (single) | ~$64 (per AZ) |
| RDS PostgreSQL | ~$13 (db.t4g.micro) | ~$90 (db.t4g.medium, Multi-AZ) |
| ElastiCache Redis | ~$12 | ~$50 |
| ALB | ~$18 | ~$25 |
| S3 + CloudWatch | a few $ | a few $ |
| **Total** | **~$210/month** | **~$490/month** |

The EKS control plane and NAT gateways bill **even with no traffic**. Always
destroy dev when you are not using it — see `docs/COST-CONTROL.md`.

---

## Security notes

- No credentials are hardcoded anywhere. Passwords are generated by the
  `secrets` module and stored in AWS Secrets Manager.
- Variables carrying secrets are marked `sensitive`, so they never appear in
  plan output or CI logs.
- Every resource is tagged with `Project`, `Environment`, `Owner` and
  `CostCenter`.
- IAM roles are least-privilege: the application role can read only its own
  secrets and write only to its own S3 bucket prefix.
- CI assumes a role via GitHub OIDC, scoped to this repository and to protected
  branches. No long-lived AWS access key exists in the repository or in GitHub.
- RDS enforces TLS (`rds.force_ssl = 1`), and both RDS and ElastiCache are
  encrypted at rest.
- S3 blocks all public access; incident media is only reachable through
  short-lived presigned URLs.

---

## Status

| Check | Status |
|---|---|
| `terraform fmt -check` | Not yet run locally (Terraform not installed in the dev environment) |
| `terraform validate` | Not yet run locally — runs in the `terraform-ci` workflow |
| `terraform plan` | Never run — no AWS credentials configured |
| `terraform apply` | **Never run.** No resources created. |
