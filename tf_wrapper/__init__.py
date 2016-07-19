#!/bin/python3

#FOLLOWING FILE IS IN PYTHON 3.5.1

# global packages
import argparse
import os
import shutil
import subprocess
import glob
import json
import pprint
import shutil

# debug
from pdb import set_trace as bp

# constants
ENVIRONMENTS_BASE_PATH = './environments'
ENVIRONMENT_FILE_NAME  = 'environment_vars.json'
THIS_DIR               = os.path.dirname(os.path.realpath(__file__))
HELP_DESCRIPTION       = '''This script allows us to use the same tf configuration
                                 for different environments. \n
                                 example use: python terraform-env.py -environment dev -action plan
                              '''

def main():
    #raw input compatibility for python 2 and 3 
    global input
    try: input = raw_input
    except NameError: pass

    # parser
    parser = argparse.ArgumentParser(description= HELP_DESCRIPTION)
    parser.add_argument('-environment', help='the environment you want to use. matches to the folder name under env')
    parser.add_argument('-reconfigure', help='pass -reconfigure true if you would like to change the remote state bucket details')
    parser.add_argument('-action', nargs=argparse.REMAINDER, help='the action passed to terraform')
    
    # ensure required vars are set from parser
    parser_values   = parser.parse_args()
    if not (parser_values.environment and parser_values.action):
        raise Exception('-environment argument and -action argument are required')

    # vars based on parser inputs
    tf_environment           = parser_values.environment
    tf_action                = parser_values.action
    environment_dir_path     = '{}/{}'.format(ENVIRONMENTS_BASE_PATH, tf_environment)
    remote_config_file_path  = '{}/{}'.format(ENVIRONMENTS_BASE_PATH, ENVIRONMENT_FILE_NAME)
    remote_config_dictionary = {}

    # configure remote config variables
    if (os.path.isfile(remote_config_file_path) and not parser_values.reconfigure):
        with open(remote_config_file_path, 'r') as file:
            remote_config_dictionary = json.loads(file.read())
    else:
        remote_config_dictionary['bucket']        = input('Please input the s3 bucket name where you will store your remote state: ')
        remote_config_dictionary['bucket_prefix'] = input('Please input the path in the bucket where you will store your remote state (including the trailing /): ')
        remote_config_dictionary['region']        = input('Please input the region in which the bucket lives: ')
        if not os.path.isdir(environment_dir_path):
            os.mkdir(environment_dir_path)
        with open(remote_config_file_path, 'w') as file:
            file.write(json.dumps(remote_config_dictionary))
    
    # remove any hanging tfstate files
    if os.path.isfile('./.terraform/terraform.tfstate'):
        os.remove('./.terraform/terraform.tfstate')
    if os.path.isfile('./.terraform/terraform.tfstate.backup'):
        os.remove('./.terraform/terraform.tfstate.backup')
    
    # make sure tfvars file exists
    if os.listdir(environment_dir_path) == []:
        raise Exception('There are no tf files for the environment specified. please add terraform files to {}/'.format(environment_dir_path))
    
    # (re)create symlink
    for file in os.listdir('./{}'.format(environment_dir_path)):
        file_path = './{}/{}'.format(environment_dir_path, file)
        sym_path  = './{}'.format(file)
        if os.path.islink(sym_path):
            os.remove(sym_path)
        os.symlink(file_path, sym_path)
    
    # configure remote state
    subprocess.call(['terraform', 'remote', 'config',
                     '-backend', 'S3',
                     '-backend-config=bucket={}'.format(remote_config_dictionary['bucket']),
                     '-backend-config=key={}{}'.format(remote_config_dictionary['bucket_prefix'], tf_environment),
                     '-backend-config=region={}'.format(remote_config_dictionary['region'])
                     ])
    
    # run terraform
    print("running: terraform {}".format(" ".join(tf_action)))
    tf_action.insert(0, 'terraform')
    lastVal = subprocess.call(tf_action)
    if lastVal == 0 and " ".join(tf_action).find('apply') != -1:
        subprocess.call(['terraform', 'remote', 'push'])

    # remove symlinks
    for file in os.listdir('./{}'.format(environment_dir_path)):
        file_path = './{}/{}'.format(environment_dir_path, file)
        sym_path  = './{}'.format(file)
        if os.path.islink(sym_path):
            os.remove(sym_path)
