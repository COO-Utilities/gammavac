"""Script for logging to InfluxDB."""
import time
import sys
import json
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import SPCe

# cfg_file = files('scripts'), 'influxdb_config.json')

def main(config_file):
    """Query user for setup info and start logging to InfluxDB."""

    ## read config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    ## Connect to GammaVac SPCe
    if verbose:
        print("Connecting to SPCe controller...")
    gv = SPCe.SpceController(bus_address=cfg['gamma_bus_address'])  # set bus_address as appropriate
    gv.connect(host=cfg['device_host'], port=cfg['device_port'])      # Terminal Server IP and port

    ## Connect to InfluxDB
    if verbose:
        print("Connecting to InfluxDB...")
    db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'], org=cfg['db_org'])
    write_api = db_client.write_api(write_options=SYNCHRONOUS)

    ## Check pump status
    if 'Running' in gv.get_pump_status():
        gv.set_units("T")   # set units to Torr
        try:
            while True:
                ## Pressure
                pressure = gv.read_pressure()
                ppoint = (
                    Point("gammavac")
                    .field("pressure", pressure)
                    .tag("units", "Torr")
                    .tag("channel", f"{cfg['db_channel']}")
                )
                write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=ppoint)
                if verbose:
                    print(ppoint)
                current = gv.read_current()
                ## Current
                cpoint = (
                    Point("gammavac")
                    .field("current", current)
                    .tag("units", "Amps")
                    .tag("channel", f"{cfg['db_channel']}")
                )
                write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=cpoint)
                if verbose:
                    print(cpoint)
                ## Voltage
                voltage = gv.read_voltage()
                vpoint = (
                    Point("gammavac")
                    .field("voltage", voltage)
                    .tag("units", "Volts")
                    .tag("channel", f"{cfg['db_channel']}")
                )
                write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=vpoint)
                if verbose:
                    print(vpoint)
                # Sleep for interval_secs
                time.sleep(cfg['interval_secs'])

        except KeyboardInterrupt:
            print("\nShutting down InfluxDB logging...")
            db_client.close()
            gv.disconnect()
    else:
        print("Pump not running")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
