from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Any, Dict, Iterator, List, Optional

Parameters = Dict[str, Any]


class Instance(ABC):
    @abstractmethod
    def run(self,
            command: List[str],
            snapshot_id: str,
            parameters: Parameters):
        pass

    @abstractmethod
    def logs(self, stdout: bool = True, stderr: bool = True):
        pass

    @abstractmethod
    def output_files_tarball(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

    @abstractmethod
    def get_container_state(self, execution_id) -> str:
        pass


ExecutionInfo = namedtuple(
    'ExecutionInfo', ['execution_id', 'container_status', 'instance_type'])


class InstanceProvider(ABC):
    @abstractmethod
    def acquire_instance(
            self, execution_id: str, execution_spec: dict) -> Iterator[str]:
        pass

    @abstractmethod
    def release_instance(self, execution_id: str):
        pass

    @abstractmethod
    def instance_for(self, execution_id: str) -> Optional[Instance]:
        pass

    @abstractmethod
    def push(self, image_tag: str):
        pass

    @abstractmethod
    def get_commands(self) -> ExecutionInfo:
        pass
