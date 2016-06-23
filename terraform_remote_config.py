"""
variables used in terraform-env.py. Make sure to change these for each project.
They define where the tfstates associated with this project and it's various
environment files reside.
"""

# variables
bucket        = 'hci-terraform'
bucket_prefix = 'hci-tf-global' # should match project name
region        = 'us-west-2'