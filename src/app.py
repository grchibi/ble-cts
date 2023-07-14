import datetime
import logging

from backports.zoneinfo import ZoneInfo

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from ble_lib import (
    Advertisement,
    Application,
    Characteristic,
    CharacteristicUserDescriptionDescriptor,
    Service,
    find_adapter,
)

MainLoop = None
try:
    from gi.repository import GLib

    MainLoop = GLib.MainLoop
except ImportError:
    import gobject as GObject

    MainLoop = GObject.MainLoop

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logHandler = logging.StreamHandler()
filelogHandler = logging.FileHandler("ble-cts.log")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logHandler.setFormatter(formatter)
filelogHandler.setFormatter(formatter)
logger.addHandler(filelogHandler)
logger.addHandler(logHandler)

mainloop = None

BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IF = "org.bluez.GattManager1"
LE_ADVERTISEMENT_IF = "org.bluez.LEAdvertisement1"
LE_ADVERTISING_MANAGER_IF = "org.bluez.LEAdvertisingManager1"
AGENT_IF = "org.bluez.Agent1"


class TTCTService(Service):
    TT_CTService_UUID = "00001805-0000-1000-8000-00805f9b34fb"

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TT_CTService_UUID, True)
        self.add_characteristic(CurrentTimeCharacteristic(bus, 0, self))
        self.add_characteristic(LocalTimeInformationCharacteristic(bus, 1, self))


class CurrentTimeCharacteristic(Characteristic):
    uuid = "00002a2b-0000-1000-8000-00805f9b34fb"
    description = b"Return the current time"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["read"], service,
        )

        self.value = []
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        logger.debug("current time Read: " + repr(self.value))

        try:
            self.value = encode_current_time()
        except Exception as e:
            logger.error(f"Error in encode_current_time()")
            self.value = bytearray("ERROR", encoding="utf8")

        return self.value


class LocalTimeInformationCharacteristic(Characteristic):
    uuid = "00002a0f-0000-1000-8000-00805f9b34fb"
    description = b"Return the local time information"

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, self.uuid, ["read"], service,
        )

        self.value = []
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        logger.debug("local time information Read: " + repr(self.value))

        try:
            self.value = encode_current_time_info()
        except Exception as e:
            logger.error(f"Error in encode_current_time_info()")
            self.value = bytearray("ERROR", encoding="utf8")

        return self.value


class TTCTSAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, "peripheral")
        self.add_manufacturer_data(
            0xffff, [0x08, 0x08],
        )
        self.add_service_uuid(TTCTService.TT_CTService_UUID)

        self.add_local_name("TTCTS")
        self.include_tx_power = True


# return current time information, 2 bytes
def encode_current_time_info():
    tzoffset = int(datetime.datetime.now(ZoneInfo('Asia/Tokyo')).utcoffset().total_seconds() / 60 / 15)
    dstoffset = int(datetime.datetime.now(ZoneInfo('Asia/Tokyo')).dst().total_seconds() / 60 / 15)

    bary_tzdst_info = bytearray((tzoffset, dstoffset))

    return bary_tzdst_info


# return 10 bytes data
def encode_current_time():
    dt_now = datetime.datetime.now()

    bary_y = dt_now.year.to_bytes(2, 'big')
    bary_dt = bytearray((dt_now.month, dt_now.day, dt_now.hour, dt_now.minute, dt_now.second, datetime.date.today().isoweekday(), dt_now.microsecond//1000*256//1000, 0))

    return bary_y + bary_dt


# called when Advertisement success
def register_ad_cb():
    logger.info("Advertisement registered")


# called when Advertisement failed
def register_ad_error_cb(error):
    logger.critical("Failed to register advertisement: " + str(error))
    mainloop.quit()


def register_app_cb():
    logger.info("GATT application registered")


def register_app_error_cb(error):
    logger.critical("Failed to register application: " + str(error))
    mainloop.quit()


def main():
    global mainloop

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # get the system bus
    bus = dbus.SystemBus()

    # get the BLE controller
    adapter = find_adapter(bus)
    if not adapter:
        logger.critical("GattManager1 interface not found")
        return
    
    adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter)
    #adapter_props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")

    # powered property on the controller to on
    #adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    # Get manager objs
    svc_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IF)
    adv_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IF)

    advertisement = TTCTSAdvertisement(bus, 0)
    #obj = bus.get_object(BLUEZ_SERVICE_NAME, "/org/bluez")

    app = Application(bus)
    app.add_service(TTCTService(bus, 2))

    mainloop = MainLoop()

    adv_manager.RegisterAdvertisement(
        advertisement.get_path(),
        {},
        reply_handler = register_ad_cb,
        error_handler = register_ad_error_cb,
    )

    logger.info("Registering GATT application...")

    svc_manager.RegisterApplication(
        app.get_path(),
        {},
        reply_handler = register_app_cb,
        error_handler = [register_app_error_cb],
    )
    
    mainloop.run()
 

if __name__  == "__main__":
    main()