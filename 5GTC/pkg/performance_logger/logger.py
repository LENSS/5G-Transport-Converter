import logging
import time
import sys
import argparse
import threading
from pkg.performance_logger.db import DB
from pkg.performance_logger.webui import WebUI
from pkg.performance_logger.util import random_iteration_id_string
from mptcp_util import *

logger = logging.getLogger("performance_logger")
logger.setLevel(logging.DEBUG)

FILTER_COLUMNS = [
    "id",
    "tcpi_state",
    "tcpi_ca_state",
]

class PerformanceLogger:
    """
    This class is used to log performance metrics for an MPTCP connection
    It exposes a run a background thread that periodically logs the metrics
    and can be stopped by calling stop() which writes the metrics to a file 
    specified by the user.
    """
    def __init__(self, sock, log="INFO"):
        # WebUI is already initialized in main.py
        # No need to pass host and port
        logger.setLevel(log)
        self.webui = WebUI()
        self.sock = sock
        self.iteration_id = random_iteration_id_string()
        self._inserted_subflows_cache = {}
        self.webui.log_iteration_page(self.iteration_id)

    def __del__(self):
        self.stop()

    def init_db(self):
        self.db = DB({
            "db_path": "performance_log.db",
            "delete_db_on_exit": False
        })

    def run(self, interval_ms=1, features="all"):
        """
        Run the logger in a background thread
        """
        logger.info("Starting PerformanceLogger for connection between {} and {}".format(self.sock.getsockname(), self.sock.getpeername()))
        logger.debug("PerformanceLogger [fid: {}] Started".format(self.sock.fileno()))
        logger.debug("PerformanceLogger [fid: {}] Logging interval: {} ms".format(self.sock.fileno(), interval_ms))
        logger.debug("PerformanceLogger [fid: {}] Logging features: {}".format(self.sock.fileno(), features))

        self.interval_ms = interval_ms / 1000
        self.thread = threading.Thread(target=self._run_logger, args=(self.interval_ms, features,))
        self._thread_run = True
        self.thread.start()

    def stop(self):
        # Stop the logger thread
        self._thread_run = False
        self.thread.join()
        logger.debug("PerformanceLogger [fid: {}] Stopped".format(self.sock.fileno()))


    def _run_logger(self, interval_ms, features):
        #  We init the DB in the background thread since SQLite objects
        #  cannot be shared between threads
        self.init_db()
        if features == "all":
            self.measure_all = True
        else:
            self.measure_all = False
            # If features is not a list, throw an error
            if not isinstance(features, list):
                raise ValueError("Features must be a list")
        while self._thread_run:
            # Get the subflow TCP info
            subflow_tcp_info = get_subflow_tcp_info(self.sock.fileno())
            for subflow in subflow_tcp_info:
                sid = subflow["id"]
                # Add subflow to the subflows table if needed
                # Avoid DB reads by caching the subflows that have been inserted
                if sid not in self._inserted_subflows_cache:
                    # Get the local and remote IP addresses
                    subflow_info = get_subflow_info(self.sock.fileno())
                    # Filter the list by id
                    sinfo = list(filter(lambda x: x["id"] == sid, subflow_info))[0]
                    if not sinfo:
                        raise Exception("Subflow info not found for subflow id: {}".format(sid))
                    self.db.insert_subflow(self.iteration_id, sid, sinfo["local_addr"], sinfo["remote_addr"])
                    self._inserted_subflows_cache[sid] = True
                
                #  Filter out the features that are not needed
                subflow_features = list(subflow.keys())
                for feature in subflow_features:
                    if (feature in FILTER_COLUMNS) or (not self.measure_all and feature not in features):
                        del subflow[feature]

                # Insert the subflow TCP info into the DB
                self.db.insert_subflow_tcp_conn_info(self.iteration_id, sid, subflow)

            # Sleep for the interval assigned
            time.sleep(interval_ms)

        self.db.conn.close()


# Allow the PerformanceLogger to run as an independent module for
# on-server testing as opposed to just through a Transport Converter
if __name__ == "__main__":
    if len(sys.argv) < 2 or "".join(sys.argv).find("--help") != -1:
        print("Usage: python3 logger.py <socket fd> [--webui-host <host>] [--webui-port <port>] [--interval <interval>] [--features <features>] [--log <log>]")
        print("\t<socket fd>: Socket file descriptor to log performance metrics for")
        print("\t--webui-host <host>: Host to run the webui on")
        print("\t--webui-port <port>: Port to run the webui on")
        print("\t--interval <interval>: Interval in ms to log the performance metrics")
        print("\t--features <features>: Features to log")
        print("\t--log <log>: Log level")
        print("Example: python3 logger.py 3 --webui-host localhost --webui-port 5000 --interval 1000 --features all --log INFO")

        sys.exit(1)
    # Read the command line arguments
    parser = argparse.ArgumentParser(description="Performance Logger")
    parser.add_argument("sockfd", type=int, help="Socket file descriptor")
    parser.add_argument("--webui-host", type=str, default="localhost", help="Host to run the webui on")
    parser.add_argument("--webui-port", type=int, default=5000, help="Port to run the webui on")
    parser.add_argument("--interval", type=int, default=1000, help="Interval in ms to log the performance metrics")
    parser.add_argument("--features", type=str, default="all", help="Features to log")
    parser.add_argument("--log", type=str, default="INFO", help="Log level")
    args = parser.parse_args()

    # Initialize the WebUI module
    webui = WebUI(args.host, args.port, log=args.log)

    # Feature split by comma
    features = args.features.split(",")

    # Initialize the PerformanceLogger
    logger = PerformanceLogger(args.sockfd, log=args.log)

    # Run the logger
    logger.run(interval_ms=args.interval, features=features)

