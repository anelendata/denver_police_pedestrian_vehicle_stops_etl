# Denver Police Pedestrian Vehicle Stops ETL

.. image:: https://img.shields.io/pypi/v/denver_police_pedestrian_vehicle_stops_etl.svg
        :target: https://pypi.python.org/pypi/denver_police_pedestrian_vehicle_stops_etl

.. image:: https://img.shields.io/travis/daigotanaka/denver_police_pedestrian_vehicle_stops_etl.svg
        :target: https://travis-ci.org/daigotanaka/denver_police_pedestrian_vehicle_stops_etl

.. image:: https://readthedocs.org/projects/denver-police-pedestrian-vehicle-stops-etl/badge/?version=latest
        :target: https://denver-police-pedestrian-vehicle-stops-etl.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

ELT pipeline from Denver Police Pedestrian Stops and Vehicle Stops dataset

* Free software: Apache Software License 2.0
* Documentation: https://denver-police-pedestrian-vehicle-stops-etl.readthedocs.io.


## Introduction

Write what it does...

## File structure

```
.
├── aws_utils: (submodule) Convenience Python module for boto3 commands
├── Dockerfile: A Dockerfile that wraps the code as a single command
├── etl_utils: (submodule) Misc. tools for ETL tasks
├── fgops: (submodule) Fargate operation commands
├── impl.py: Implementation of the task
├── README.md: This file
├── requirements.txt: List of required Python modules
├── runner.py: Entrypoint for the task
└── ssm_params.txt: List of AWS SSM Parameters to be retrieved from runner.py
```

## Fargate deployment via fgops

The repository refers to [fgops](https://github.com/anelendata/fgops) as a submodule.
fgops are a set of Docker and Cloudformation commands to build and push the docker images to
ECR, create the ECS task definition, and schedule the events to be executed via Fargate.

fgops requires an environment file. See ____.env____fg as an example. In this document, any variables
defined in the environment file is referred with as <VAR_NAME>.

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
pip install -r requirements.txt
```

Define AWS credentials as environment variables:

```
export AWS_ACCESS_KEY_ID=<key>
export AWS_SECRET_KEY=<secret>
```

### AWS SSM Parameters

The configurations including the secrets to access source and destination servers 
are managed with
[AWS SSM Parameters](https://console.aws.amazon.com/systems-manager/parameters).

You need to list the parameter names in ssm_params.txt. Then the parameters must 
be stored in SSM with the parameter name prefix <STACK_NAME>_.
The values are retrieved during the initialization.

A convenience function to upload the parameters from a local JSON file is
provided. To do this, first create a JSON file to define the parameter name and
value:

For example,

```
{
  "tap_command": "tap_bigquery",
  "tap_args": "--config .env/tap_config.json --catalog ./catalog/default_catalog.json --start_date '{start_at}' --end_date '{end_at}'",
  "target_command": "target_pardot",
  "target_args": "--config .env/target_config.json",
  "tap_config": "{\"streams\": [{\"name\": \"schema_name\",}]}",
  "target_config": "{\"api_key\": \"xxxx\", \"secret\": \"xxxx\"}",
}
```

Note that you can embed JSON by escaping quotation character as in the above example.
This is extensively used in singer.io use cases to write out the tap/target configuration
files read from SSM parameters.

When kinoko.io is used with singer.io, these parameters are reserved:

- tap/target_command: Define the command name for tap/target.
- tap/target_args: A string of whole tap/target command arguments.
- tap/target_config: An escaped JSON string to define tap/target config file.
- google_client_secret: An escapted JSON of the client secret file of a
  [GCP service account](https://cloud.google.com/kubernetes-engine/docs/tutorials/authenticating-to-cloud-platform)


After creating the JSON file, run this convenience function to upload the value 
to SSM:

```
python runner.py put_ssm_parameters -d '{"param_file":"<path_to_JSON>"}'
```

You can check the currently stored values by dump command:

```
python runner.py dump_ssm_parameters -d '{"param_file":"./ssm_params.txt"}'
```

(Make sure ./ssm_params.txt reflect the parameter names.)

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

Build the image:

```
./fgops/docker-task.sh build 0.1 .env_fg 
```

Note: "0.1" here is the image version name. You decide what to put there.

```
docker run --env-file <env_file_name> <IMAGE_NAME>
```

You need to define

```
STACK_NAME
AWS_ACCESS_KEY_ID
AWS_SECRET_KEY
AWS_REGION
```

in <env_file_name> file.

By default, Dockerfile is configured to execute `python runner.py default`.

Or you can specify the function to run together with the data via environment
variable:

```
COMMAND=show_commands
DATA={"start_at":"1990-01-01T00:00:00","end_at":"2030-01-01T00:00:00"}
```

...that would be picked up by Docker as

```
CMD python3 runner.py ${COMMAND:-default} -d ${DATA:-{}}
```

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
