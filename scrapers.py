#!/usr/bin/env python3
import os
import datetime
import json
import time
import sys
import argparse
import importlib.util
import sys

from operator import itemgetter

from threading import Thread
from multiprocessing import Process

from enum import Enum

from pymongo import MongoClient # sync mongodb

from helper import Helper
from buildutil import get_config_path, get_build_root

verbose = False

class InvalidProgramArgumentException(Exception):
    pass

class ConfigurationException(Exception):
    pass

class ConfigurationNotFoundException(ConfigurationException):
    pass

class ScriptFileNotFoundException(ConfigurationException):
    pass

class ApplicationException(Exception):
    pass

class DatabaseConnectionFailedException(ApplicationException):
    pass

class DatabaseNotConnectedException(ApplicationException):
    pass

class ConfigurationNotLoadedException(ApplicationException):
    pass

class ScriptNotConfiguredException(ApplicationException):
    pass

class ScriptNotEnabledException(ApplicationException):
    pass

class NoScriptsEnabledException(ApplicationException):
    pass

class ScriptNotFoundException(ApplicationException):
    pass

class ScraperAlreadyRunningException(ApplicationException):
    pass

class ConcurrencyMode(Enum):
    SINGLE = "single"
    THREADING = "threading"
    MULTIPROCESSING = "multiprocessing"

