import logging
from typing import Iterator, Optional

from containers import Containers
from images import Images
from instances.instance_base import Instance

log = logging.getLogger('localhost')


class LocalhostInstance(Instance):
    def __init__(self,
                 images: Images,
                 containers: Containers,
                 execution_id: str):
        self.images = images
        self.containers = containers
        self.execution_id = execution_id

    def run(self, command: str, snapshot_id: str):
        """
        Runs a command on the instance.
        """
        self.containers.run(self.execution_id, snapshot_id, command)

    def logs(self):
        return self.containers.logs(self.execution_id)

    def cleanup(self):
        self.containers.rm(self.execution_id)


class Localhost:
    # noinspection PyUnusedLocal
    @staticmethod
    def from_config(config):
        images = Images.from_config(config)
        return Localhost(images)

    def __init__(self, images: Images):
        self.images = images
        self.execution_ids = set()

    def acquire_instance(self, execution_id: str) -> Iterator[str]:
        """
        "Acquires" an instance.

        As we're dealing with `localhost` here, it's always the same instance.
        """
        self.execution_ids.add(execution_id)
        return iter([])

    def release_instance(self, execution_id: str):
        """
        "Releases" an instance.

        As we're dealing with `localhost` here, this doesn't do much.
        """
        self.instance_for(execution_id).cleanup()
        self.execution_ids.remove(execution_id)

    def instance_for(self, execution_id: str) -> Optional[LocalhostInstance]:
        """
        "Gets" the instance assigned to the execution ID.

        As we're dealing with `localhost` here, it's always the same instance.
        """
        if execution_id in self.execution_ids:
            containers = Containers()
            return LocalhostInstance(self.images, containers, execution_id)
        else:
            return None

    # noinspection PyUnusedLocal
    def push(self, image_tag: str):
        pass
