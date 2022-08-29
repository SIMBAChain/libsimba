import logging

from typing import Any, List, Tuple

from libsimba.simba_request import SimbaRequest
from libsimba.utils import Path


logger = logging.getLogger(__name__)


class ParamChecking:
    def __init__(self, app_name, contract_name):
        self.app_name = app_name
        self.contract_name = contract_name
        self.metadata = self.get_metadata()

    def get_metadata(self):
        resp = SimbaRequest(
            endpoint=Path.APP_CONTRACT.format(self.app_name, self.contract_name),
            query_params={"format": "json"},
        ).send_sync()
        return resp.get("metadata")

    def is_array(self, data_type) -> bool:
        return data_type.endswith("]")

    def is_struct(self, param_type) -> bool:
        return param_type.startswith("struct ")

    def get_dimension_lengths(self, dims: str) -> List[int]:
        """
        Reads a solidity array definition and returns a list of ints
        for the array lengths. zero means the array is dynamically sized.

        :param dims: the array declaration with potentially multiple dimensions
        :type dims: str
        :return: a list of ints in order of the dimensions of the arrays
        :rtype: List[int]
        """
        ret: List[int] = []
        dimensions: List[str] = list(filter(None, dims.split("[")))
        for dim in dimensions:
            if len(dim) == 1:
                ret.insert(0, 0)
            else:
                ret.insert(0, int(dim[:-1]))
        return ret

    def get_type_info(self, data_type: str) -> Tuple[str, bool, List[int]]:
        """
        Break down the type string into components for further processing.

        :param data_type: data type string
        :type data_type: str
        :return: a tuple of data type, is struct and list of array dimensions
        :rtype: Tuple[str, bool, List[int]]
        """
        struct = self.is_struct(data_type)
        if struct:
            data_type = data_type[7:]
        array = self.is_array(data_type)
        if array:
            ind = data_type.find("[")
            dimensions = self.get_dimension_lengths(data_type[ind:])
            data_type = data_type[:ind]
        else:
            dimensions = []
        return data_type, struct, dimensions

    def validate_params(self, method_name: str, inputs: dict) -> None:
        """
        validate parameters for a given method.

        :param method_name: method name
        :type method_name: str
        :param inputs: method inputs as a dict
        :type inputs: dict
        :raises: ValueError if validation fails
        """
        md = self.metadata.get("contract", {})
        method = md.get("methods", {}).get(method_name)
        if not method:
            raise ValueError(f"Execpted method name: {method_name}")
        self.validate(inputs=inputs, param_list=method.get("params"), md=md)

    def validate(self, inputs: dict, param_list: List[dict], md: dict) -> None:
        """
        validate parameters for a given method.

        :param method_name: method name
        :type method_name: str
        :param inputs: method inputs as a dict
        :type inputs: dict
        :param param_list: list of parameter name/type dicts
        :type param_list: List[dict]
        :param md: the contract metadata
        :type md: dict
        :raises: ValueError if validation fails
        """
        params = self.params_as_dict(param_list)
        for k, v in params.items():
            if k == "_bundleHash":
                continue
            if not inputs.get(k):
                raise ValueError(
                    f"Unexpected keys. Definition: {params}, inputs: {inputs}"
                )
            type_info = self.get_type_info(v)
            self.validate_param(
                key=k,
                input=inputs.get(k),
                data_type=type_info[0],
                struct=type_info[1],
                dimensions=type_info[2],
                md=md,
            )

    def validate_param(
        self,
        key: str,
        input: Any,
        data_type: str,
        struct: bool,
        dimensions: List[int],
        md: dict,
    ):
        """
        validate a parameter for a given method.

        :param key: parameter name
        :type key: str
        :param input: method input
        :type input: Any
        :param data_type: data type
        :type data_type: str
        :param struct: boolean indicating the type is a struct
        :type struct: bool
        :param dimensions: list of dimensions
        :type dimensions: List[int]
        :param md: the contract metadata
        :type md: dict
        :raises: ValueError if validation fails
        """
        logger.debug(
            f"key: {key}, input: {input}, data type: {data_type}, struct: {struct}, dimensions: {dimensions}"
        )
        if dimensions:
            if not isinstance(input, (list, tuple)) or not dimensions:
                raise ValueError(
                    f"Expected a list for key: {key} and an array of type: {data_type} but got a {input}"
                )
            length = dimensions[0]
            if length > 0 and not len(input) == length:
                raise ValueError(
                    f"Unexpected length. Expected {length} but got {len(input)}"
                )
            for v in input:
                self.validate_param(
                    key=key,
                    input=v,
                    data_type=data_type,
                    struct=struct,
                    dimensions=dimensions[1:],
                    md=md,
                )
        elif struct:
            params = md.get("types", {}).get(data_type, {}).get("components")
            self.validate(inputs=input, param_list=params, md=md)
        else:
            self.expect_scalar(key=key, data_type=data_type, value=input)

    def params_as_dict(self, params: List[dict]) -> dict:
        return {p.get("name"): p.get("type") for p in params}

    def expect_scalar(self, key: str, data_type: str, value: Any):
        """
        validate a scalar value

        :param key: parameter name
        :type key: str
        :param data_type: data type
        :type data_type: str
        :param value: input
        :type value: Any
        :raises: ValueError if validation fails
        """
        if value is None:
            raise ValueError(
                f"Values cannot be null for key: {key} and data type {data_type}"
            )
        if data_type.startswith("bool") and not isinstance(value, bool):
            raise ValueError(f"Expected boolean but got {type(value)}")
        elif data_type.startswith("uint"):
            if not isinstance(value, (int, str)):
                raise ValueError(
                    f"Expected int or string but got {type(value)} for key: {key} and value: {value}"
                )
            if int(value) < 0:
                raise ValueError(
                    f"Expected non negative int but got {value} for key: {key}"
                )
        elif data_type.startswith("int"):
            if not isinstance(value, (int, str)):
                raise ValueError(
                    f"Expected int or string but got {type(value)} for key: {key} and value: {value}"
                )
            if isinstance(value, str):
                if not value.startswith("0x"):
                    raise ValueError(
                        f"Expected string to be hex encoded but got {value} for key: {key}"
                    )
        elif data_type == "address":
            if not isinstance(value, str):
                raise ValueError(
                    f"Expected string but got {type(value)} for key: {key} and value: {value}"
                )
            if not value.startswith("0x"):
                raise ValueError(
                    f"Expected string to be hex encoded but got {value} for key: {key}"
                )
        elif data_type.startswith("byte") or data_type.startswith("sbyte"):
            if not isinstance(value, str):
                raise ValueError(
                    f"Expected string but got {type(value)} for key: {key} and value: {value}"
                )
            if not value.startswith("0x"):
                raise ValueError(
                    f"Expected string to be hex encoded but got {value} for key: {key}"
                )
