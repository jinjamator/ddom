import logging
import yaml
from glob import glob
import os
import re
import inspect
import sys
from deepmerge import always_merger
import copy
from pprint import pprint

DATA_DIR = (
    os.path.abspath(os.path.dirname(__file__) + os.path.sep + "data") + os.path.sep
)

cls_lookup_table = {}


class CannotFindDeviceBluePrintError(Exception):
    pass


class InvalidChildDeviceTypeError(Exception):
    pass


class AlreadyConnectedError(Exception):
    pass


class InvalidAirFlowError(Exception):
    pass


class ChildNotFoundError(Exception):
    pass


class DeviceObject(object):
    def __init__(self, pid, vendor="generic", configuration={}):
        self._log = logging.getLogger()
        self._type = (self.__class__.__name__).lower()
        self._parents = []
        self._children = []
        self._capabilities = {}
        self._vendor = str(vendor).lower()
        self._pid = str(pid).lower()
        self._max_children = 1
        self._max_parents = 1
        self._name = None
        self._number = configuration.get("number", None)
        self._device_blueprint = self._load_blueprint(
            self._type, self._pid, self._vendor
        )
        if configuration:
            self._log.debug(f"got configuration {configuration}")
            always_merger.merge(self._device_blueprint, configuration)

        self._build()

    @property
    def parent(self):
        try:
            return self._parents[0]
        except IndexError:
            return None

    @property
    def name(self):
        # print(self._name)
        if self._name:
            try:
                return self._name.format(self=self)
            except:
                return None
        return self.pid

    def _load_blueprint(self, type, pid, vendor="generic"):

        self._glob_path = f"{DATA_DIR}{vendor}{os.path.sep}{type}{os.path.sep}**{os.path.sep}{pid}.yaml"
        self._log.debug(self._glob_path)
        result = list(glob(self._glob_path, recursive=True))
        if len(result) > 1:
            raise CannotFindDeviceBluePrintError(
                f"Too many results for type {self._type} vendor {self._vendor} pid {self._pid}: {result}"
            )
        if len(result) < 1:
            raise CannotFindDeviceBluePrintError(
                f"No results for type {self._type} vendor {self._vendor} pid {self._pid}: globbing was {self._glob_path}"
            )
        device_blueprint_path = result[0]
        with open(device_blueprint_path, "r") as stream:
            device_blueprint = yaml.safe_load(stream)
            if not device_blueprint:
                device_blueprint = {}
        for inheritance in device_blueprint.get("inherit", {}):
            inherited_type = self._get_dict_singelton_key(inheritance)
            inherited_pid = inheritance[inherited_type].get("pid")
            inherited_vendor = inheritance[inherited_type].get("vendor", "generic")
            inherited_bp = self._load_blueprint(
                inherited_type, inherited_pid, inherited_vendor
            )
            device_blueprint = always_merger.merge(inherited_bp, device_blueprint)

        if "inherit" in device_blueprint:
            del device_blueprint["inherit"]
        return device_blueprint

    def _get_dict_singelton_key(self, obj):
        if not isinstance(obj, dict):
            raise TypeError("obj is not a dict")
        lst = list(obj.keys())
        if len(lst) != 1:
            raise ValueError(f"obj must have exactly one key {obj}")
        return lst[0]

    def _build(self):
        self._max_children = self._device_blueprint.get(
            "max_children", len(self._device_blueprint.get("children", ["fake"]))
        )
        self._log.debug(f"{self.type} {self.pid} max_children: {self._max_children}")
        for attribute, value in self._device_blueprint.items():
            if attribute not in [
                "inherit",
                "children",
                "vendor",
                "pid",
                "type",
                "name",
            ]:
                self._log.debug(f"{self} :  setting {attribute} to {value}")
                setattr(self, attribute, value)
            if attribute == "name":
                self._name = value
        for child in self._device_blueprint.get("children", []):
            key = self._get_dict_singelton_key(child)

            child_class = cls_lookup_table[key]
            child_vendor = child[key].get("vendor", self._vendor)
            child_pid = child[key].get("pid", "generic")
            child_cfg = child[key]

            try:
                child_instance = getattr(sys.modules[__name__], child_class)(
                    child_pid, child_vendor, child_cfg
                )
            except CannotFindDeviceBluePrintError:
                self._log.debug(
                    f"Implicitly falling back to generic vendor for {child_class}"
                )
                child_vendor = "generic"
                child_instance = getattr(sys.modules[__name__], child_class)(
                    child_pid, child_vendor, child_cfg
                )

            self.connect(child_instance)

    def __getattr__(self, name):

        try:  # generic read only access for private attributes -> some kind of generic @property
            return copy.deepcopy(self.__getattribute__(f"_{name}"))
        except AttributeError:
            pass

        use_index = False
        if name.endswith("_index"):
            name = name[:-6]
            use_index = True

        lst = {"name": {}, "index": {}, "number": {}}

        idx = 0
        for child in self._children:
            if child._type == name:
                if child.number:
                    lst["number"][child.number] = child
                lst["index"][idx] = child
                idx += 1
                lst["name"][child.name] = child
        if lst["name"] or lst["number"] or lst["index"]:

            def wrapper(*args, **kwargs):
                if not args:  # return first child if no arguments
                    return lst["index"][0]
                if isinstance(args[0], int):
                    if use_index:
                        return lst["index"][args[0]]
                    else:
                        return lst["number"][args[0]]
                if isinstance(args[0], str):
                    try:
                        return lst["name"][args[0]]
                    except KeyError:
                        raise ChildNotFoundError(
                            f"{self}: cannot find child with name {args[0]}"
                        )

            return wrapper

    def __repr__(self) -> str:
        return super().__repr__()

    def __str__(self, level=-1) -> str:
        level += 1
        retval = (
            level * " "
            + f"{self.type}: {self.vendor} {self.pid} {self.__repr__()} {self.name}\n"
        )
        for child in self._children:
            retval += child.__str__(level)
        return retval

    def inserted(self, parent, force=False) -> bool:
        self._parents.append(parent)
        self._log.debug(f"{self.__repr__()} got inserted into {parent.__repr__()}")
        return True

    def check_child_on_attachment(self, child) -> bool:
        child_ok = False

        for allowed_child_type in self._device_blueprint.get(
            "allowed_child_types", self._device_blueprint.get("children", [])
        ):
            if isinstance(allowed_child_type, str):
                if child.type == allowed_child_type:
                    child_ok = True
                    break
            elif isinstance(allowed_child_type, dict):
                type_list = list(allowed_child_type.keys())
                allowed_type = type_list[0]
                if len(type_list) != 1:
                    raise ValueError("allowed_child dict must contain a single key")
                allowed_vendor = allowed_child_type[allowed_type].get(
                    "vendor", "generic"
                )
                allowed_pid = allowed_child_type[allowed_type].get("pid", "generic")
                if (
                    child.vendor == allowed_vendor
                    and child.pid == allowed_pid
                    and child.type == allowed_type
                ):
                    child_ok = True
                    break
            else:
                raise TypeError(
                    f"child types must be type str or a dict  {type(allowed_child_type)}"
                )
        else:  # if no explicit allowed child type is specified everthing is allowed. Don't know if this is a good idea
            child_ok = True
        return child_ok

    def connect(self, child, force=False) -> bool:
        child_ok = False
        if not str(type(child)).startswith("<class 'ddom."):
            raise InvalidChildDeviceTypeError(f"Invalid Baseclass {type(child)}")
        if getattr(child, "_base_class", None):
            self._log.debug(
                f"connecting multiple children: of type {child._base_class}"
            )
            for obj in child.all:
                self.connect(obj)
            return True

        else:
            self._log.debug(
                f"{self.__repr__()} connecting child: {child.__repr__()} of type {child.type}"
            )
            if child in self._children:
                raise AlreadyConnectedError(
                    f"child {child} is already connected to {self}"
                )
            child_ok = self.check_child_on_attachment(child)

            if child_ok:
                self._children.append(child)
                child.inserted(self)
            else:
                if force:
                    self._log.warning(
                        f'Cannot attach {child.type} {child.vendor} {child.pid} to {self.type} {self.vendor} {self.pid}. Allowed types {self._device_blueprint.get("allowed_child_types")}'
                    )
                else:
                    raise InvalidChildDeviceTypeError(
                        f'Cannot attach {child.type} {child.vendor} {child.pid} to {self.type} {self.vendor} {self.pid}. Allowed types {self._device_blueprint.get("allowed_child_types")}'
                    )
        return True

    def find_children(self, type, match_attributes={}) -> list:
        retval = []
        for child in self._children:
            if child.type == type or type == "*":
                if match_attributes:
                    ok = True
                    for attribute, rgx in match_attributes.items():
                        for bad_token in [
                            "(",
                            ")",
                            "import",
                            "eval",
                        ]:  # this is not sufficient, but for now good enough
                            if bad_token in attribute:
                                raise Exception("bad token")
                                return []
                        code = f"child.{attribute}"
                        match_value = eval(
                            code
                        )  # this is a security risk, but for now good enough
                        if not re.search(rgx, str(match_value)):
                            ok = False
                            break
                    if ok:
                        retval.append(child)
                else:
                    retval.append(child)
            retval += child.find_children(type, match_attributes)
        return retval


