import threading
import time
from typing import Iterator, Optional

import boto3
from botocore.exceptions import ClientError

from instances.aws.ec2_instance import EC2Instances
from instances.instance_base import Instance


class AutoScalingGroup:
    # We find available instances by looking at those in which
    # the Execution-Id tag is empty. The autoscaling group has this tag
    # with an empty value, and it is propagated to new instances.
    _EXECUTION_ID_TAG = 'Execution-Id'

    _name_to_group = {}
    _name_to_group_lock = threading.RLock()

    @staticmethod
    def from_config(config):
        name = config.aws_autoscaling_group
        client = boto3.client('autoscaling')
        instances = EC2Instances(
            client=boto3.client('ec2'),
            filters=[{'Name': 'tag:aws:autoscaling:groupName',
                      'Values': [name]}])
        return AutoScalingGroup(name, client, instances)

    def __new__(cls, name: str, client, instances: EC2Instances):
        with AutoScalingGroup._name_to_group_lock:
            try:
                return AutoScalingGroup._name_to_group[name]
            except KeyError:
                pass
            AutoScalingGroup._check_autoscaling_group_exists(name)
            group = super().__new__(cls)
            AutoScalingGroup._name_to_group[name] = group
            return group

    def __init__(self, name: str, client, instances: EC2Instances):
        self.name = name
        self.client = client
        self.instances = instances
        self.lock = threading.RLock()

    def acquire_instance(
            self,
            execution_id: str,
            max_trials: int = 30,
            wait_for_seconds: int = 10) \
            -> Iterator[str]:
        """
        Gets an available instance for the execution with the given id.

        If there's at least one instance in the group that is not running
        a command, assign the execution id to one of them and return it.
        Otherwise, increase the desired capacity of the group and try until
        the maximum number of trials.
        """
        tries_remaining = max_trials
        with self.lock:
            did_increase_capacity = False
            while tries_remaining > 0:
                tries_remaining -= 1

                instance = self.instances.acquire_for(execution_id)
                if instance:
                    yield 'started'
                    break
                else:
                    yield 'pending'

                if not did_increase_capacity:
                    try:
                        self._increase_desired_capacity()
                        did_increase_capacity = True
                        yield 'allocated'
                    except ClientError as e:
                        error_code = e.response['Error']['Code']
                        # Might fail if there's a scaling event taking place
                        if error_code == 'ScalingActivityInProgress':
                            pass
                        elif error_code == 'ValidationError':
                            raise MaxNumberOfInstancesReached(e.args)
                        else:
                            raise

                time.sleep(wait_for_seconds)

    def release_instance(self, execution_id: str):
        self.instances.release_for(execution_id)

    def instance_for(self, execution_id) -> Optional[Instance]:
        return self.instances.instance_for(execution_id)

    @staticmethod
    def _check_autoscaling_group_exists(name: str):
        client = boto3.client('autoscaling')
        response = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[name],
            MaxRecords=1
        )
        if len(response['AutoScalingGroups']) == 0:
            raise ValueError(f'Auto scaling group doesn\'t exist: [{name}]')

    def _get_desired_capacity(self) -> int:
        response = self.client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.name],
            MaxRecords=1
        )
        return int(response['AutoScalingGroups'][0]['DesiredCapacity'])

    def _increase_desired_capacity(self, amount=1):
        with self.lock:
            desired_capacity = self._get_desired_capacity()
            self.client.set_desired_capacity(
                AutoScalingGroupName=self.name,
                DesiredCapacity=desired_capacity + amount,
                HonorCooldown=True)


class MaxNumberOfInstancesReached(Exception):
    pass
