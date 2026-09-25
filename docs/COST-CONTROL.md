# SafeCity — AWS Cost Control and Teardown Runbook

> ⚠️ **Read this before running `terraform apply`.**
>
> Nothing in this repository has been applied. No AWS resource exists. If you do apply
> the Terraform, you will start paying **per hour**, whether or not anyone uses the
> deployment. The dev environment costs roughly **$180/month idle** and the largest
> single line items cost money even with zero traffic.

---

## 1. The three facts that matter

1. **The EKS control plane bills hourly regardless of use.** ~$0.10/hour ≈ **$73/month**
   with no nodes, no traffic, and an empty cluster. It does not scale to zero.
2. **NAT gateways bill hourly plus per gigabyte.** ~$0.056/hour ≈ **$41/month each**.
   The dev overlay deliberately uses **one** shared NAT for this reason; staging and prod
   use one per AZ, which triples that line item.
3. **A forgotten environment is the normal failure mode, not an exotic one.** An SDP team
   applies the stack for a demo, passes the viva, and moves on. Six months later the
   account has been billed ~$1,000 for an idle cluster. Set a budget alarm *before* the
   first apply, not after.

---

## 2. Indicative monthly estimates

Region **ap-south-1 (Mumbai)**, on-demand pricing, **excluding** tax, credits, data
transfer and support. Figures are rounded and indicative only.

| Component | dev | staging | prod |
|-----------|-----|---------|------|
| EKS control plane | $73 | $73 | $73 |
| EKS worker nodes | 2 × `t3.medium` SPOT ≈ $20 | 2 × `t3.medium` ≈ $66 | 3 × `t3.medium` ≈ $99 |
| NAT gateway(s) | 1 × $41 | 3 × $41 = $123 | 3 × $41 = $123 |
| RDS PostgreSQL | `db.t4g.micro` ≈ $13 | `db.t4g.small` multi-AZ ≈ $52 | `db.t4g.medium` multi-AZ ≈ $104 |
| ElastiCache Redis | `cache.t4g.micro` ≈ $13 | multi-AZ 2 nodes ≈ $27 | multi-AZ 2 nodes ≈ $27 |
| Application Load Balancer | $16 | $16 | $16 |
| S3 (media, ~10 GB) | ~$1 | ~$1 | ~$2 |
| CloudWatch (logs + alarms) | ~$3 | ~$5 | ~$10 |
| ECR (image storage) | ~$1 | ~$1 | ~$1 |
| Secrets Manager | ~$2 | ~$2 | ~$2 |
| Route 53 hosted zone | $0.50 | $0.50 | $0.50 |
| **Indicative total / month** | **≈ $185** | **≈ $370** | **≈ $460** |

### What actually drives the bill

Ranked by how much they matter:

1. **NAT gateway hours** (and data processing per GB) — the most commonly underestimated line item. Replacing one NAT with three costs $82/month more.
2. **EKS control plane** — flat, unavoidable, and non-negotiable while the cluster exists.
3. **Node hours × instance type** — SPOT in dev cuts this by roughly 70%, at the cost of occasional reclamation.
4. **RDS multi-AZ** — roughly doubles the instance cost. Correct for staging and prod; wasteful for dev.
5. **Data transfer out** — free-ish at SDP scale, but media downloads add up if the platform is widely shared.