class DeviceObjectList(object):
    _base_class = None

    def __init__(self, pid, vendor="generic", configuration={}):
        self._log = logging.getLogger()
        self._lst = []
        self._type = self._base_class.lower()
        self._vendor = vendor
        self._pid = pid
        self._configuration = configuration
        for number in range(
            configuration.get("start", 0), configuration.get("end", -1) + 1
        ):
            child_class = self._base_class
            try:
                child_instance = getattr(sys.modules[__name__], child_class)(
                    pid, vendor, configuration
                )
            except CannotFindDeviceBluePrintError:
                self._log.debug(
                    f"Implicitly falling back to generic vendor for {child_class}"
                )
                vendor = "generic"
                child_instance = getattr(sys.modules[__name__], child_class)(
                    pid, vendor, configuration
                )
            child_instance._number = number
            self._lst.append(child_instance)

    @property
    def all(self):
        return self._lst

    @property
    def type(self):
        return self._type

    @property
    def pid(self):
        return self._pid

    @property
    def vendor(self):
        return self._vendor


class Transceiver(DeviceObject):
    pass


class Port(DeviceObject):
    pass


class Chassis(DeviceObject):
    def __init__(self, pid, vendor="generic", configuration={}):
        self.airflow = None
        super().__init__(pid, vendor, configuration)


