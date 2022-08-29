import json
import os
import logging
from typing import Union, Any

logger = logging.getLogger(__name__)


class Templates(object):
    def __init__(self):
        templates = os.path.join(os.path.dirname(__file__), "types.json")
        with open(templates, "r") as types_file:
            self.types = json.load(types_file)

    def assert_structure(
        self, type_name: str, struct: Union[list, dict], many: bool = False
    ):
        template = self.types.get(type_name)
        if not template:
            raise ValueError(f"Unknown type {type_name}")
        if many and isinstance(struct, dict):
            if not struct.get("results"):
                raise ValueError(
                    "Many is true and response is dict but doesn't contain a 'results' key"
                )
            struct = struct.get("results")
            if not isinstance(struct, (list, tuple)):
                raise ValueError("'results' is not a list")
        if many:
            for s in struct:
                self.check_structure(struct=s, template=template)
        else:
            self.check_structure(struct=struct, template=template)

    def check_structure(self, template, struct):
        if not template:
            return True
        logger.info(f"template: {template}, struct: {struct}")
        if isinstance(struct, dict) and isinstance(template, dict):
            if not template.keys() <= set(struct.keys()):
                raise ValueError(
                    f"Invalid structure: {struct.keys()} given template: {template.keys()}"
                )
            for k in template.keys():
                self.check_structure(template.get(k), struct.get(k))
        if isinstance(struct, list) and isinstance(template, list):
            return all(
                self.check_structure(template=template[0], struct=c) for c in struct
            )
        elif isinstance(struct, type):
            good = isinstance(template, struct)
            if not good:
                raise ValueError(
                    f"Invalid structure: {struct} given template: {template}"
                )
        else:
            return False

    def assert_value(self, data: Any, value: Any, path: str = None):
        if path:
            components = path.split(".")
            tail = components[-1]
            head = components[0:-1]
            for h in head:
                data = data.get(h)
                if not data:
                    raise ValueError(f"No data found at {h} in path {path}")
            data = data.get(tail)
            if not data:
                raise ValueError(f"No data found at {tail} in path {path}")
        assert data == value
