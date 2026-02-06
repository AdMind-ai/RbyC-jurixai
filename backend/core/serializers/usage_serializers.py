from rest_framework import serializers

from core.models.usage import UsageSubTool, UsageTool


class ToolBreakdownSubItemSerializer(serializers.Serializer):
    cost = serializers.FloatField()
    count = serializers.IntegerField()


class ToolBreakdownSerializer(serializers.Serializer):
    cost = serializers.FloatField()
    count = serializers.IntegerField()
    subItems = serializers.DictField(
        child=ToolBreakdownSubItemSerializer(), required=False
    )


class UserBreakdownSerializer(serializers.Serializer):
    userId = serializers.IntegerField()
    userName = serializers.CharField()
    userEmail = serializers.EmailField()
    role = serializers.CharField()
    isCompanyAdmin = serializers.BooleanField()
    totalCost = serializers.FloatField()
    costs = serializers.DictField(child=serializers.FloatField())
    counts = serializers.DictField(child=serializers.IntegerField())
    subToolCosts = serializers.DictField(
        child=serializers.DictField(child=serializers.FloatField()),
        required=False,
    )
    subToolCounts = serializers.DictField(
        child=serializers.DictField(child=serializers.IntegerField()),
        required=False,
    )


class UsageReportSerializer(serializers.Serializer):
    month = serializers.CharField()
    monthLabel = serializers.CharField()
    currency = serializers.CharField()
    totalCost = serializers.FloatField()
    totalRequests = serializers.IntegerField()
    toolUsage = serializers.DictField(child=ToolBreakdownSerializer())
    userBreakdown = UserBreakdownSerializer(many=True)


class UsageMonthOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    totalCost = serializers.FloatField()


class UsageManualRecordSerializer(serializers.Serializer):
    tool = serializers.ChoiceField(choices=UsageTool.choices)
    subTool = serializers.ChoiceField(
        choices=UsageSubTool.choices, required=False, allow_null=True
    )
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=0.0001, default=1
    )
    metadata = serializers.JSONField(required=False, default=dict)
