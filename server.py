#!/usr/bin/env python3
from concurrent.futures import ProcessPoolExecutor
import asyncio
import json
import datetime
import re

import motor.motor_asyncio # async mongodb

from aiohttp import web, WSMsgType
import aiohttp_jinja2
import jinja2

import aiofiles

from buildutil import get_build_folder, get_config_path

class NewsWall:
    def __init__(self):
        self.clients = {}
        self.running = False

    def routes(self):
        return [
            web.get('/', self.handle_index),
            web.get('/main', self.handle_websocket),
            web.static('/static', get_build_folder("static")),
            web.static('/images', get_build_folder("images"))
        ]

    async def config(self):
        async with aiofiles.open(get_config_path(), mode='r') as config_file_object:
            config = await config_file_object.read()
            return json.loads(config)

    async def sites(self, paths=False):
        config = await self.config()
        sites = {}
        for site, site_config in config["sites"].items():
            if not paths:
                site_config.pop('path', None)
            sites[site] = site_config
        return sites

    async def start(self):
        self.running = True
        config = await self.config()

        print("Attempting to connect to MongoDB asynchronously")
        self.async_mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(config["database_url"])
        self.async_mongodb_database = self.async_mongodb_client[config["database_name"]]
        await self.async_log("Application connected to MongoDB asynchronously")
        
        self.app = web.Application()
        self.app.add_routes(self.routes())
        aiohttp_jinja2.setup(self.app, loader=jinja2.FileSystemLoader(get_build_folder("templates")))

        await web._run_app(self.app)

    async def async_log(self, message, source="http", exception=None):
        log_line = {"date": datetime.datetime.utcnow(), "source": source, "text": message}
        if exception != None:
            log_line["exception"] = exception

        inserted_log_line = await self.async_mongodb_database["log"].insert_one(log_line)
        log_line["_id"] = inserted_log_line.inserted_id
        
        print("[%s] [%s] [%s] %s" % (str(log_line["_id"]), source, log_line["date"], message))
        if exception != None:
            print(exception)
        return log_line["_id"]

    @aiohttp_jinja2.template('app.jinja2')
    async def handle_index(self, request):
        return {}

    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients[ws] = None

        async def send(data):
            await ws.send_str(json.dumps(data, default=str))

        async def build_aggregation(data):
            aggregation = []

            if not data["type"] == "root":
                await self.async_log("Error building aggregation: no root")
                return

            if not "children" in data:
                await self.async_log("Error building aggregate: no root children found")
                return

            for site_node in data["children"]:
                if not "type" in site_node:
                    await self.async_log("Error building aggregate: no type in child")
                    return
                if not "filter" in site_node:
                    await self.async_log("Error building aggregate: no filter in child")
                    return
                if not "value" in site_node:
                    await self.async_log("Error building aggregate: no value in child")
                    return
                
                if not site_node["type"] == "rule":
                    await self.async_log("Error building aggregate: root node is not a rule")
                    return

                if not site_node["filter"] == "site":
                    await self.async_log("Error building aggregate: root filter is not a site")
                    return
                
                failed = False
                async def traverse(node):
                    if not "type" in node:
                        await self.async_log("Error building aggregate: node does not contain type")
                        return False
                    
                    if node["type"] == "group":
                        if not "children" in node:
                            await self.async_log("Error building aggregate: group node does not contain children")
                            return False

                        if not "condition" in node:
                            await self.async_log("Error building aggregate: group node does not contain condition")
                            return False

                        aggregate_cond = "$or" if node["condition"] == "OR" else "$and"
                        aggregate_cond_expressions = []

                        for child_node in node["children"]:
                            aggregate_cond_expressions.append(await traverse(child_node))
                            if failed:
                                return False

                        return {
                            aggregate_cond: aggregate_cond_expressions
                        }
                    elif node["type"] == "rule":
                        if not "operator" in node:
                            await self.async_log("Error building aggregate: rule node does not contain operator")
                            return False

                        if not "value" in node:
                            await self.async_log("Error building aggregate: rule node does not contain value")
                            return False

                        if not "filter" in node:
                            await self.async_log("Error building aggregate: rule node does not contain filter")
                            return False

                        if node["operator"] == "equals":
                            return {
                                node["filter"]: node["value"]
                            }
                        elif node["operator"] == "contains":
                            return {
                                node["filter"]: {
                                    "$regex": re.escape(node["value"])
                                }
                            }
                        elif node["operator"] == "regex":
                            return {
                                node["filter"]: {
                                    "$regex": node["value"]
                                }
                            }
                        elif node["operator"] == "regex_case_insensitive":
                            return {
                                node["filter"]: {
                                    "$regex": node["value"],
                                    "$options": "i"
                                }
                            }

                if failed:
                    return []
                
                aggregate_union = {
                    "$unionWith": {
                        "coll": site_node["value"],
                        "pipeline": []
                    }
                }

                if len(site_node["children"]) > 0:
                    for child_node in site_node["children"]:
                        aggregate_union["$unionWith"]["pipeline"] = [{"$match": await traverse(child_node)}]

                aggregate_union["$unionWith"]["pipeline"].append({
                    "$addFields": {
                        "site": site_node["value"]
                    }
                })

                aggregation.append(aggregate_union)

            return aggregation

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(msg.data)
                if "cmd" in data:
                    if data["cmd"] == "sites":
                        sites = await self.sites()
                        await send({
                            "cmd": "sites",
                            "data": sites
                        })

                    if data["cmd"] == "query":
                        print("Received query")
                        aggregation = await build_aggregation(data["data"])
                        aggregation.append({ "$sort": { "_id" : -1} })
                        aggregation.append({ "$limit": 100 })
                        print(aggregation)
                        docs = []
                        async for doc in self.async_mongodb_database["empty"].aggregate(aggregation):
                            docs.append(doc)
                        await ws.send_str(json.dumps({"cmd": "report", "report": docs}, default=str))
                        
                    if data["cmd"] == "filter" and "filter" in data:
                        self.clients[ws] = data["filter"]
                        aggregation = []
                        sites = list(data["filter"].keys())
                        first_site = sites.pop(0)
                        for site in sites:
                            aggregation.append({
                                "$unionWith": site
                            })

                        aggregation.append({ "$sort": { "_id" : -1} })
                        aggregation.append({ "$limit": 100 })

                        docs = []
                        async for doc in self.async_mongodb_database[first_site].aggregate(aggregation):
                            docs.append(doc)
                        await ws.send_str(json.dumps({"cmd": "report", "report": docs}, default=str))

    async def stop(self):
        await self.async_log("Shutting down asynchronous MongoDB client")
        self.async_mongodb_client.close()

        await self.app.shutdown()

if __name__ == "__main__":
    newswall = NewsWall()

    loop = asyncio.new_event_loop()
    loop.create_task(newswall.start())
    loop.run_forever()