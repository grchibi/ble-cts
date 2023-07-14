import dbus

import array
import logging
import sys

DBUS_OMAN_IF = "org.freedesktop.DBus.ObjectManager"
DBUS_PROPS_IF = "org.freedesktop.DBus.Properties"

GATT_SERVICE_IF = "org.bluez.GattService1"
GATT_CHAR_IF = "org.bluez.GattCharacteristic1"
GATT_DESC_IF = "org.bluez.GattDescriptor1"

BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IF = "org.bluez.GattManager1"
LE_ADVERTISEMENT_IF = "org.bluez.LEAdvertisement1"
LE_ADVERTISING_MANAGER_IF = "org.bluez.LEAdvertisingManager1"

AGENT_IF = "org.bluez.Agent1"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotPermitted"


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotSupported"


def find_adapter(bus):
    remote_obj_man = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OMAN_IF)
    objs = remote_obj_man.GetManagedObjects()
    
    for o, props in objs.items():
        if GATT_MANAGER_IF in props.keys():
            return o
        
    return None
    

class Advertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = None
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties["Type"] = self.ad_type
        if self.service_uuids is not None:
            properties["ServiceUUIDs"] = dbus.Array(self.service_uuids, signature="s")
        if self.solicit_uuids is not None:
            properties["SolicitUUIDs"] = dbus.Array(self.solicit_uuids, signature="s")
        if self.manufacturer_data is not None:
            properties["ManufacturerData"] = dbus.Dictionary(
                self.manufacturer_data, signature="qv"
            )
        if self.service_data is not None:
            properties["ServiceData"] = dbus.Dictionary(
                self.service_data, signature="sv"
            )
        if self.local_name is not None:
            properties["LocalName"] = dbus.String(self.local_name)
        if self.include_tx_power is not None:
            properties["IncludeTxPower"] = dbus.Boolean(self.include_tx_power)

        if self.data is not None:
            properties["Data"] = dbus.Dictionary(self.data, signature="yv")
        return {LE_ADVERTISEMENT_IF: properties}
    
    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature="qv")
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature="y")

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature="sv")
        self.service_data[uuid] = dbus.Array(data, signature="y")

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature="yv")
        self.data[ad_type] = dbus.Array(data, signature="y")

    @dbus.service.method(DBUS_PROPS_IF, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        logger.info("GetAll")
        if interface != LE_ADVERTISEMENT_IF:
            raise InvalidArgsException()
        logger.info("returning props")
        return self.get_properties()[LE_ADVERTISEMENT_IF]

    @dbus.service.method(LE_ADVERTISEMENT_IF, in_signature="", out_signature="")
    def Release(self):
        logger.info("%s: Released!" % self.path)


# org.bluez.GattService1 interface implementation
class Service(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/service"

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IF: {
                "UUID": self.uuid,
                "Primary": self.primary,
                "Characteristics": dbus.Array(
                    self.get_characteristic_paths(), signature="o"
                ),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics
    
    @dbus.service.method(DBUS_PROPS_IF, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IF:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IF]
    

# org.bluez.GattCharacteristic1 interface implementation
class Characteristic(dbus.service.Object):    
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHAR_IF: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
                "Descriptors": dbus.Array(self.get_descriptor_paths(), signature="o"),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROPS_IF, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHAR_IF:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHAR_IF]

    @dbus.service.method(GATT_CHAR_IF, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        logger.info("Default ReadValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHAR_IF, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        logger.info("Default WriteValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHAR_IF)
    def StartNotify(self):
        logger.info("Default StartNotify called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHAR_IF)
    def StopNotify(self):
        logger.info("Default StopNotify called, returning error")
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROPS_IF, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


# org.bluez.GattDescriptor1 interface implementation
class Descriptor(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + "/desc" + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_DESC_IF: {
                "Characteristic": self.chrc.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROPS_IF, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_DESC_IF:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IF]

    @dbus.service.method(GATT_DESC_IF, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        logger.info("Default ReadValue called, returning error")
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IF, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        logger.info("Default WriteValue called, returning error")
        raise NotSupportedException()
    

# CUD descriptor
class CharacteristicUserDescriptionDescriptor(Descriptor):
    CUD_UUID = "2901"

    def __init__(
        self, bus, index, characteristic,
    ):

        self.value = array.array("B", characteristic.description)
        self.value = self.value.tolist()
        Descriptor.__init__(self, bus, index, self.CUD_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


# org.bluez.GattApplication1 interface implementation
class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OMAN_IF, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        logger.info("GetManagedObjects")

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


