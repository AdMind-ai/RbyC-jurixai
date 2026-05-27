from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import boto3
from django.conf import settings


AWS_SERVICE_MAP = {
    "Amazon Elastic Compute Cloud - Compute": ("ec2", "AWS EC2"),
    "Amazon Relational Database Service": ("rds", "AWS RDS"),
    "Amazon Simple Storage Service": ("s3", "AWS S3"),
    "Amazon CloudFront": ("cloudfront", "AWS CloudFront"),
    "AWS Lambda": ("lambda", "AWS Lambda"),
    "Amazon ElastiCache": ("elasticache", "AWS ElastiCache"),
    "Amazon Elastic Container Service": ("ecs", "AWS ECS"),
    "Amazon Elastic Kubernetes Service": ("eks", "AWS EKS"),
    "Amazon Route 53": ("route53", "AWS Route 53"),
    "AmazonCloudWatch": ("cloudwatch", "AWS CloudWatch"),
    "AWS Secrets Manager": ("secrets-manager", "AWS Secrets Manager"),
    "EC2 - Other": ("ec2-other", "AWS EC2 Other"),
    "Elastic Load Balancing": ("load-balancer", "AWS Load Balancer"),
    "NatGateway": ("nat-gateway", "AWS NAT Gateway"),
}


class AwsCostsConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AwsCostCollection:
    items: list[dict]
    total: Decimal
    currency: str


class AwsCostExplorerService:
    @classmethod
    def collect_monthly_costs(
        cls,
        *,
        period_month: date,
        currency: str,
    ) -> AwsCostCollection:
        region = cls._required_setting("INTERNAL_COSTS_AWS_REGION")

        client = boto3.client("ce", region_name=region)
        start_date = period_month.isoformat()
        end_date = cls._next_month(period_month).isoformat()
        period_key = period_month.strftime("%Y-%m")
        response = client.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": end_date},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        items: list[dict] = []
        total = Decimal("0.00")

        for time_bucket in response.get("ResultsByTime", []):
            for group in time_bucket.get("Groups", []):
                metric = ((group.get("Metrics") or {}).get("UnblendedCost") or {})
                amount_value = metric.get("Amount")
                if amount_value in (None, ""):
                    continue

                amount = Decimal(str(amount_value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
                if amount == Decimal("0.00"):
                    continue

                service_name = (group.get("Keys") or ["AWS Other"])[0]
                service, label = cls._normalize_service(service_name)
                source_currency = (metric.get("Unit") or currency).upper()

                items.append(
                    {
                        "category": "infra",
                        "provider": "aws",
                        "service": service,
                        "label": label,
                        "amount": float(amount),
                        "currency": source_currency,
                        "periodMonth": period_key,
                        "metadata": {
                            "region": region,
                            "aws_service_name": service_name,
                        },
                    }
                )
                total += amount

        return AwsCostCollection(
            items=items,
            total=total.quantize(Decimal("0.01"), ROUND_HALF_UP),
            currency=currency.upper(),
        )

    @staticmethod
    def _required_setting(name: str) -> str:
        value = getattr(settings, name, None)
        if value is None or str(value).strip() == "":
            raise AwsCostsConfigurationError(f"{name} is not configured.")
        return str(value).strip()

    @staticmethod
    def _next_month(period_month: date) -> date:
        if period_month.month == 12:
            return date(period_month.year + 1, 1, 1)
        return date(period_month.year, period_month.month + 1, 1)

    @staticmethod
    def _normalize_service(service_name: str) -> tuple[str, str]:
        mapped = AWS_SERVICE_MAP.get(service_name)
        if mapped:
            return mapped

        normalized = (
            service_name.lower()
            .replace("amazon ", "")
            .replace("aws ", "")
            .replace("/", " ")
            .replace("-", " ")
        )
        parts = [part for part in normalized.split() if part]
        slug = "-".join(parts) or "other"
        label_parts = [part.upper() if len(part) <= 3 else part.capitalize() for part in parts]
        label = f"AWS {' '.join(label_parts)}".strip()
        return slug, label
