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
REMOTE_STATE_VAR_DIR        = "./environments/"
REMOTE_STATE_VARS           = "{}envVars.json".format(REMOTE_STATE_VAR_DIR)
ENV_DICTIONARY              = {}
THIS_DIR                    = os.path.dirname(os.path.realpath(__file__))
HELP_DESCRIPTION            = '''This script allows us to use the same tf configuration
                                 for different environments. \n
                                 example use: python terraform-env.py -environment dev -action plan
                              '''
GIT_REPO                    = None

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
    
    # values from parser
    parser_values   = parser.parse_args()
    if not (parser_values.environment and parser_values.action):
        raise Exception("-environment argument and -action argument are required")
    tf_environment  = parser_values.environment
    tf_action       = parser_values.action
    #tf_args         = parser_values.args if parser_values.args else ''
    
    #make sure git is initialized
#    if not (os.path.isdir("./.git"):
#        gitRemote = raw_input("git directory is not yet initialized. This tool requires the current directory to be tracked by git. \
#               Please enter the remote ssh address for the git remote repo:")
#        GIT_REPO = init_repository('test')

    # populate the ENV_DICTIONARY
    if (os.path.isfile(REMOTE_STATE_VARS) and not parser_values.reconfigure):
        ENV_DICTIONARY = {}
        with open(REMOTE_STATE_VARS, 'r') as file:
            ENV_DICTIONARY = json.loads(file.read())
    else:
        ENV_DICTIONARY = {}
        ENV_DICTIONARY['bucket'] = input("Please input the s3 bucket name where you will store your remote state: ")
        ENV_DICTIONARY['bucket_prefix'] = input("Please input the path in the bucket where you will store your remote state (including the trailing /): ")
        ENV_DICTIONARY['region'] = input("Please input the region in which the bucket lives: ")
        if not os.path.isdir(REMOTE_STATE_VAR_DIR):
            os.mkdir(REMOTE_STATE_VAR_DIR)
        with open(REMOTE_STATE_VARS, 'w') as file:
            file.write(json.dumps(ENV_DICTIONARY))
    
    # color helpers
    color_red        = '\033[01;31m{0}\033[00m'
    color_green      = '\033[1;36m{0}\033[00m'
    
    # vars based on parser
    environment_file = '{}/{}.tf'.format(REMOTE_STATE_VAR_DIR, tf_environment)
    
    # get environment from file
    if not os.path.isfile(environment_file):
        raise Exception("There is no tf file for the environment specified. please add the file ./environments/{}.tf".format(tf_environment))
    
    #symlink environment var into current directory
    if os.path.islink('./environment.tf'):
        os.remove('./environment.tf')
    os.symlink('{}/{}.tf'.format(REMOTE_STATE_VAR_DIR, tf_environment), './environment.tf')
    
    # configure remote state
    subprocess.call(['terraform', 'remote', 'config',
                     '-backend', 'S3',
                     '-backend-config=bucket={}'.format(ENV_DICTIONARY['bucket']),
                     '-backend-config=key={}{}'.format(ENV_DICTIONARY['bucket_prefix'],tf_environment),
                     '-backend-config=region={}'.format(ENV_DICTIONARY['region'])
                     ])
    
    # run terraform
    print("running: terraform {}".format(" ".join(tf_action)))
    lastVal = subprocess.call(['terraform', " ".join(tf_action)])
    if lastVal == 0 and " ".join(tf_action).find('apply'):
        subprocess.call(['terraform', 'remote push'])
