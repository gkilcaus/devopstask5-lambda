import boto3
import os
from aws_lambda_powertools import Tracer, Logger
from boto3.dynamodb.conditions import Attr
from botocore.client import Config
from threading import Thread
from botocore.exceptions import ClientError
import wikiquote

tracer = Tracer(service="devops5")
logger = Logger(
    service="devops5", level=os.environ.get("LOG_LEVEL", "INFO")
)

# this will prevent long timeouts
BOTO3_CONFIG = Config(connect_timeout=5, retries={"max_attempts": 0})
VALID_ACTIONS = ["start","stop","test"]

STARTABLE_CODES = [80]
STOPPABLE_CODES = [0,16,32,64]

ec2client = boto3.client('ec2', config=BOTO3_CONFIG)

@tracer.capture_method
def get_regions(ec2_client):
    """
  Return all AWS regions
  """

    regions = []

    try:
        aws_regions = ec2_client.describe_regions()["Regions"]
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
        raise

    else:
        for region in aws_regions:
            regions.append(region["RegionName"])

    return regions

@tracer.capture_method
def get_instances(ec2_client):
    """
  Returns all EC2 instances in specified region
  """

    instances = []

    try:
        ec2_response = ec2_client.describe_instances(MaxResults=1000)
    except ClientError as e:
        logger.error(e.response["Error"]["Message"])
        raise

    else:
        for reservation in ec2_response["Reservations"]:
            for instance in reservation["Instances"]:
                # Looking for Environment Tag with value not equal to PRD/PRODUCTION
                if "Tags" in instance:
                    prd_tag = False
                    for tag in instance["Tags"]:
                        if tag['Key'] == "Environment" and (tag["Value"].lower() == "prd" or tag["Value"].lower() == "production"):
                            prd_tag = True
                    if not prd_tag:
                        instances.append(instance)
                else:
                    instances.append(instance)
    return instances

@tracer.capture_method
def process_instances(region, action):
    """
  Processes action for given region
  """
    logger.info(
        f"Region {region} started processing.."
    )
    ec2client = boto3.client('ec2', region_name=region, config=BOTO3_CONFIG)

    instances = get_instances(ec2client)


    for instance in instances:
        if action == "start":
            if instance['State']['Code'] in STARTABLE_CODES:
                try:
                    logger.info(
                        f"Starting instance {instance['InstanceId']} in {region}.."
                    )
                    ec2client.start_instances(
                        InstanceIds=[
                            instance["InstanceId"]
                        ]
                    )
                except ClientError as e:
                    logger.error(
                        f"Starting instance {instance['InstanceId']} in {region} failed: {e.response['Error']['Message']}"
                    )
                    pass
        elif action == "stop":
            if instance["State"]["Code"] in STOPPABLE_CODES:
                try:
                    logger.info(
                        f"Stopping instance {instance['InstanceId']} in {region}.."
                    )
                    ec2client.stop_instances(
                        InstanceIds=[
                            instance["InstanceId"]
                        ]
                    )
                except ClientError as e:
                    logger.error(
                        f"Stopping instance {instance['InstanceId']} in {region} failed: {e.response['Error']['Message']}"
                    )
                    pass
        elif action == "test":
            if instance["State"]["Code"] in STOPPABLE_CODES:
                try:
                    logger.info(
                        f"Stopping instance {instance['InstanceId']} in {region}.."
                    )
                    ec2client.stop_instances(
                        InstanceIds=[
                            instance["InstanceId"]
                        ],
                        DryRun=True
                    )
                except ClientError as e:
                    logger.error(
                        f"Testing Stopping instance {instance['InstanceId']} in {region} failed: {e.response['Error']['Message']}"
                    )
                    raise RuntimeError(
                        "Test Fail"
                    )
    logger.info(
        f"Region {region} processed."
    )


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    
    try:
        action = event['action']
    except:
        raise RuntimeError(
            "Missing parameter: action"
        )
    
    if action not in VALID_ACTIONS:
        raise RuntimeError(
            f"Invalid action: {action}"
        )

    aws_regions = get_regions(ec2client)

    threads = []

    for region in aws_regions:        
        thread = Thread(target=process_instances, args=(region, action))
        threads += [thread]
        thread.start()
    
    for thread in threads:
        thread.join()

    return wikiquote.quote_of_the_day()[0]