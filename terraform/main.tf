terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-west-1"
}

resource "aws_sqs_queue" "care_plan_dlq" {
  name                      = "care-plan-dlq-terraform-demo"
  message_retention_seconds = 1209600  # 14 天
}

resource "aws_sqs_queue" "care_plan_queue" {
  name                       = "care-plan-queue-terraform-demo"
  visibility_timeout_seconds = 360  # 必须 >= generate_careplan Lambda 的 timeout (60s)，推荐 6 倍
  message_retention_seconds  = 86400  # 1 天

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.care_plan_dlq.arn
    maxReceiveCount     = 3
  })
}

# ─── RDS PostgreSQL ───────────────────────────────────────────────

variable "db_password" {
  description = "RDS master user password"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for care plan generation"
  type        = string
  sensitive   = true
}

# 用 default VPC 的子网（us-west-1 有两个 AZ，满足 subnet group 最低要求）
data "aws_subnets" "default" {
  filter {
    name   = "defaultForAz"
    values = ["true"]
  }
}

resource "aws_db_subnet_group" "careplan" {
  name       = "careplan-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

# 允许外部连接 5432 端口（学习阶段；生产环境应限制到固定 IP 或放在私有子网）
resource "aws_security_group" "rds_sg" {
  name        = "careplan-rds-sg"
  description = "Allow PostgreSQL access for careplan"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "careplan" {
  identifier     = "careplan-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro"

  db_name  = "careplan"
  username = "careplan_admin"
  password = var.db_password

  allocated_storage = 20
  storage_type      = "gp2"

  publicly_accessible    = true
  db_subnet_group_name   = aws_db_subnet_group.careplan.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  # 免费套餐要求：单 AZ，不能 Multi-AZ
  multi_az                = false
  backup_retention_period = 7
  skip_final_snapshot     = true

  tags = {
    Name        = "careplan-db"
    Environment = "dev"
  }
}

output "rds_endpoint" {
  description = "RDS connection endpoint (host:port)"
  value       = aws_db_instance.careplan.endpoint
}

output "rds_db_name" {
  value = aws_db_instance.careplan.db_name
}

# ─── Lambda IAM Role ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_exec" {
  name = "careplan-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 允许 create_order Lambda 往 SQS 发消息
resource "aws_iam_role_policy" "lambda_sqs_send" {
  name = "careplan-lambda-sqs-send"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.care_plan_queue.arn
    }]
  })
}

# 允许 generate_careplan Lambda 从 SQS 拉消息（这条 managed policy 包含 Receive/Delete/GetAttributes）
resource "aws_iam_role_policy_attachment" "lambda_sqs_consume" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

# ─── Lambda Functions ─────────────────────────────────────────────

# 三个 Lambda 都要连 RDS，所以把 DB 环境变量提取成 locals 复用
locals {
  db_env = {
    DB_HOST     = aws_db_instance.careplan.address
    DB_PORT     = tostring(aws_db_instance.careplan.port)
    DB_NAME     = aws_db_instance.careplan.db_name
    DB_USER     = aws_db_instance.careplan.username
    DB_PASSWORD = var.db_password
  }
}

resource "aws_lambda_function" "create_order" {
  function_name    = "create-order-tf"
  filename         = "${path.module}/../aws/create_order_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../aws/create_order_lambda.zip")
  handler          = "create_order_lambda.handler"
  runtime          = "python3.11"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30

  environment {
    variables = merge(local.db_env, {
      SQS_QUEUE_URL = aws_sqs_queue.care_plan_queue.url
    })
  }
}

resource "aws_lambda_function" "generate_careplan" {
  function_name    = "generate-careplan-tf"
  filename         = "${path.module}/../aws/process_care_plan_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../aws/process_care_plan_lambda.zip")
  handler          = "process_care_plan_lambda.handler"
  runtime          = "python3.11"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 60

  environment {
    variables = merge(local.db_env, {
      OPENAI_API_KEY = var.openai_api_key
      USE_FAKE_LLM   = "false"
    })
  }
}

resource "aws_lambda_function" "get_order" {
  function_name    = "get-order-tf"
  filename         = "${path.module}/../aws/get_order_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../aws/get_order_lambda.zip")
  handler          = "get_order_lambda.handler"
  runtime          = "python3.11"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30

  environment {
    variables = local.db_env
  }
}

# ─── SQS → generate_careplan 触发 ─────────────────────────────────

resource "aws_lambda_event_source_mapping" "sqs_to_careplan" {
  event_source_arn = aws_sqs_queue.care_plan_queue.arn
  function_name    = aws_lambda_function.generate_careplan.arn
  batch_size       = 1
  enabled          = true

  # 必须在 IAM policy 生效后再创建，否则会报"Lambda 没权限 poll SQS"
  depends_on = [aws_iam_role_policy_attachment.lambda_sqs_consume]
}

output "lambda_names" {
  value = [
    aws_lambda_function.create_order.function_name,
    aws_lambda_function.generate_careplan.function_name,
    aws_lambda_function.get_order.function_name,
  ]
}

# ─── API Gateway (HTTP API) ───────────────────────────────────────

resource "aws_apigatewayv2_api" "careplan" {
  name          = "careplan-api-tf"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.careplan.id
  name        = "$default"
  auto_deploy = true
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.careplan.api_endpoint
}

# ─── API Gateway → Lambda 集成 ────────────────────────────────────

# POST /orders → create_order
resource "aws_apigatewayv2_integration" "create_order" {
  api_id                 = aws_apigatewayv2_api.careplan.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_order.invoke_arn
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "post_orders" {
  api_id    = aws_apigatewayv2_api.careplan.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.create_order.id}"
}

resource "aws_lambda_permission" "apigw_create_order" {
  statement_id  = "AllowAPIGatewayInvokeCreateOrder"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.careplan.execution_arn}/*/*"
}

# GET /orders/{id} → get_order
resource "aws_apigatewayv2_integration" "get_order" {
  api_id                 = aws_apigatewayv2_api.careplan.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_order.invoke_arn
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "get_order_by_id" {
  api_id    = aws_apigatewayv2_api.careplan.id
  route_key = "GET /orders/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_order.id}"
}

resource "aws_lambda_permission" "apigw_get_order" {
  statement_id  = "AllowAPIGatewayInvokeGetOrder"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.careplan.execution_arn}/*/*"
}
