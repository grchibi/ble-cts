import dbus

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

def find_adapter(bus):
    remote_obj_man = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OMAN_IF)
    objs = remote_obj_man.GetManagedObjects()

    for o, props in objs.items():
        if GATT_MANAGER_IF in props.keys():
            return o
        
        return None