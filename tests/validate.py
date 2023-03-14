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
        try:
            template = self.types.get(type_name)
            if not template:
                raise ValueError(f"[Templates] :: Unknown type {type_name}")
            if many and isinstance(struct, dict):
                if not struct.get("results"):
                    raise ValueError(
                        "[Templates] :: Many is true and response is dict but doesn't contain a 'results' key"
                    )
                struct = struct.get("results")
                if not isinstance(struct, (list, tuple)):
                    raise ValueError("'results' is not a list")
            if many:
                for s in struct:
                    self.check_structure(type_name=type_name, struct=s, template=template)
            else:
                self.check_structure(type_name=type_name, struct=struct, template=template)
        except Exception as ex:
            logger.exception("[Templates] :: error")
            raise ex

    def check_structure(self, type_name: str, template, struct):
        if not template:
            return True
        logger.info(f"[Templates] :: template: {template}, struct: {struct}")
        if isinstance(struct, dict) and isinstance(template, dict):
            if not template.keys() <= set(struct.keys()):
                unknown_keys = set(template.keys()) - set(struct.keys())
                raise ValueError(
                    f"[Templates] :: Error with type {type_name}: Expected keys: {unknown_keys} not found in response: {struct.keys()}"
                )
            for k in template.keys():
                self.check_structure(type_name=type_name, template=template.get(k), struct=struct.get(k))
        if isinstance(struct, list) and isinstance(template, list):
            return all(
                self.check_structure(type_name=type_name, template=template[0], struct=c) for c in struct
            )
        elif isinstance(struct, type):
            good = isinstance(template, struct)
            if not good:
                raise ValueError(
                    f"[Templates] :: Error with type {type_name}: Unexpected type: {type(struct)} given type in template: {type(template)}"
                )
        else:
            return False

    def assert_value(self, type_name: str, data: Any, value: Any, path: str = None):
        try:
            logger.info(f"[Templates] :: Type {type_name}: assert_value data: {data}, value: {value}, path: {path}")
            if path:
                components = path.split(".")
                tail = components[-1]
                head = components[0:-1]
                for h in head:
                    data = data.get(h)
                    if not data:
                        raise ValueError(f"[Templates] :: Error with type {type_name}: No data found at {h} in path {path}")
                data = data.get(tail)
                if not data:
                    raise ValueError(f"[Templates] :: Error with type {type_name}: No data found at {tail} in path {path}")
            logger.info(f"[Templates] :: assert_value {data} == {value}")
            assert data == value
        except Exception as ex:
            logger.exception(f"[Templates] :: Error with type {type_name}: error")
            raise ex
