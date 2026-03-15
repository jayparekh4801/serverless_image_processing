Face Recognition Pipeline with Custom Auto-Scaling
This project implements a scalable, decoupled face recognition system built on AWS. Unlike standard managed auto-scaling solutions, this architecture utilizes a custom-built controller within the web tier to dynamically manage a pool of preconfigured EC2 instances, manually matching compute capacity to real-time SQS queue depth.

Architecture Overview
The system is designed to handle high-concurrency requests by separating the ingestion, orchestration, processing, and retrieval layers into distinct, asynchronous components.

Core Components
Web Tier: Acts as the entry point, handling API requests, managing the S3 upload process, and hosting the custom orchestration logic.

Request Queue (SQS): Decouples the web tier from the processing power, holding job metadata and S3 locations.

Custom Controller: A logic layer on the web tier that monitors SQS depth via AWS CloudWatch metrics and uses the AWS EC2 SDK to programmatically start/stop preconfigured instances.

Worker Tier (EC2): A pool of preconfigured instances (AMIs) that are maintained in a stopped state until needed. When started, they pull jobs, execute the recognition algorithm, and shut down.

Storage (S3): Used for persistent storage of input images and processed, annotated results.

Response Queue (SQS): Facilitates the asynchronous return of results back to the web tier for the final user response.

System Workflow
Ingestion: The frontend sends an image to the Web Tier. The Web Tier uploads the image to an S3 bucket and generates a unique Request ID.

Queueing: The Web Tier pushes a message containing the Request ID and S3 URI (e.g., s3://input-bucket/image_id.jpg) to the Request SQS.

Orchestration: The Web Tier’s controller checks the depth of the Request SQS. It programmatically starts the required number of stopped EC2 workers to handle the current load.

Processing:

The activated EC2 worker polls the Request SQS for a job.

It downloads the image from S3 and runs the face recognition algorithm.

It deletes the original image from the input bucket and saves the recognized, annotated image to the output bucket.

It pushes the recognition result and metadata to the Response SQS.

The instance then programmatically stops itself to conserve resources.

Retrieval: The Web Tier continuously polls the Response SQS. Once a matching Request ID is found, the recognition result is returned to the client.

Technologies Used
Cloud Platform: AWS (EC2, S3, SQS, CloudWatch)

Web Tier Development: [e.g., Python (Flask/Django)]

AWS SDK (for programmatic control): [e.g., Boto3 for Python]

Face Recognition Library: [e.g., face_recognition (Python), OpenCV]

Key Features
Custom Load Balancing: Custom-built logic to spawn EC2 instances based on specific queue thresholds, rather than generic CPU or memory usage.

Decoupled Architecture: Asynchronous communication via SQS ensures the web tier remains responsive, preventing input processing bottlenecks.

Cost Efficiency: Processing nodes only run while there is an active queue depth and stop immediately after task completion, optimizing compute spend.

Integrated S3 Lifecycle: Raw input images are automatically cleaned up post-processing to manage storage costs.
