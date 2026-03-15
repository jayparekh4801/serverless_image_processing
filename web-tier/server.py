from flask import Flask, request, jsonify
import boto3
import threading
import time
import uuid
import json

app = Flask(__name__)

S3_BUCKET_NAME = "1232291504-in-bucket"
SIMPLE_DB_DOMAIN = "1232291504-simpleDB"
REQ_MESSGE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/615299743604/1232291504-req-queue"
RES_MESSGE_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/615299743604/1232291504-resp-queue"
REGION_NAME = "us-east-1"

s3_client = boto3.client("s3", region_name=REGION_NAME)
simpledb_client = boto3.client("sdb", region_name=REGION_NAME)
sqs_client = boto3.client("sqs", region_name=REGION_NAME)

all_responses = {}

thread_lock = threading.Lock()


def deposit_result_to_responses():
    while True:
        response = sqs_client.receive_message(
            QueueUrl=RES_MESSGE_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=0
        )

        if "Messages" in response:
            message = response["Messages"][0]
            body = json.loads(message["Body"])
            result = body.get("result")
            request_id = body.get("request_id")
            if request_id:
                with thread_lock:
                    all_responses[request_id] = result
                    print("in lock:- ", all_responses[request_id])

                sqs_client.delete_message(
                    QueueUrl=RES_MESSGE_QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"]
                )


def upload_to_s3_deposit_message(file_obj, file_name, request_id):
    try:
        s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, file_name)
        send_sqs_message(S3_BUCKET_NAME, file_name, request_id)
    except Exception as e:
        return f"{e!r}"

def send_sqs_message(bucket_name, file_name, request_id):
    try:
        message = {
            "request_id": request_id,
            "bucket_name": bucket_name,
            "file_name": file_name
        }
        sqs_client.send_message(
            QueueUrl=REQ_MESSGE_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
    except Exception as e:
        print(f"Error sending SQS message: {e}")

# Function to poll SQS for a response
def poll_sqs_for_response(request_id):
    while True:
        if request_id in all_responses.keys():
            with thread_lock:
                result = all_responses[request_id]
                print(result)
                all_responses.pop(request_id)
            return result
        time.sleep(0.02)
# Flask route for file upload
@app.route('/', methods=['POST'])
def upload_file():

    file = request.files['inputFile']
    file_name = file.filename
    request_id = str(uuid.uuid4())

    upload_thread = threading.Thread(target=upload_to_s3_deposit_message, args=(file, file_name, request_id))
    upload_thread.start()

    # Wait for a response from the response SQS queue
    result = poll_sqs_for_response(request_id)
    print(result)
    return f"{file_name.split('.')[0]}:{result}"

# Run Flask app with threading enabled
if __name__ == '__main__':
    threading.Thread(target=deposit_result_to_responses, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)