class ScraperManager:
    def __init__(self, configuration_path="config.json", verbose=True, sigkill_child_processes=True, disable_xvfb=False):
        if not os.path.exists(configuration_path):
            raise ConfigurationNotFoundException("The configuration file specified does not exist.")
        with open(configuration_path) as f:
            self.configuration = json.load(f)
        self.verbose = verbose
        self.sigkill_child_processes = sigkill_child_processes
        self.disable_xvfb = disable_xvfb
        self.sync_mongodb_client = None
        self.sync_mongodb_database = None
        self.concurrency_mode = ConcurrencyMode.SINGLE
        self.scrapers = None

    def set_concurrency_mode(self, concurrency_mode):
        self.concurrency_mode = concurrency_mode

    def connect_to_database(self):
        print("Attempting to connect to MongoDB synchronously")
        try:
            self.sync_mongodb_client = MongoClient(self.configuration["database_url"])
            self.sync_mongodb_database = self.sync_mongodb_client[self.configuration["database_name"]]
        except Exception as e:
            raise DatabaseConnectionFailedException(e)

        info = self.sync_mongodb_client.server_info()
        self.log("Application connected to MongoDB (%s) synchronously" % (info["version"]))
        return info["version"]

    def shutdown(self):
        self.log("Shutting down: closing database connection")
        self.sync_mongodb_client.close()

    def log(self, line):
        log_line = {"date": datetime.datetime.utcnow(), "source": "scrapers", "text": line}
        log_line["_id"] = self.sync_mongodb_database["log"].insert_one(log_line).inserted_id
        
        if self.verbose:
            print("[%s] [%s] %s" % (log_line["source"], log_line["date"], line))

    def load_sites_from_configuration(self):
        def _import_site(path):
            if not os.path.exists(path):
                raise ScriptNotFoundException("The script referenced existing at '%s' was not found." % (path))
            name = os.path.basename(os.path.splitext(path)[0])
            spec = importlib.util.spec_from_file_location(name, path)
            site = importlib.util.module_from_spec(spec)
            sys.modules[name] = site
            spec.loader.exec_module(site)
            return site

        scrapers = {}

        for site_identifier, site_configuration in self.configuration["sites"].items():
            for site_configuration_property in ["name", "enabled", "path", "class"]:
                if not site_configuration_property in site_configuration:
                    raise ConfigurationException("Configuration for site '%s' does not contain the '%s' property" % (site_identifier, site_configuration_property))
            
            if not ".py" in site_configuration["path"]:
                site_configuration["path"] = site_configuration["path"] + ".py"

            site_path = os.path.join(get_build_root(), site_configuration["path"])
            if not os.path.exists(site_path):
                raise ScriptFileNotFoundException("Site '%s' cannot be found at %s" % (site_identifier, site_path))

            self.log("Importing '%s' @ '%s'" % (site_identifier, site_path))
            module = _import_site(site_path)

            module_class = getattr(module, site_configuration["class"])

            scrapers[site_identifier] = {
                "identifier": site_identifier,
                "running": False,
                "last_run": 0,
                "enabled": site_configuration["enabled"],
                "class": module_class,
                "configuration": site_configuration,
                "runs": 0
            }

        self.scrapers = scrapers

        return self.scrapers.keys()

    def set_site_override(self, site_override_identifier):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to set an override.")

        if not site_override_identifier in self.scrapers:
            raise ScriptNotConfiguredException("The site attempting to run was not loaded from the configuration file.")

        for site_identifier in self.scrapers.keys():
            self.scrapers[site_identifier]["enabled"] = site_identifier == site_override_identifier

    def get_scraper_identifiers(self):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        return self.scrapers.keys()

    def get_scraper_identifiers_by_last_run(self):
        identifiers = []
        for value in sorted(self.scrapers.values(), key=lambda d: d['last_run']):
            identifiers.append(value["identifier"])
        return identifiers

    def get_num_scrapers_enabled(self):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        return sum(1 for site_identifier in list(self.scrapers.keys()) if self.scrapers[site_identifier]["enabled"])

    def get_num_scrapers_running(self):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        return sum(1 for site_identifier in list(self.scrapers.keys()) if self.scrapers[site_identifier]["running"])

    def is_scraper_enabled(self, site_identifier):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        if not site_identifier in self.scrapers:
            raise ScriptNotConfiguredException("The site attempting to run was not loaded from the configuration file.")

        return self.scrapers[site_identifier]["enabled"]

    def is_scraper_running(self, site_identifier):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        if not site_identifier in self.scrapers:
            raise ScriptNotConfiguredException("The site attempting to run was not loaded from the configuration file.")

        return self.scrapers[site_identifier]["running"]

    def set_site_finished(self, site_identifier):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        if not site_identifier in self.scrapers:
            raise ScriptNotConfiguredException("The site attempting to run was not loaded from the configuration file.")

        self.scrapers[site_identifier]["last_run"] = time.time()
        self.scrapers[site_identifier]["running"] = False
        self.scrapers[site_identifier]["runs"] += 1
        
    def get_scraper_information(self, site_identifier):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to access the scraper information.")

        if not site_identifier in self.scrapers:
            raise ScriptNotConfiguredException("The site attempting to run was not loaded from the configuration file.")

        return self.scrapers[site_identifier]

    def start_scraper(self, site_identifier):
        if self.scrapers == None:
            raise ConfigurationNotLoadedException("You must call `ScraperManager.load_sites_from_configuration` before attempting to start a scraper.")

        if not site_identifier in self.scrapers:
            raise ScriptNotConfiguredException("The site attempting to run was not loaded from the configuration file.")

        if self.sync_mongodb_client == None:
            raise DatabaseNotConnectedException("You must call `ScraperManager.connect_to_database` before starting a scraper.")

        if self.scrapers[site_identifier]["running"]:
            raise ScraperAlreadyRunningException("The scraper you have attempted to run is already running.")

        if not self.scrapers[site_identifier]["enabled"]:
            raise ScriptNotEnabledException("The scraper you attempted to run is not enabled.")

        site_configuration = self.configuration["sites"][site_identifier]
        
        def entrypoint():
            try:
                sync_mongodb_client = MongoClient(self.configuration["database_url"])
                sync_mongodb_database = sync_mongodb_client[self.configuration["database_name"]]
                site_helper = Helper(site_identifier, site_configuration["name"], sync_mongodb_database, self.sigkill_child_processes, self.disable_xvfb)
                site_object = self.scrapers[site_identifier]["class"](site_helper)
                site_object.start()
            except Exception as e:
                self.log("ScraperManager caught an error on site '%s': %s" % (site_identifier, str(e)), exception=e)
            finally:
                self.log("ScraperManager site finished: '%s'" % site_identifier)

        self.log("Starting scraper '%s'" % site_identifier)

        self.scrapers[site_identifier]["running"] = True

        if self.concurrency_mode == ConcurrencyMode.SINGLE:
            entrypoint()
            return True
        elif self.concurrency_mode == ConcurrencyMode.THREADING:
            thread = Thread(target=entrypoint)
            thread.start()
            return thread
        elif self.concurrency_mode == ConcurrencyMode.MULTIPROCESSING:
            process = Process(target=entrypoint)
            process.start()
            return process

