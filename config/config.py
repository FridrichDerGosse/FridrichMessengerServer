from extra import BetterDict
import json
import os


class _Config:
    _data: dict

    def __init__(self):
        # directly write to dict, because getitem returns an error
        self.__dict__["_data"] = {}

        # iterate through the config directory and sort the config files by folder/filename
        vertices = os.listdir("./config/")
        for vertex in vertices:
            vertex_path = f"./config/{vertex}/"
            if not os.path.isdir(vertex_path):
                continue

            nodes = os.listdir(vertex_path)

            vertex_data = {}
            for node in nodes:
                if not node.endswith(".json"):
                    continue

                with open(f"./config/{vertex}/{node}", "r") as inp:
                    node_data = json.load(inp)

                vertex_data[node.rstrip(".json")] = node_data

            # only actually append if config files are found in the directory
            if vertex_data:
                self.__dict__["_data"][vertex] = vertex_data

    def __getattr__(self, item):
        return BetterDict(self._data[item])

    def __setattr__(self, key, value):
        raise PermissionError("Config Files are READ-ONLY!")


Config = _Config()