class LineCard(DeviceObject):
    @property
    def number(self):  # inherit lc number from slot if not defined
        if not self._number:
            return self._parents[0].number


class SuperVisor(LineCard):
    pass


class Module(LineCard):
    pass


class PowerSupply(DeviceObject):
    def inserted(self, parent):
        if parent._parents[0].airflow:

            if parent._parents[0].airflow != self.airflow:
                raise InvalidAirFlowError(
                    f"chassis has airflow {parent._parents[0].airflow} , powersupply {self.airflow}"
                )
        else:
            self._log.debug(
                f"{self.__repr__()} slot: {parent.name} setting chassis airflow to {self.airflow}"
            )
            parent._parents[0].airflow = self.airflow
        super().inserted(parent)


class Slot(DeviceObject):

    pass


class Fan(DeviceObject):
    def inserted(self, parent):
        if parent._parents[0].airflow:

            if parent._parents[0].airflow != self.airflow:
                raise InvalidAirFlowError(
                    f"chassis has airflow {parent._parents[0].airflow} , fan {self.airflow}"
                )
        else:
            self._log.debug(
                f"{self.__repr__()} slot: {parent.name} setting chassis airflow to {self.airflow}"
            )
            parent._parents[0].airflow = self.airflow
        super().inserted(parent)


class Ports(DeviceObjectList):
    _base_class = "Port"


class Cable(DeviceObject):
    def inserted(self, parent, force=False) -> bool:
        self._parents.append(parent)
        self._log.debug(f"{self.__repr__()} got inserted into {parent.__repr__()}")
        return True


class Jack(DeviceObject):
    pass


for cls in inspect.getmembers(
    sys.modules[__name__],
    lambda member: inspect.isclass(member) and member.__module__ == __name__,
):
    cls_lookup_table[cls[0].lower()] = cls[0]
