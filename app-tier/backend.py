import boto3
import json
import requests
import sys
import os
import subprocess


S3_OUT_BUCKET_NAME = "1232291504-out-bucket"
REQ_MESSGE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/615299743604/1232291504-req-queue"
RES_MESSGE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/615299743604/1232291504-resp-queue"
REGION_NAME = "us-east-1"
LOCAL_FILE_DIR = "/home/ec2-user/cc_project/data_dir"
MODEL_WEIGHT_PATH = "/home/ec2-user/cc_project/project1/inference/data.pt"


sqs_client = boto3.client("sqs", region_name=REGION_NAME)
ec2_client = boto3.client("ec2", region_name=REGION_NAME)
s3_client = boto3.client("s3", region_name=REGION_NAME)


def get_instance_id():
    INSTANCE_METADATA_URI = "http://169.254.169.254/latest/meta-data/instance-id"

    def get_token():
        TOKEN_URL = "http://169.254.169.254/latest/api/token"
        token_response = requests.put(TOKEN_URL, headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"}, timeout=1)
        token = token_response.text
        return token

    try:
        token = get_token()
        headers = {"X-aws-ec2-metadata-token": token}
        instance_id = requests.get(INSTANCE_METADATA_URI, headers=headers, timeout=1).text
        return instance_id

    except Exception as e:
        print(f"Error getting instance id: {str(e)}")
        return None

def stop_instance():
    instance_id = get_instance_id()
    if instance_id:
        print(f"Stopping instance {instance_id} due to no messages or after processing.")
        try:
            ec2_client.stop_instances(InstanceIds=[instance_id], Force=True)
        except Exception as e:
            print(f"Error stopping instance: {str(e)}")
    else:
        print("Instance ID not found. Exiting.")
    sys.exit(0)


def downloadFile(bucket_name, file_name):
    try:
        s3_client.download_file(bucket_name, file_name, os.path.join(LOCAL_FILE_DIR, file_name))
    
    except Exception as e:
        print(f"Error downloading file from S3: {e!r}")
        raise


def deleteFile(file_name):
    try:
        os.remove(os.path.join(LOCAL_FILE_DIR, file_name))
    except Exception as e:
        print(f"{e!r}")


def get_prediction(file_name):
    file_path = os.path.join(LOCAL_FILE_DIR, file_name)

    process_result = subprocess.run(["python3", "face_recognition.py", file_path, MODEL_WEIGHT_PATH], capture_output=True, text=True)
    output_lines = process_result.stdout.strip().split("\n")
    result = output_lines[-2]

    return result


def copy_file_to_output_bucket(input_bucket, file_name, output_bucket):
    copy_resource = {
        'Bucket': input_bucket,
        'Key': file_name
    }

    s3_client.copy(copy_resource, output_bucket, file_name)


if __name__ == "__main__":
    while True:
        response = sqs_client.receive_message(
            QueueUrl=REQ_MESSGE_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=0,
            MessageAttributeNames=['All']
        )
        
        messages = response.get('Messages', [])
        if not messages:
            print("No messages found. Stopping instance immediately.")
            break
        
        message = messages[0]

        try:
            data = json.loads(message['body'])
        except json.JSONDecodeError as e:
            print(f"Error decoding message: {e!r}")
            sqs_client.delete_message(
                QueueUrl=REQ_MESSGE_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
        
        downloadFile(data["bucket_name"], data["file_name"])

        result = get_prediction(data["file_name"])

        copy_file_to_output_bucket(data["bucket_name"], data["file_name"], S3_OUT_BUCKET_NAME)

        res_queue_message = {
            "request_id": data["request_id"],
            "result": result
        }

        try:
            sqs_client.send_message(
                QueueUrl=RES_MESSGE_QUEUE_URL,
                MessageBody=json.dumps(res_queue_message)
            )
            sqs_client.delete_message(
                QueueUrl=REQ_MESSGE_QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )

        except Exception as e:
            print(f"{e!r}")
        

        deleteFile(data["file_name"])
    
    stop_instance()

    
    