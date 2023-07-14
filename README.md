# ble-cts
BLE Current Time Service application

## Register to Systemd

```
$ cp -a  ble-cts.service /etc/systemd/system/
$ systemctl enable ble-cts
```

To run as a systemd service, execute the following command.
```
$ systemctl start ble-cts
```

## Check the logs

You can view the journal logs.
```
$ journalctl -u ble-cts.service --no-pager --since="2023-01-27 18:00:00"
```
