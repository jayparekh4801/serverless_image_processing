import boto3

REGION_NAME = "us-east-1"
REQ_MESSGE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/615299743604/1232291504-req-queue"
sqs_client = boto3.client("sqs", region_name=REGION_NAME)
ec2_client = boto3.client("ec2", region_name=REGION_NAME)

TOTAL_INSTANCES = 15

def get_instances_status():
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': ['app-tier-instance-*']
            }
        ]
    )

    running = []
    stopped = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            state = instance['State']['Name'] 


            if state == "running":
                running.append(instance_id)
            elif state == "stopped":
                stopped.append(instance_id)

    return running, stopped


def get_req_queue_length():
    attributes = sqs_client.get_queue_attributes(
        QueueUrl=REQ_MESSGE_QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(attributes['Attributes']['ApproximateNumberOfMessages'])


def start_required_instances():

    running, stopped = get_instances_status()

    number_of_requests_in_queue = get_req_queue_length()

    if len(running) < number_of_requests_in_queue:

        number_of_additional_instaces = min(number_of_requests_in_queue - len(running), len(stopped))

        instances = stopped[:number_of_additional_instaces]

        if len(instances) < 1:
            print("No need to start additional instances.")
            return

        ec2_client.start_instances(InstanceIds=instances)
        print("Started instances:", instances)
    else:
        print("No Need To Scale Up")


if __name__ == "__main__":
    while True:
        start_required_instances()