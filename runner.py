import argparse, datetime, json, logging, os, sys

import impl


logging.basicConfig(stream=sys.stdout,
                    format="%(asctime)s - " + str(__name__) + " - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def read_parameters_from_file(parameter_file):
    with open(parameter_file, "r") as f:
        params = json.load(f)
    for param in params:
        os.environ[param] = params[param]


def read_ssm_parameters():
    if not os.path.exists("./ssm_params.txt"):
        return
    from aws_utils import ssm
    for param in [line.rstrip('\n') for line in open("ssm_params.txt", "r")]:
        ssm.set_env_var_from_ssm(os.environ.get("STACK_NAME"), param)


def put_ssm_parameters(param_file):
    if not os.path.exists(param_file):
        raise ValueError("You need to provide a parameter JSON file.")
    from aws_utils import ssm
    with open(param_file, "r") as f:
        params = json.load(f)
    for key in params.keys():
        ssm.put_parameter(os.environ.get("STACK_NAME"), key, params[key])


def dump_ssm_parameters(param_file, format_="json"):
    if not os.path.exists(param_file):
        raise ValueError("You need to provide a parameter file.")
    from aws_utils import ssm
    project = os.environ.get("STACK_NAME")
    params = {}
    for key in [line.rstrip('\n') for line in open(param_file, "r")]:
        try:
            param = ssm.get_parameter(project, key)
        except Exception as e:
            print(e)
            print("...while reading %s_%s" % (project, key))
            return
        value = param["Parameter"]["Value"]
        params[key] = value
    string = json.dumps(params, indent=2)
    # string = json.dumps(params).replace("\\n", "\n").replace("\\\"", "\"").replace("\\", "")
    print(string)


def run(command, data, parameter_file=None):
    """
    """
    if command == "put_ssm_parameters":
        put_ssm_parameters(data["param_file"])
        return
    if command == "dump_ssm_parameters":
        dump_ssm_parameters(data["param_file"])
        return


    # Search in impl.py for available commands
    commands = dict()
    impl_obj = dir(impl)
    for name in impl_obj:
        if name[0] == "_":
            continue
        obj = getattr(impl, name)
        if callable(obj):
            commands[name] = obj

    if command not in commands:
        raise ValueError("Invalid command: %s\nAvailable commands are %s" %
                         (command, [x for x in commands.keys()]))

    logger.info("Running " + command)

    if parameter_file:
        if not os.path.isfile(parameter_file):
            raise ValueError(parameter_file + " not found.")
        logger.info("Reading parameters from file: " + parameter_file)
        read_parameters_from_file(parameter_file)
    else:
        logger.info("Reading parameters from SSM.")
        read_ssm_parameters()
    start = datetime.datetime.utcnow()
    logger.info("Job started at " + str(start))

    # Run the command
    commands[command](data)

    end = datetime.datetime.utcnow()
    logger.info("Job ended at " + str(end))
    duration = end - start
    logger.info("Processed in " + str(duration))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ETL.")
    parser.add_argument("command", type=str, help="command")
    parser.add_argument("-d", "--data", type=str, default="{}", help="Data required for the command as a JSON string")
    parser.add_argument("-p", "--parameter_file", type=str, default=None, help="Read parameters from file instead from AWS SSM")
    args = parser.parse_args()
    command = args.command
    data_json = args.data
    logger.debug(data_json)
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        data = json.loads(data_json[0:-1])
    logger.info("Running " + command + " data:" + str(data))
    run(command, data, args.parameter_file)
