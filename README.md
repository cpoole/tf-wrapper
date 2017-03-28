**DEPRICATION NOTICE**
As of terraform 0.9.2 remote state management using s3 is greatly improved. In addition terraform now has the concept of environments. 
I highly suggest migrating to this format and using map vars to store environment specific variables with the terraform.environment as a lookup key.

Terraform Wrapper
=================
This project is intended to provide a wrapper around terraform for any projects where infrastructure might be duplicated in different environments. If you maintain different environments (dev, stage, prod) in separate regions, data centers, or different clouds this tool will help you maintain consistency across your infrastructure.

The Fundamentals
================
**Requirements**

You must have AWS credentials, and terraform already installed. The AWS credentials file must have the individual profiles labeled

**Project Structure**

This project requires the following format:

```
    .
    ├── environments
    │   ├── dev
    │   │   └── dev.tf
    │   ├── environment_vars.json
    │   ├── hub
    │   │   └── hub.tf
    │   └── prod
    │       └── prod.tf
    ├── main.tf
    └── variables.tf
```

In each project shared resources and variables are placed at the top level. Environment specific resources are placed under ``./environments/<environment_name>/<any files you want>``. The file ``./environment/environment_vars.json`` stores the information about your AWS remote state.

**Example environment_vars.json**

```
{
    "hub": {
        "region": "us-west-2",
        "bucket_prefix": "config/tf/implementations/rancher-hosts/",
        "profile": "profile1",
        "bucket": "bucket-for-profile1"
    },
    "prod": {
        "region": "us-west-2",
        "bucket_prefix": "config/tf/implementations/rancher-hosts/",
        "profile": "profile2",
        "bucket": "bucket-for-profile2"
    }
}
```
please note the name of each environment definition must be the same as the name of the environment folder

**Package Use**

Every time you run this package you need to specify the environment and the action. the environment is the name of the folder under ``./environments`` and the action is the typical action passed to terraform (ie. plan, destroy, apply, etc.)

A sample command would be: ``tf -environment prod -action plan``

**Usage Details**

When you run this command the tf-wrapper will:
- Symlink all files under ``./environments/<environment_name>/`` into the top level directory.
- It will delete the ``.terraform/terraform.tfstate`` and ``.terraform/terraform.tfstate.backup`` files as this project requires remote state config, negating the need for local copies of state after the run has completed.
- For commands ``apply`` and ``destroy`` the resulting run state will automatically be pushed.

**Upgrading from < 1.0.0**

Please run ``tf -reconfigure true`` to update your terraform files to the latest format

**Authors**

Connor Poole @cpoole
Matt Rabinovitch @roobytwo
