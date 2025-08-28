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

    ## Connect to InfluxDB
    if verbose:
        print("Connecting to InfluxDB...")
    db_client = InfluxDBClient(url=cfg['url'], token=cfg['db_token'], org=cfg['org'])
    write_api = db_client.write_api(write_options=SYNCHRONOUS)

    ## Connect to GammaVac SPCe
    if verbose:
        print("Connecting to SPCe controller...")
    gv = SPCe.SpceController(bus_address=cfg['gamma_bus_address'])  # set bus_address as appropriate
    gv.connect(host=cfg['gamma_host'], port=cfg['gamma_port'])      # Terminal Server IP and port

    ## Check pump status
    if 'Running' in gv.get_pump_status():
        gv.set_units("T")   # set units to Torr
        try:
            while True:
                pressure = gv.read_pressure()
                current = gv.read_current()
                voltage = gv.read_voltage()
                point = (
                    Point("gammavac")
                    .field("Torr", pressure)
                    .field("Amps", current)
                    .field("volts", voltage)
                    .tag("channel", f"{cfg['channel']}")
                )
                write_api.write(bucket=cfg['bucket'], org=cfg['org'], record=point)
                if verbose:
                    print(point)
                time.sleep(cfg['interval_secs'])
        except KeyboardInterrupt:
            print("Shutting down InfluxDB logging...")
            db_client.close()
            gv.disconnect()
    else:
        print("Pump not running")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
