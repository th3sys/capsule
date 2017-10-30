CAPSULE - MARKET DATA ADAPTER
================================

This is an implementation of the TWS Market Data Adapter.

.. image:: https://api.travis-ci.org/th3sys/capsule.svg?branch=master
 :target: https://travis-ci.org/th3sys/capsule/

Features
========
TWS Market Data Adapter is implemented using Interactive Brokers API.

- Dockerfile for headless environment setup
- Interactive Brokers Gateway
- Amazon EC2 Container Service setup
- AWS DynamoDB tables

Usage
=====
Follow these steps the run IB gateway in a docker container on AWS EC2 Container Services platform.
Subscribe to the securities from the Securities table and push the quotes back to the Quotes table in DynamoDB.

1. To use Capsule create Securities and Quotes tables in DynamoDB using the scripts ``create_tables.py`` and ``python push_items.py``.

2. Create AWS CloudWatch Log Group ``/aws/docker/Capsule``

3. Rename config.default.aws to config.aws and provide your role, access id, etc.

4. Rename credentials.default.aws to credentials.aws and provide your role, access id, etc.

5. Build docker image using the dockerfile provided, create ``capsule`` repository in your EC2 Container Services AWS account

.. code:: bash

    #Build image
    docker build -t capsule .

    #Create repo
    aws ecr create-repository --repository-name capsule

6. Tag and push the image in the repo

.. code:: bash

    #Tag repo
    docker tag capsule accountid.dkr.ecr.us-east-1.amazonaws.com/capsule

    #Get login and push
    aws ecr get-login --no-include-email --region us-east-1
    docker push accountid.dkr.ecr.us-east-1.amazonaws.com/capsule

7. In AWS EC2 Container Services create a task definition from the DockerTask.json file

8. In AWS EC2 Container Services create a Cluster and Container service to run the task definition on a Container instance

9. Deploy the ``nightwatch.py`` script in AWS Lambda function to monitor and start EC2 Container instance

*This product includes software developed by Interactive Brokers (https://www.interactivebrokers.com/).*
*The steps in the Dockerfile have been lifted from http://www.algoeye.com/blog/running-ib-gateway-on-vps/.*