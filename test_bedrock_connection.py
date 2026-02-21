#!/usr/bin/env python3
"""
Test AWS Bedrock connection and model access
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_bedrock_access():
    """Test AWS Bedrock connection and model access."""

    aws_region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv("BEDROCK_MODEL", "anthropic.claude-sonnet-4-5-20250929-v1:0")

    print("=" * 80)
    print("AWS Bedrock Connection Test")
    print("=" * 80)
    print(f"Region: {aws_region}")
    print(f"Model: {model_id}")
    print()

    try:
        # Create Bedrock client
        print("Step 1: Creating Bedrock client...")
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=aws_region
        )
        print("✅ Bedrock client created successfully")
        print()

        # Test simple converse call
        print("Step 2: Testing model access with simple query...")
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Say 'Hello, Portfolio Assistant is working!' and nothing else."}]
                }
            ],
            inferenceConfig={
                "temperature": 0.0,
                "maxTokens": 100
            }
        )

        # Extract response
        if response and "output" in response:
            output_message = response["output"]["message"]
            text_content = []
            for content_block in output_message.get("content", []):
                if "text" in content_block:
                    text_content.append(content_block["text"])

            response_text = "\n".join(text_content)
            print("✅ Model response received:")
            print(f"   {response_text}")
            print()
            print("=" * 80)
            print("SUCCESS: AWS Bedrock is configured correctly!")
            print("Your Portfolio Assistant should now work properly.")
            print("=" * 80)
            return True
        else:
            print("❌ Unexpected response format")
            return False

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        print(f"❌ AWS Client Error: {error_code}")
        print(f"   Message: {error_message}")
        print()

        if error_code == "ValidationException":
            print("SOLUTION:")
            if "channel program account" in error_message:
                print("  Your AWS account type doesn't have access to this model.")
                print("  Try one of these ACTIVE models instead:")
                print("    - anthropic.claude-3-haiku-20240307-v1:0 (fast, low-cost)")
                print("    - anthropic.claude-3-5-haiku-20241022-v1:0 (good balance)")
            elif "Access denied" in error_message or "not authorized" in error_message:
                print("  You need to request model access in AWS Console:")
                print("  1. Go to AWS Console → Amazon Bedrock")
                print("  2. Navigate to 'Model access'")
                print("  3. Request access to Claude models")
        elif error_code == "AccessDeniedException":
            print("SOLUTION:")
            print("  1. Check your AWS credentials: aws sts get-caller-identity")
            print("  2. Ensure your IAM user/role has bedrock:InvokeModel permission")
        else:
            print("SOLUTION:")
            print("  Check the error message above and verify:")
            print("  1. AWS credentials are configured correctly")
            print("  2. You have Bedrock access in your region")
            print("  3. Model access is enabled in AWS Console")

        return False

    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}")
        print(f"   {str(e)}")
        print()
        print("SOLUTION:")
        print("  1. Verify AWS credentials: aws configure list")
        print("  2. Check network connectivity")
        print("  3. Ensure boto3 is installed: pip install boto3")
        return False

if __name__ == "__main__":
    success = test_bedrock_access()
    sys.exit(0 if success else 1)
