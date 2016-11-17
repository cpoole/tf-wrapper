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

# TF-WRAPPER environment_vars.json format:
ENVIRONMENT_FORMAT = '''
{
    "hub": {
        "region": "us-west-2",
        "bucket_prefix": "terraform-remote-states/implementations/elb/",
        "bucket": "bucketName",
        "credential_file" : "/Users/myusername/.aws/credentials",
        "profile" : "profileName"
    },
    "dev": {
        "region" : "us-west-2",
        "bucket_prefix": "config/tf/implementations/elb/",
        "bucket": "otherBucket",
        "credential_file" : "/Users/myusername/.aws/credentials",
        "profile" : "otherProfileName"
    }
}
'''

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
    if parser_values.reconfigure:
        if (parser_values.environment or parser_values.action):
            raise Exception('you must pass \"-reconfigure true\" as the only flag')
    else:
        if not (parser_values.environment and parser_values.action):
            raise Exception('-environment argument and -action argument are required')

    # vars based on parser inputs
    tf_environment           = parser_values.environment
    tf_action                = parser_values.action
    environment_dir_path     = '{}/{}'.format(ENVIRONMENTS_BASE_PATH, tf_environment)
    remote_config_file_path  = '{}/{}'.format(ENVIRONMENTS_BASE_PATH, ENVIRONMENT_FILE_NAME)
    remote_config_dictionary = {}

    #remove remote state files
    removeStateFiles()

    # configure remote config variables
    if (os.path.isfile(remote_config_file_path) and not parser_values.reconfigure):
        with open(remote_config_file_path, 'r') as file:
            remote_config_dictionary = json.loads(file.read())
            if not tf_environment in remote_config_dictionary:
                raise Exception('Your terraform files are out of date either run with the -reconfigure flag or manually edit the environment_file to look like: \n {}'.format(ENVIRONMENT_FORMAT))
    else:
        response = ""
        while response.lower() != 'n':
            environment = input('What would you like to name this environment? ')
            remote_config_dictionary[environment] = {}
            remote_config_dictionary[environment]['bucket']        = input('Please input the s3 bucket name where you will store your remote state: ')
            remote_config_dictionary[environment]['bucket_prefix'] = input('Please input the path in the bucket where you will store your remote state (including the trailing /): ')
            remote_config_dictionary[environment]['region']        = input('Please input the region in which the bucket lives: ')
            remote_config_dictionary[environment]['profile']       = input('Please input the name of the profile in the aws creds with the key pairs for this account: ')
            response = input('are there any additional environments you want to input? (y/n): ')
        if not os.path.isdir(environment_dir_path):
            os.mkdir(environment_dir_path)
        with open(remote_config_file_path, 'w') as file:
            file.write(json.dumps(remote_config_dictionary))

    if parser_values.reconfigure:
        print("Reconfigure is true, we will check to make sure the remote state files are correctly configured")
        for env in remote_config_dictionary:
            removeStateFiles()
            configBucket(remote_config_dictionary, env)
            subprocess.call(['terraform','remote','pull'])
            terraform_json = {}
            with open('./.terraform/terraform.tfstate', 'r') as file:
                terraform_json = json.loads(file.read())
            if 'profile' not in terraform_json['remote']['config']:
                print('The {} state file needs to be updated'.format(env))
                terraform_json['remote']['config']['profile'] = remote_config_dictionary[env]['profile']
                terraform_json['remote']['config']['key'] = remote_config_dictionary[env]['bucket_prefix']
                with open('./.terraform/terraform.tfstate', 'w') as file:
                    file.write(json.dumps(terraform_json))
                subprocess.call(['terraform','remote','push'])
                removeStateFiles()
        print("reconfigure finished, exiting")
        exit()

    configBucket(remote_config_dictionary, tf_environment)


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

def configBucket (remote_config_dictionary, tf_environment):
    subprocess.call(['terraform', 'remote', 'config',
                     '-backend', 'S3',
                     '-backend-config=bucket={}'.format(remote_config_dictionary[tf_environment]['bucket']),
                     '-backend-config=key={}{}'.format(remote_config_dictionary[tf_environment]['bucket_prefix'], tf_environment),
                     '-backend-config=region={}'.format(remote_config_dictionary[tf_environment]['region']),
                     '-backend-config=profile={}'.format(remote_config_dictionary[tf_environment]['profile'])
                     ])
def removeStateFiles():
    if os.path.isfile('./.terraform/terraform.tfstate'):
        os.remove('./.terraform/terraform.tfstate')
    if os.path.isfile('./.terraform/terraform.tfstate.backup'):
        os.remove('./.terraform/terraform.tfstate.backup')