class ScraperScheduler:
    def __init__(self, scraper_manager, concurrency_maximum, concurrency_interval):
        self.scraper_manager = scraper_manager
        self.concurrency_maximum = concurrency_maximum
        self.concurrency_interval = concurrency_interval
        self.tasks = {}

    def run_iteration(self):

        scrapers_running = self.scraper_manager.get_num_scrapers_running()
        if scrapers_running < self.concurrency_maximum:
            scrapers_starting = self.concurrency_maximum - scrapers_running
            
            for site_identifier in self.scraper_manager.get_scraper_identifiers_by_last_run():
                site_information = self.scraper_manager.get_scraper_information(site_identifier)

                def scraper_runnable():
                    if not site_information["enabled"]:
                        return False
                    if site_information["running"]:
                        return False
                    if site_information["last_run"] == 0:
                        return True
                    if ((time.time() - site_information["last_run"]) > self.concurrency_interval):
                        return True
                    else:
                        return False

                if scraper_runnable():
                    self.tasks[site_identifier] = self.scraper_manager.start_scraper(site_identifier)
                    scrapers_starting -= 1
                    if scrapers_starting == 0:
                        break
            
            return self.concurrency_maximum - scrapers_running != scrapers_starting
        else:
            return False

    def find_dead_tasks(self):
        dead_tasks = []
        for site_identifier in list(self.tasks.keys()):
            site_task_instance = self.tasks[site_identifier]

            if type(site_task_instance) == Thread or type(site_task_instance) == Process:
                if not site_task_instance.is_alive():
                    dead_tasks.append(site_identifier)
                    self.scraper_manager.set_site_finished(site_identifier)
                    del self.tasks[site_identifier]
            else:
                if site_task_instance:
                    dead_tasks.append(site_identifier)
                    self.scraper_manager.set_site_finished(site_identifier)
                    del self.tasks[site_identifier]
        return dead_tasks

def parse_args():
    parser = argparse.ArgumentParser(
                    prog = "newswall Scrapers",
                    description = "This program starts the scrapers and uses a scheduler to run them.",
                    epilog = "For multiprocessing mode, it is recommended to use sigkill_child_processes")

    parser.add_argument("configuration_path", action="store", type=str, default=get_config_path(), help="Path to the configuration file to load and use")
    parser.add_argument("-m", "--concurrency-mode", dest="concurrency_mode", action="store", type=str, default="multiprocessing", help="Run the tasks in a certain concurrency mode (single = single site mode, threading = threaded mode, multiprocessing = multiprocessing mode)")
    parser.add_argument("-n", "--concurrency-maximum", dest="concurrency_maximum", action="store", type=int, default=5, help="A number to denote the instances of scrapers to run concurrently")
    parser.add_argument("-t", "--concurrency-interval", dest="concurrency_interval", action="store", type=int, default=1800, help="The interval between launching the number of tasks specified as the concurrency maximum")
    parser.add_argument("-s", "--sigkill-child-processes", dest="sigkill_child_processes", action="store_true", default=False, help="Send SIGKILL to all child processes after running the scraper")
    parser.add_argument("-o", "--override-site", dest="override_site", action="store", type=str, default="", help="Override the configuration and only start the specified site")
    parser.add_argument("-x", "--disable-xvfb", dest="disable_xvfb", action="store_true", default=False, help="Disable headless Xvfb and use DISPLAY from script environment")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=True)

    return parser, parser.parse_args()

def main():
    parser, args = parse_args()

    try:
        concurrency_mode = ConcurrencyMode(args.concurrency_mode)
    except:
        raise InvalidProgramArgumentException("Concurrency mode '%s' was not found")

    manager = ScraperManager(args.configuration_path, sigkill_child_processes=args.sigkill_child_processes)
    manager.set_concurrency_mode(concurrency_mode)
    
    try:
        version = manager.connect_to_database()
        print("ScraperManager connected to database (MongoDB v%s)" % version)
    except ApplicationException as application_exception:
        print(application_exception.message)
        sys.exit(1)

    try:
        manager.load_sites_from_configuration()
    except ConfigurationException as configuration_exception:
        print(configuration_exception.message)
        sys.exit(2)

    if args.override_site != "":
        manager.set_site_override(args.override_site)

    if manager.get_num_scrapers_enabled() == 0:
        print("No scrapers are enabled")
        sys.exit(3)

    scheduler = ScraperScheduler(manager,
        concurrency_maximum=args.concurrency_maximum,
        concurrency_interval=args.concurrency_interval)

    running = True
    while running:
        scrapers_started = scheduler.run_iteration()
        if scrapers_started:
            manager.log("%d scrapers are running" % (manager.get_num_scrapers_running()))

        dead_tasks = scheduler.find_dead_tasks()
        if len(dead_tasks) > 0:
            manager.log("%d scrapers have ended" % len(dead_tasks))

        time.sleep(0.1)

    manager.shutdown()

if __name__ == "__main__":
    main()