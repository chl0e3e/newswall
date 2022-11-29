#!/usr/bin/env python3
import os
import asyncio
import concurrent.futures
import threading
import datetime
import uuid
import base64
import time
import subprocess
import json
import traceback

from pymongo import MongoClient # sync mongodb
import motor.motor_asyncio # async mongodb

from xvfbwrapper import Xvfb
from xdotool import XdotoolWrapper

from aiohttp import web, WSMsgType
import aiohttp_jinja2
import jinja2

import janus

from buildutil import get_build_var, get_build_folder

chromedriver_path = get_build_var("chromedriver")
chrome_path = get_build_var("chrome")
profiles_path = get_build_folder("profiles")
sites_path = get_build_folder("sites")

import uc

def import_site(path):
    import importlib.util
    import sys
    name = os.path.basename(os.path.splitext(path)[0])
    print("Importing %s from %s" % (name, path))
    spec = importlib.util.spec_from_file_location(name, path)
    print(spec)
    site = importlib.util.module_from_spec(spec)
    sys.modules[name] = site
    print(site)
    spec.loader.exec_module(site)
    return site

class NewsWall:
    def __init__(self):
        self.mongo_url = "mongodb://localhost:27017/"
        self.mongo_database = "newswall"
        self.ucs = {}
        self.sites = {}
        self.sites_objs = {}
        self.clients = {}
        self.display_number = 0
        self.running = False

    def sync_start(self):
        threading.Thread(target=asyncio.run, args=[self.start()])
        newswall.start_site_threads()

    async def start(self):
        self.log_queue = janus.Queue()
        self.report_queue = janus.Queue()
        self.running = True

        self.start_async_mongodb_client()
        
        self.app = web.Application()
        self.app.add_routes(self.routes())
        aiohttp_jinja2.setup(self.app, loader=jinja2.FileSystemLoader(get_build_folder("templates")))

        asyncio.create_task(web._run_app(self.app))
        asyncio.create_task(self.log_queue_loop())
        asyncio.create_task(self.report_queue_loop())

    def routes(self):
        return [
            web.get('/', self.handle_index),
            web.get('/main', self.handle_websocket),
            web.static('/static', get_build_folder("static")),
            web.static('/images', get_build_folder("images"))
        ]

    async def log_queue_loop(self):
        async_q = self.log_queue.async_q
        while self.running:
            q_el = await async_q.get()
            for ws in self.clients.keys():
                await ws.send_str(json.dumps({"cmd": "log", "log": q_el}))
            async_q.task_done()

    async def report_queue_loop(self):
        async_q = self.report_queue.async_q
        while self.running:
            q_el = await async_q.get()
            for ws, filter in self.clients.items():
                await ws.send_str(json.dumps({"cmd": "report", "report": [q_el]}))
            async_q.task_done()

    @aiohttp_jinja2.template('app.jinja2')
    async def handle_index(self, request):
        return {}

    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients[ws] = None

        await ws.send_str(json.dumps({"cmd": "sites", "sites": self.sites_objs}))

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(msg.data)
                if data["cmd"] == "filter" and "filter" in data:
                    self.clients[ws] = data["filter"]
                    aggregation = []
                    sites = list(data["filter"].keys())
                    first_site = sites.pop(0)
                    for site in sites:
                        aggregation.append({
                            "$unionWith": site
                        })

                    docs = []
                    async for doc in self.async_mongodb_database[first_site].aggregate(aggregation):
                        docs.append(doc)
                    await ws.send_str(json.dumps({"cmd": "report", "report": docs}, default=str))

    async def stop(self):
        self.stop_sync_mongodb_client()
        self.stop_async_mongodb_client()

        await self.app.shutdown()

    def start_site_threads(self):
        self.start_sync_mongodb_client()

        for site_path in os.listdir(sites_path):
            if not site_path.endswith(".py"):
                continue
            site_path = os.path.join(sites_path, site_path)
            if not site_path in self.sites:
                site_module = import_site(site_path)
                print("%s imported" % site_path)
                self.sites[site_path] = site_module
                site_class = getattr(site_module, site_module.__type__)
                print("%s found" % site_module.__type__)
                site_obj = site_class(self)
                self.sites_objs[site_obj.id] = site_obj.name
                print("%s instantiated" % site_obj.__class__)
                if site_obj.id == "bbc":
                    thread = threading.Thread(target=site_obj.start, args=[])
                    thread.start()
                print("%s thread started" % site_path)
            else:
                print("%s already imported" % (site_path))

    def start_sync_mongodb_client(self):
        print("Attempting to connect to MongoDB synchronously")
        self.sync_mongodb_client = MongoClient(self.mongo_url)
        self.sync_mongodb_database = self.sync_mongodb_client[self.mongo_database]
        info = self.sync_mongodb_client.server_info()
        self.sync_log("db", "Application connected to MongoDB (%s) synchronously" % (info["version"]))

    def stop_sync_mongodb_client(self):
        self.sync_log("db", "Shutting down synchronous MongoDB client")
        self.sync_mongodb_client.close()

    def start_async_mongodb_client(self):
        print("Attempting to connect to MongoDB asynchronously")
        self.async_mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(self.mongo_url)
        self.async_mongodb_database = self.async_mongodb_client[self.mongo_database]
        self.sync_log("db", "Application connected to MongoDB asynchronously")

    def stop_async_mongodb_client(self):
        self.sync_log("db", "Shutting down asynchronous MongoDB client")
        self.async_mongodb_client.close()
    
    def get_image_path(self, site, id, ext="png"):
        images_folder = get_build_folder("images")
        site_images_folder = os.path.join(images_folder, site)
        if not os.path.exists(images_folder): os.mkdir(images_folder)
        if not os.path.exists(site_images_folder): os.mkdir(site_images_folder)
        image_filename = id + "." + ext
        image_path = os.path.join(site_images_folder, image_filename)
        return {
            "path": image_path,
            "url": "/images/" + site + "/" + image_filename
        }

    def sync_find_if_exists(self, site, id):
        return self.sync_mongodb_database[site].find_one({"report_id": id})

    def sync_report(self, site, id, data):
        return self.sync_mongodb_database[site].insert_one({"report_id": id, "report_date": datetime.datetime.utcnow(), **data})
    
    def sync_insert_presence(self, site, db_id, date):
        return self.sync_mongodb_database[site].update_one({"_id": db_id}, {"$push": {"presence": date}})

    def sync_log(self, source, message, exception=None):
        log_line = {"date": datetime.datetime.utcnow(), "source": source, "text": message}
        if exception != None:
            log_line["exception"] = exception

        logs = self.sync_mongodb_database["log"]
        log_id = logs.insert_one(log_line).inserted_id
        log_line["_id"] = log_id

        self.log_queue.sync_q.put(log_line)
        
        print("[%s] [%s] [%s] %s" % (str(log_id), source, log_line["date"], message))
        if exception != None:
            print(exception)
        return log_id

    def sync_uc(self, name, headless=False):
        if name in self.ucs:
            return self.ucs[name]

        options = uc.ChromeOptions()
        if headless:
            options.headless = True
            options.add_argument('--headless')

        # vdisplay = Xvfb(display=self.display_number)
        # vdisplay.start()

        display = "172.21.80.1:0.0"

        profile_dir = os.path.join(profiles_path, name)
        driver = uc.Chrome(options=options,
            driver_executable_path=chromedriver_path,
            browser_executable_path=chrome_path,
            log_level=10,
            display=display)
        self.ucs[name] = driver

        # find the window ID for this window
        window_uuid = uuid.uuid4()
        window_uuid_str = str(window_uuid)
        self.sync_log(name, "uuid: %s" % window_uuid_str)
        html_with_uuid_title = "<!DOCTYPE html><html><head><title>" + window_uuid_str + "</title></head><body></body></html>"
        self.sync_log(name, "uuidhtml: %s" % html_with_uuid_title)
        window_uuid_url = "data:text/html;charset=utf-8;base64," + base64.b64encode(html_with_uuid_title.encode("ASCII")).decode('ASCII')
        self.sync_log(name, "uuidurl: %s" % window_uuid_url)
        driver.get(window_uuid_url)
        self.sync_log(name, "Navigated to window finder data URL")
        xdotool = XdotoolWrapper(display, window_uuid)
        self.sync_log(name, "XdotoolWrapper created, window: %d" % (xdotool.window_id))

        return xdotool, driver

if __name__ == "__main__":
    newswall = NewsWall()

    newswall.sync_start()