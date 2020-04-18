# Denver Police Pedestrian Vehicle Stops ETL

ELT pipeline from Denver Police Pedestrian Stops and Vehicle Stops dataset

* Free software: Apache Software License 2.0
* Documentation: https://denver-police-pedestrian-vehicle-stops-etl.readthedocs.io.


## Introduction

This is a public project to showcase to perform ELT (extract, load, transform) 
[the city of Denver Police Pedestrian Stops and Vehicle Stops dataset](https://www.denvergov.org/opendata/dataset/city-and-county-of-denver-police-pedestrian-stops-and-vehicle-stops)

The data is loaded to Google BigQuery.

This ETL process follows kinoko.io, a template for creating a docker image
that runs ETL based on singer.io. The ETL process is intended to be deployed
to AWS Fargate.

### Extraction and Load

Extraction and Load are done through singer.io framework.
The EL process is docker-containerized and deployed to AWS Fargate.
The containerization is based on [ANELEN]'s kinoko.io framework.

### Transformation

Transformation takes place after the data is loaded to BigQuery.
The transformation is defined as SQL statement and managed by 
[dbt](https://getdbt.com)

### Data format and REST API

The data follows arcGIS format. The API server is an
[arcGIS feature-layer](https://developers.arcgis.com/labs/rest/query-a-feature-layer/)

## File structure

```
.
├── README.md: This file
├── Dockerfile: A Dockerfile that wraps the code as a single command
├── aws_utils: (submodule) Convenience Python module for boto3 commands
├── etl_utils: (submodule) Misc. tools for ETL tasks
├── fgops: (submodule) Fargate operation commands
├── impl.py: Implementation of the task
├── requirements.txt: List of required Python modules
├── runner.py: Entrypoint for the task
├── ssm_params.txt: List of AWS SSM Parameters to be retrieved from runner.py
└── dbt: dbt project directory
```

## Executing locally

### Install

Prerequisites:

- AWS CLI
- Python 3.6 or later
- Docker

Create Python virtual environment and install the modules:

```
python3 -m venv ./venv
source venv/bin/activate
pip install wheel
pip install -e ./tap_xxxx
pip install -e ./target_xxxx
pip install -r requirements.txt
```
(Replace xxxx with your tap and target names found in this repository)


### Configure tap & target commands

Configure singer.io tap & target commands by referring docs of the installed
tap and target.

The recommendation is to create .env directory and store the following configuration
files with the exact name:

- tap_config.json
- target_config.json
- (optional) client_secret.json  (Google Cloud Platform key JSON file)

After tap & target command is working locally, run:

```
./bin/gen_ssm_param_json .env > .env/ssm_param_values.json
```

`.env/ssm__param_values.json` will be used in the next section.

### AWS configuration

Create a programmatic access user with an appropriate role with AWS IAM.
The user should have a sufficient permissions to run the process. At minimum,
AmazonSSMReadOnlyAccess. Obtain the access keys and define AWS credentials and 
region as environment variables:

```
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_KEY=<secret>
export AWS_REGION=<region_name>
```

Also define STACK_NAME. This is used as the stack name for cloudformation
later, and also act as a "name space" for the SSM Parameters explained in
the next section:

```
export STACK_NAME=<some-stack-name>
```

#### AWS SSM Parameters

[AWS SSM Parameter Store](https://console.aws.amazon.com/systems-manager/parameters)
is used to pass the tap & target configurations and other secrets such as
GCP key. In SSM, the parameters are stored in <STACK_NAME>_<param_name> format.

A convenience function to upload the parameters from a local JSON file is
provided. We have created such a JSON file in the previous step (`.env/ssm_param_values.json`)

(Take a look inside the JSON file)

Note that you can embed JSON by escaping quotation character as in the above example.
This is extensively used in singer.io use cases to write out the tap/target configuration
files read from SSM parameters.

When kinoko.io is used with singer.io, these parameters are reserved:

- tap/target_command: Define the command name for tap/target.
- tap/target_args: A string of whole tap/target command arguments.
- tap/target_config: An escaped JSON string to define tap/target config file.
- google_client_secret: An escapted JSON of the client secret file of a
  [GCP service account](https://cloud.google.com/kubernetes-engine/docs/tutorials/authenticating-to-cloud-platform)

Run this convenience function to upload the value to SSM:

```
python runner.py put_ssm_parameters -d '{"param_file":"<path_to_JSON>"}'
```

You can check the currently stored values by dump command:

```
python runner.py dump_ssm_parameters -d '{"param_file":"./ssm_params.txt"}'
```

You also need to list the parameter names in ssm_params.txt that looks like:

```
tap_command
tap_args
tap_config
target_command
target_args
target_config
google_client_secret
```

(TODO: query SSM parameters with STACK_NAME so that we don't need to prepare ssm_params.txt)

### Run

To locally run the ETL, do:

```
python runner.py default -d '{"venv":"./venv"}'
```

`default` is a function defined in `impl.py`. Any function defined in `impl.py` can be invoked
in the same manner.

```
python runner.py show_commands -d '{"view": "<view_name>"}'
```

In the above example, the show_commands function expects a JSON string as a parameter that contains
view.

## Execute in a Docker container

### Fargate deployment via fgops

The repository refers to [fgops](https://github.com/anelendata/fgops) as a submodule.
fgops are a set of Docker and CloudFormation commands to build and push the docker images to
ECR, create the ECS task definition, and schedule the events to be executed via Fargate.

fgops requires an environment file. See [_env_fg](./fgops/_.env_fg) as an example. 

### Build the image

```
./fgops/docker-task.sh build 0.1 .env_fg 
```

Note: "0.1" here is the image version name. You decide what to put there.

```
docker run --env-file <env_file_name> <IMAGE_NAME>
```

Like the way you defined when running locally, you need to define

```
STACK_NAME
AWS_ACCESS_KEY_ID
AWS_SECRET_KEY
AWS_REGION
```

in <env_file_name> file to pass on to Docker contianer.

By default, Dockerfile is configured to execute `python runner.py default`.

Or you can specify the function to run together with the data via additional
environment variables in <env_file_name>:

```
COMMAND=show_commands
DATA={"start_at":"1990-01-01T00:00:00","end_at":"2030-01-01T00:00:00"}
```

...that would be picked up by Docker just as

```
CMD python3 runner.py ${COMMAND:-default} -d ${DATA:-{}}
```

See [Dockerfile](./Dockerfile) for details.

## Pushing the image and create the ECS task

Note: Please see fgops instructions for the details.

Push the image to the ECR:

```
./fgops/docker-task.sh push 0.1 .env_fg
```

Create the cluster and the task via Cloudformation:

```
./fgops/cf_create_stack.sh 0.1 .env_fg
```

Check the creation on [Cloudformation](https://console.aws.amazon.com/cloudformation/home)

## Additional permissions

Farget TaskRole will be created under the name: <STACK_NAME>-TaskRole-XXXXXXXXXXXXX
Additional AWS Policy may be attached to the TaskRole depends on the ECS Task.

## Scheduling via Fargate

```
./fgops/events_schedule_create test 1 '0 0 * * ? *' .env_fg
```

The above cron example runs the task at midnight daily.

Check the execution at AWS Console:

https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters

...and Cloudwatch logs:

https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logs:

## How to update the stack

1. Make code change and test locally.
2. Build docker image with ./fgops/docker-task.sh
3. Test docker execution locally.
4. Push docker image with ./fgops/docker-task.sh
5. Update stack:

```
./fgops/cf_update_stack.sh 0.1 .env_fg
```

6. Unschedule the Fargate task:

```
./fgops/events_schedule_remove 1 .env_fg
```

7. Reschedule the task:

```
./fgops/events_schedule_create 1 '0 0 * * ? *' .env_fg
```

## Credits

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