> **These numbers are not a quote.** AWS pricing changes, varies by region, and is
> affected by credits and Savings Plans. Confirm current figures with the
> [AWS Pricing Calculator](https://calculator.aws/) before committing to a budget, and
> check the estimate in `terraform plan` output.

---

## 3. Do you actually need AWS for the SDP?

Honestly: **probably not for the demonstration.** Split the two concerns:

| Purpose | Right tool | Cost |
|---------|-----------|------|
| Demonstrate a working platform | `docker compose up` (see [INSTALLATION-GUIDE.md](INSTALLATION-GUIDE.md)) | $0 |
| Demonstrate cloud architecture competence | The Terraform and Helm code, reviewed as code, plus `terraform plan` | $0 |

`terraform plan` exercises the entire module graph, surfaces provider and dependency
errors, and prints the resource changes — **without creating anything**. For an academic
submission, a reviewed plan plus passing `fmt`/`validate` demonstrates the same
engineering as an apply, at zero cost.

Apply only if you specifically need to prove the deployment runs on real infrastructure,
and destroy it the same day.

---

## 4. Budget alarms (do this first)

Set these **before** the first `apply`. An alarm configured afterwards is a record of
money already spent.

```bash
# Replace the email and confirm the SNS subscription from your inbox,
# or the alarm will fire into the void.
aws budgets create-budget \
  --account-id "$(aws sts get-caller-identity --query Account --output text)" \
  --budget '{
    "BudgetName": "safecity-monthly",
    "BudgetLimit": {"Amount": "100", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "you@example.com"}]
  }]'
```

Recommended supplementary alarms:

| Metric | Threshold | Why |
|--------|-----------|-----|
| Estimated charges | $50 (early warning) | Catches a runaway NAT or an autoscaler that never scales down |
| Estimated charges | $100 / $200 | Hard escalation |
| NAT gateway bytes | Daily spike | A misconfigured pod retrying an external endpoint can move real money |
| EKS node count | Above expected | A stuck HPA is a billing problem before it is a reliability one |

The CloudWatch module in the Terraform also creates log groups with explicit retention;
an unset retention policy on a busy log group is a slow, invisible cost.

---

## 5. Teardown runbook

### Standard dev teardown

```bash
cd infrastructure/terraform/environments/dev

# 1. See exactly what will be destroyed. Read it.
terraform plan -destroy -out=destroy.tfplan

# 2. Destroy.
terraform destroy

# 3. Confirm nothing is left billing.
aws ec2 describe-nat-gateways --filter "Name=state,Values=available" \
  --query 'NatGateways[].{Id:NatGatewayId,State:State}'
aws eks list-clusters
aws rds describe-db-instances \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Status:DBInstanceStatus}'
aws elasticache describe-cache-clusters --query 'CacheClusters[].CacheClusterId'
```

### Production teardown (ordered, and slow on purpose)

Production sets `deletion_protection` and `prevent_destroy` on the database and media
bucket, so those two **cannot** be destroyed until the guards are removed. This is
deliberate: it is the difference between a mistake and a catastrophe.

Order matters — destroy consumers before the network and data they depend on:

1. **Remove the ingress/DNS first.** Deleting the ALB while Route 53 still points at it
   produces confusing errors for anyone still using the hostname.
2. **Stop the application.** `helm uninstall safecity -n safecity-prod`. This removes
   Deployments, Services, Ingress and the migration Job.
3. **Take a final database snapshot** if the data has any value:
   ```bash
   aws rds create-db-snapshot \
     --db-instance-identifier safecity-prod-db \
     --db-snapshot-identifier safecity-prod-final-$(date +%F)
   ```
   Snapshots bill for storage, but they are cheap next to losing real data.
4. **Remove the RDS guard, then destroy.** Set `deletion_protection = false` in
   `environments/prod/main.tf`, run `terraform apply` to update the attribute *only*,
   then destroy. Alternatively use `terraform state rm` to stop managing it and delete it
   manually — but be explicit about which you are doing.
5. **Empty and remove the S3 bucket guard.** S3 refuses to delete a non-empty bucket.
   Decide deliberately whether to preserve media:
   ```bash
   aws s3 ls s3://safecity-prod-media --recursive --summarize | tail -2
   # If it should go:
   aws s3 rm s3://safecity-prod-media --recursive
   ```
6. **Destroy ElastiCache** (snapshots retained per `snapshot_retention_days`).
7. **Destroy the EKS node group, then the cluster.** Node groups first — deleting the
   cluster first can orphan instances that keep billing with no way to manage them.
8. **Destroy NAT gateways, then the VPC.** A NAT gateway cannot be deleted while it is
   attached to a subnet with a route table pointing at it; remove the route first. **An
   orphaned NAT gateway is the single most common source of "why am I still being
   charged?"**
9. **Remove remaining ECR images**, Secrets Manager entries, and the Route 53 hosted zone.
10. **Delete the Terraform state bucket last** — you need the state to destroy the
    resources it tracks.

### Verify the teardown

```bash
aws ec2 describe-nat-gateways --filter "Name=state,Values=available" --query 'NatGateways[].NatGatewayId'
aws eks list-clusters --query 'clusters'
aws rds describe-db-instances --query 'DBInstances[].DBInstanceIdentifier'
aws elasticache describe-cache-clusters --query 'CacheClusters[].CacheClusterId'
aws ec2 describe-addresses --query 'Addresses[].PublicIp'          # unattached EIPs bill
aws elbv2 describe-load-balancers --query 'LoadBalancers[].LoadBalancerName'
```

Then check **Billing → Cost Explorer** over the next two days. Cost reporting lags by up
to 24 hours, so a yesterday-shaped spike is normal and does not mean the teardown failed.

**Unattached Elastic IPs bill hourly.** They are free while attached to a running
instance and chargeable when idle — precisely the state a partial teardown leaves behind.

---

## 6. Cost hygiene checklist

Before applying:

- [ ] Budget alarm created **and the SNS subscription confirmed by email**
- [ ] `terraform plan` read, not skimmed
- [ ] You know today's date and when you will tear it down
- [ ] You are working in the intended account (check `aws sts get-caller-identity`)
- [ ] Dev uses `nat_gateway_per_az = false` and SPOT nodes
- [ ] Log retention is set to a finite number of days

After finishing:

- [ ] `helm uninstall` run
- [ ] `terraform destroy` run
- [ ] NAT gateways, unattached EIPs and load balancers verified gone
- [ ] Cost Explorer checked two days later

Never:

- [ ] Leave a cluster up "just in case" for more than a day
- [ ] Commit `terraform.tfvars` or a `*.tfstate` file — state contains the generated DB password
- [ ] Apply directly from a laptop without reviewing the plan

---

## 7. Cheaper alternatives worth considering

| Instead of | Consider | Trade-off |
|------------|----------|-----------|
| EKS control plane | A single EC2 instance running k3s | Loses the managed-control-plane story; saves ~$73/month |
| 3 NAT gateways | 1 shared NAT, or VPC endpoints for S3 | Loses AZ-level egress redundancy; saves ~$82/month |
| RDS | PostgreSQL in a container on the node | Loses managed backups and failover — not acceptable for real citizen data |
| ElastiCache | Redis in a container | Same |
| CloudWatch Logs | Shorter retention, or a self-hosted aggregator | Less history for incident forensics |

For an academic SDP these trade-offs are legitimate; for a real municipal deployment they
are not. Which is appropriate depends entirely on whether real citizen data is involved.
