import datetime, json, logging, os, shlex, sys
import attr
import subprocess

import etl_utils as etl

logger = logging.getLogger(__name__)


def _get_params(start_at=None, end_at=None):
    params = etl.get_python_info(__name__)
    if start_at:
        params.update({"start_at": start_at})
    if end_at:
        params.update({"end_at": end_at})

    return params


def _get_env():
    work_dir = os.getcwd()
    env = {"PYTHONPATH": ":".join(sys.path)}
    google = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if google:
        env.update({"GOOGLE_APPLICATION_CREDENTIALS": google})

    return env


def _get_command_string(command, argstring, params, venv=None):
    """
    Available params:
    - python
    - code_dir
    - work_dir
    """
    command = command + " " + argstring
    command = command.format(**params)

    if venv:
        params.update({"venv": venv})
        command = '/bin/bash -c "source {code_dir}/{venv}/bin/activate && '.format(**params) + command + '"'

    return command


def _get_singer_commands(start_at=None, end_at=None, venv=None):
    params = _get_params(start_at, end_at)
    env = _get_env()
    tap_command = os.environ.get("tap_command")
    tap_args = os.environ.get("tap_args")
    target_command = os.environ.get("target_command")
    target_args = os.environ.get("target_args")

    tap_bash_command = _get_command_string(tap_command, tap_args, params, venv)
    target_bash_command = _get_command_string(target_command, target_args, params, venv)

    return tap_bash_command, target_bash_command


def _write_config():
    params = _get_params()
    tap_config = os.environ.get("tap_config")
    if not os.path.isdir(".env"):
        os.mkdir(".env")
    with open(os.path.join(params["work_dir"], ".env/tap_config.json"), "w") as f:
        f.write(tap_config)
    target_config = os.environ.get("target_config")
    with open(os.path.join(params["work_dir"], ".env/target_config.json"), "w") as f:
        f.write(target_config)

    google_client_secret_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ".env/client_secret.json")
    google_client_secret_path = os.path.join(params["work_dir"], google_client_secret_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_client_secret_path

    google_client_secret = os.environ.get("google_client_secret")
    with open(google_client_secret_path, "w") as f:
        f.write(google_client_secret)


def _write_catalog():
    params = _get_params()
    # TODO: Find a way of passing catalog other than env var because the theoretical limit is 32,767 bytes
    # TODO: Also note that AWS SSM Parameter Store's limit is 4KB
    catalog = os.environ.get("catalog")
    if not catalog:
        return
    with open(os.path.join(params["work_dir"], "./catalog.json"), "w") as f:
        f.write(catalog)


def _get_time_window(data):
    start_at, end_at = etl.get_time_window(data,
                                           start_offset=datetime.timedelta(days=-1),
                                           end_offset=datetime.timedelta(days=1))
    return start_at, end_at


def run_etl(data):
    """
    Run singer.io process connecting input and output with a PIPE
    """
    _write_config()
    env = _get_env()
    venv = data.get("venv")

    _write_catalog()

    start_at, end_at = _get_time_window(data)
    tap_command, target_command = _get_singer_commands(start_at, end_at, venv)

    # In Docker container, it takes shell=True to run a subprocess without causing Permission error (13)
    # and to run with shell=True, we need to feed the entire cmd string with args without splitting.
    # tap_proc = subprocess.Popen(shlex.split(tap_command),
    tap_proc = subprocess.Popen([tap_command],
            stdout=subprocess.PIPE, env=env, shell=True)
    try:
        # output = subprocess.check_output(shlex.split(target_command),
        output = subprocess.check_output([target_command],
                stdin=tap_proc.stdout, env=env, shell=True)
    except subprocess.CalledProcessError as e:
        logger.error("Error:" + str(e))
        raise
    tap_proc.wait()


def show_commands(data):
    """
    Show singer.io tap and target commands
    """
    _write_config()
    env = _get_env()
    venv = data.get("venv")

    start_at, end_at = _get_time_window(data)

    tap_command, target_command = _get_singer_commands(start_at, end_at, venv)
    print(tap_command)
    print(target_command)


def default(data):
    run_etl(data)


if __name__ == "__main__":
    print("Test this from runner.py")
