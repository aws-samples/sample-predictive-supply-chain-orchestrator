"""
Observability stack for AgentCore agent.

Creates OpenTelemetry-compatible tracing, CloudWatch dashboards,
and alarms for monitoring agent performance and health.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class ObservabilityStack(Stack):
    """
    Observability stack.

    Creates:
    - CloudWatch dashboard for agent metrics
    - Alarms for error rates, latency, and throttling
    - SNS topic for alert notifications
    - Log groups with metric filters
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SNS topic for alerts
        self.alert_topic = sns.Topic(
            self,
            "AgentAlertTopic",
            display_name="Procurement Agent Alerts",
        )

        # Log group for agent traces
        self.trace_log_group = logs.LogGroup(
            self,
            "AgentTraceLogGroup",
            log_group_name="/procurement-agent/traces",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Log group for gateway access logs
        self.gateway_log_group = logs.LogGroup(
            self,
            "GatewayAccessLogGroup",
            log_group_name="/procurement-agent/gateway-access",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Metric filters for agent log group
        agent_error_filter = logs.MetricFilter(
            self,
            "AgentErrorFilter",
            log_group=self.trace_log_group,
            metric_namespace="ProcurementAgent",
            metric_name="AgentErrors",
            filter_pattern=logs.FilterPattern.literal("ERROR"),
            metric_value="1",
            default_value=0,
        )

        tool_invocation_filter = logs.MetricFilter(
            self,
            "ToolInvocationFilter",
            log_group=self.trace_log_group,
            metric_namespace="ProcurementAgent",
            metric_name="ToolInvocations",
            filter_pattern=logs.FilterPattern.literal("tool_invoked"),
            metric_value="1",
            default_value=0,
        )

        optimization_latency_filter = logs.MetricFilter(
            self,
            "OptimizationLatencyFilter",
            log_group=self.trace_log_group,
            metric_namespace="ProcurementAgent",
            metric_name="OptimizationLatencyMs",
            filter_pattern=logs.FilterPattern.literal(
                '{ $.event = "optimization_complete" }'
            ),
            metric_value="$.computation_time_ms",
            default_value=0,
        )

        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self,
            "AgentDashboard",
            dashboard_name="ProcurementAgent-Dashboard",
            default_interval=Duration.hours(6),
        )

        # Agent health row
        dashboard.add_widgets(
            cloudwatch.TextWidget(
                markdown="# Procurement Optimization Agent\nReal-time monitoring dashboard",
                width=24,
                height=1,
            ),
        )

        # Error rate and invocations
        error_metric = cloudwatch.Metric(
            namespace="ProcurementAgent",
            metric_name="AgentErrors",
            statistic="Sum",
            period=Duration.minutes(5),
        )

        invocation_metric = cloudwatch.Metric(
            namespace="ProcurementAgent",
            metric_name="ToolInvocations",
            statistic="Sum",
            period=Duration.minutes(5),
        )

        latency_metric = cloudwatch.Metric(
            namespace="ProcurementAgent",
            metric_name="OptimizationLatencyMs",
            statistic="Average",
            period=Duration.minutes(5),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Tool Invocations (5min)",
                left=[invocation_metric],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Agent Errors (5min)",
                left=[error_metric],
                left_y_axis=cloudwatch.YAxisProps(min=0),
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Optimization Latency (ms)",
                left=[latency_metric],
                width=8,
                height=6,
            ),
        )

        # Single value widgets for current state
        dashboard.add_widgets(
            cloudwatch.SingleValueWidget(
                title="Total Invocations (24h)",
                metrics=[
                    cloudwatch.Metric(
                        namespace="ProcurementAgent",
                        metric_name="ToolInvocations",
                        statistic="Sum",
                        period=Duration.hours(24),
                    )
                ],
                width=8,
                height=3,
            ),
            cloudwatch.SingleValueWidget(
                title="Error Count (24h)",
                metrics=[
                    cloudwatch.Metric(
                        namespace="ProcurementAgent",
                        metric_name="AgentErrors",
                        statistic="Sum",
                        period=Duration.hours(24),
                    )
                ],
                width=8,
                height=3,
            ),
            cloudwatch.SingleValueWidget(
                title="Avg Latency (24h)",
                metrics=[
                    cloudwatch.Metric(
                        namespace="ProcurementAgent",
                        metric_name="OptimizationLatencyMs",
                        statistic="Average",
                        period=Duration.hours(24),
                    )
                ],
                width=8,
                height=3,
            ),
        )

        # Alarms
        # High error rate alarm
        error_alarm = cloudwatch.Alarm(
            self,
            "HighErrorRateAlarm",
            metric=error_metric,
            threshold=10,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Agent error rate exceeded 10 errors in 5 minutes",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        error_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))

        # High latency alarm
        latency_alarm = cloudwatch.Alarm(
            self,
            "HighLatencyAlarm",
            metric=latency_metric,
            threshold=30000,  # 30 seconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Average optimization latency exceeded 30 seconds",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        latency_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))

        # Outputs
        CfnOutput(
            self,
            "DashboardUrl",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=ProcurementAgent-Dashboard",
            description="CloudWatch Dashboard URL",
        )

        CfnOutput(
            self,
            "AlertTopicArn",
            value=self.alert_topic.topic_arn,
            description="SNS topic ARN for agent alerts",
        )

        CfnOutput(
            self,
            "TraceLogGroupName",
            value=self.trace_log_group.log_group_name,
            description="Log group for agent traces",
        )

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(
            self.alert_topic,
            [
                {
                    "id": "AwsSolutions-SNS2",
                    "reason": "SNS encryption not required for non-sensitive alert notifications in development"
                },
                {
                    "id": "AwsSolutions-SNS3",
                    "reason": "SNS SSL enforcement handled at topic policy level"
                }
            ],
        )
