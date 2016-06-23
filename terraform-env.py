#!/bin/python

#FOLLOWING FILE IS IN PYTHON 2.7

# global packages
import argparse
import os
import shutil
import subprocess
import glob
import json
import pprint

# debug
from pdb import set_trace as bp

# constants
REMOTE_STATE_VARS           = "./.environments/envVars.json"
ENV_DICTIONARY               = {}
THIS_DIR                    = os.path.dirname(os.path.realpath(__file__))
CURRENT_TFSTATE_FILE        = '.terraform/terraform.tfstate'
CURRENT_TFSTATE_BACKUP_FILE = '.terraform/terraform.tfstate.backup'
HELP_DESCRIPTION            = '''This script allows us to use the same tf configuration
                                 for different environments. \n
                                 example use: python terraform-env.py dev plan
                              '''
# populate the ENV_DICTIONARY
if os.path.isfile(REMOTE_STATE_VARS):
    ENV_DICTIONARY = {}
    with open(REMOTE_STATE_VARS, 'r') as file:
        ENV_DICTIONARY = json.loads(file.read())
else:
    ENV_DICTIONARY = {}
    ENV_DICTIONARY['bucket'] = raw_input("Please input the s3 bucket name where you will store your remote state: ")
    ENV_DICTIONARY['bucket_prefix'] = raw_input("Please input the path in the bucket where you will store your remote state: ")
    ENV_DICTIONARY['region'] = raw_input("Please input the region in which the bucket lives: ")
    if not os.path.isdir('./.environments'):
        os.mkdir('./.environments')
    if not os.path.isdir('./env'):
        os.mkdir('./env')
    with open(REMOTE_STATE_VARS, 'w') as file:
        file.write(json.dumps(ENV_DICTIONARY))

# color helpers
color_red        = '\033[01;31m{0}\033[00m'
color_green      = '\033[1;36m{0}\033[00m'

# parser
parser = argparse.ArgumentParser(description= HELP_DESCRIPTION)
parser.add_argument('environment', help='the environment you want to use. matches to the folder name under env')
parser.add_argument('action', help='the action passed to terraform')
parser.add_argument('args', nargs='*', help='extra terraform args')

# values from parser
parser_values   = parser.parse_args()
tf_environment  = parser_values.environment
tf_action       = parser_values.action
tf_args         = parser_values.args if parser_values.args else ''

# vars based on parser
environment_dir      = 'env/{}'.format(tf_environment)
bucket_key           = '{}/state/{}'.format(ENV_DICTIONARY['bucket_prefix'], tf_environment)
environment_file     = '.environment/environment' #used to see if we're in a different environment than the last run
previous_environment = 'previous' # TBC

# make sure files exists in dir based on env name
if not os.listdir(environment_dir):
    print color_red.format('environment set does not match any folders under the env folder')
    exit(1)

# get environment from file
if os.path.isfile(environment_file): 
    with open(environment_file, 'r') as file:
        previous_environment = file.readline()

# reconfigure if environment is different
environment_is_same = (tf_environment == previous_environment)
tfstate_exists      = os.path.isfile(CURRENT_TFSTATE_FILE)

if not environment_is_same:
    # move existing state files for previous environment
    if tfstate_exists:
        previous_tf_state_location        = '{}.{}'.format(CURRENT_TFSTATE_FILE, previous_environment)
        previous_tf_state_backup_location = '{}.{}'.format(CURRENT_TFSTATE_BACKUP_FILE, previous_environment)
        shutil.move(CURRENT_TFSTATE_FILE, previous_tf_state_location)
        shutil.move(CURRENT_TFSTATE_BACKUP_FILE, previous_tf_state_backup_location)

    # configure remote state
    subprocess.call(['terraform', 'remote', 'config', 
                     '-backend', 'S3',
                     '-backend-config=bucket={}'.format(ENV_DICTIONARY['bucket']),
                     '-backend-config=key={}'.format(bucket_key),
                     '-backend-config=region={}'.format(ENV_DICTIONARY['region'])
                     ]) 

    # add current environment variable to file
    with open(environment_file, 'w') as file:
        file.write(tf_environment)

# move to environment dir to perform ops
os.chdir(environment_dir)

# copy environment specific config to root
tf_env_file_names = glob.glob('*.tf')
for file in tf_env_file_names:
    from_location = file
    to_location   = '{}/environment.{}'.format(THIS_DIR, file)
    shutil.copy(from_location, to_location)

# move back to root dir to perform ops 
os.chdir(THIS_DIR)

# run terraform
subprocess.call(['terraform', tf_action])

# remove environment specific files
for file in tf_env_file_names:
    full_file_name = '{}.{}'.format('environment', file)
    os.remove(full_file_name)
