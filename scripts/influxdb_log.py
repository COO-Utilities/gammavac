"""Script for logging to InfluxDB."""
import time
import sys
import json
import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from urllib3.exceptions import ReadTimeoutError

import SPCe

# cfg_file = files('scripts'), 'influxdb_config.json')

def main(config_file):
    """Query user for setup info and start logging to InfluxDB."""

    ## read config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    # Do we have a logfile?
    if cfg['logfile'] is not None:
        # log to a file
        logger = logging.getLogger(cfg['logfile'])
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(cfg['logfile'])
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        logger = None

    # Connect to GammaVac SPCe
    if verbose:
        print("Connecting to SPCe controller...")
    if logger:
        logger.info('Connecting to InfluxDB...')
    gv = SPCe.SpceController(bus_address=cfg['gamma_bus_address'])  # set bus_address as appropriate
    gv.connect(host=cfg['device_host'], port=cfg['device_port'])      # Terminal Server IP and port

    ## Check pump status
    if 'Running' in gv.get_pump_status():
        gv.set_units("T")  # set units to Torr

        # Try/except to catch exceptions
        db_client = None
        try:
            # Loop until ctrl-C
            while True:
                try:
                    # Connect to InfluxDB
                    if verbose:
                        print("Connecting to InfluxDB...")
                    if logger:
                        logger.info('Connecting to InfluxDB...')
                    db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'],
                                               org=cfg['db_org'])
                    write_api = db_client.write_api(write_options=SYNCHRONOUS)

                    # Pressure
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
                    if logger:
                        logger.debug(ppoint)

                    # Current
                    current = gv.read_current()
                    cpoint = (
                        Point("gammavac")
                        .field("current", current)
                        .tag("units", "Amps")
                        .tag("channel", f"{cfg['db_channel']}")
                    )
                    write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=cpoint)
                    if verbose:
                        print(cpoint)
                    if logger:
                        logger.debug(cpoint)

                    # Voltage
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
                    if logger:
                        logger.debug(vpoint)

                    # Close db connection
                    if verbose:
                        print("Closing connection to InfluxDB...")
                    if logger:
                        logger.info("Closing connection to InfluxDB...")
                    db_client.close()
                    db_client = None

                # Handle exceptions
                except ReadTimeoutError as e:
                    print(f"ReadTimeoutError: {e}, will retry.")
                    if logger:
                        logger.critical("ReadTimeoutError: %s, will retry.", e)
                except Exception as e:
                    print(f"Unexpected error: {e}, will retry.")
                    if logger:
                        logger.critical("Unexpected error: %s, will retry.", e)

                # Sleep for interval_secs
                if verbose:
                    print(f"Waiting {cfg['interval_secs']} seconds...")
                if logger:
                    logger.info("Waiting %d seconds...", cfg['interval_secs'])
                time.sleep(cfg['interval_secs'])

        except KeyboardInterrupt:
            print("\nShutting down InfluxDB logging...")
            if logger:
                logger.critical("Shutting down InfluxDB logging...")
            if db_client:
                db_client.close()
            gv.disconnect()
    else:
        print("Pump not running")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
