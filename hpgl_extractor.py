#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# by Will Kamp <manimaul!gmail.com>
# use this anyway you want

from xml.dom.minidom import parseString
import os
import json
import subprocess as sp
import atexit

f = open("chartsymbols.xml", "r")
lines = f.read()
f.close()

script_dir = os.path.dirname(os.path.realpath(__file__))


def cleanup(container):
    print("kill container <{}>".format(sp.getoutput("docker kill {}".format(container))))


def build_container_image():
    print("building hpgl image...")
    print(sp.getoutput("docker build -t hpgl {}".format(script_dir)))


def hpgl_line_styles_symbols_patterns(filter_set: set = set(["BOYCAN01"])):
    dom = parseString(lines)
    result = {
        "linestyles": [],
        "symbols": [],
        "patterns": [],
    }
    for line_style in dom.getElementsByTagName("line-style"):
        item = dict()
        item["name"] = line_style.getElementsByTagName("name")[0].firstChild.nodeValue
        item["description"] = line_style.getElementsByTagName("description")[0].firstChild.nodeValue
        item["hpgl"] = line_style.getElementsByTagName("HPGL")[0].firstChild.nodeValue
        item["color_ref"] = line_style.getElementsByTagName("color-ref")[0].firstChild.nodeValue
        result["linestyles"].append(item)
    for line_style in dom.getElementsByTagName("pattern"):
        item = dict()
        item["name"] = line_style.getElementsByTagName("name")[0].firstChild.nodeValue
        item["description"] = line_style.getElementsByTagName("description")[0].firstChild.nodeValue
        item["definition"] = line_style.getElementsByTagName("definition")[0].firstChild.nodeValue
        item["filltype"] = line_style.getElementsByTagName("filltype")[0].firstChild.nodeValue
        item["spacing"] = line_style.getElementsByTagName("spacing")[0].firstChild.nodeValue
        try:
            item["hpgl"] = line_style.getElementsByTagName("HPGL")[0].firstChild.nodeValue
            item["color_ref"] = line_style.getElementsByTagName("color-ref")[0].firstChild.nodeValue
            result["patterns"].append(item)
        except:
            print("skipping {}".format(item["name"]))
            pass

    for symbol in dom.getElementsByTagName("symbol"):
        item = dict()
        try:
            name = symbol.getElementsByTagName("name")[0].firstChild.nodeValue
            item["name"] = name
            if filter_set is not None and name not in filter_set:
                continue
            vector = symbol.getElementsByTagNameNS("*", "vector")[0]
            item["width"] = int(vector.attributes["width"].value)
            item["height"] = int(vector.attributes["height"].value)
            item["distance_min"] = int(vector.getElementsByTagName("distance")[0].attributes["min"].value)
            item["distance_max"] = int(vector.getElementsByTagName("distance")[0].attributes["max"].value)
            item["pivot_x"] = int(vector.getElementsByTagName("pivot")[0].attributes["x"].value)
            item["pivot_y"] = int(vector.getElementsByTagName("pivot")[0].attributes["y"].value)
            item["origin_x"] = int(vector.getElementsByTagName("origin")[0].attributes["x"].value)
            item["origin_y"] = int(vector.getElementsByTagName("origin")[0].attributes["y"].value)
            item["hpgl"] = vector.getElementsByTagName("HPGL")[0].firstChild.nodeValue
            result["symbols"].append(item)
        except Exception as error:
            print("skipping {} error = {}".format(item["name"], error))
            pass

    hpgl_dir = os.path.join(script_dir, "out/hpgl")
    os.makedirs(hpgl_dir, exist_ok=True)
    with open(os.path.join(hpgl_dir, "hpgl_items.json"), "w") as hpgl_json:
        json.dump(result, fp=hpgl_json)

    container = sp.getoutput("docker run -dit -w /hpgl -v {}:/hpgl hpgl".format(hpgl_dir))
    print("container running {}".format(container))
    atexit.register(cleanup, container)

    for group in result:
        out_dir = os.path.join(hpgl_dir, group)
        os.makedirs(out_dir, exist_ok=True)
        for each in result[group]:
            name = each["name"]
            hpgl_name = "{}.hpgl".format(name)
            with open(os.path.join(out_dir, hpgl_name), "w") as hpgl:
                hpgl.write(each["hpgl"])
            print(sp.getoutput("docker exec -w /hpgl {} hp2xx -r 180 -m svg /hpgl/{}/{}".format(container, group, hpgl_name)))
            uid = os.getuid()
            print(sp.getoutput("docker exec -w /hpgl {} chown {}:{} /hpgl/{}/{}.svg".format(container, uid, uid, group, hpgl_name)))
            svg_name = os.path.join(out_dir, "{}.hpgl.svg".format(name))
            with open(svg_name, "r+") as svg:
                data = svg.read().replace("stroke:rgb(255,255,255); fill:none; stroke-width:0.100mm", "stroke:rgb(0,0,0); fill:none; stroke-width:4mm")
                svg.seek(0)
                svg.write(data)
                svg.truncate()

            # width = sp.getoutput('inkscape --batch-process --actions="select-all;SelectionGroup;query-width;" {}'.format(svg_name))
            print(sp.getoutput('inkscape --batch-process '
                               '--actions "select-all" '
                               '--verb "ObjectFlipHorizontally;FitCanvasToDrawing;FileSave;FileClose" {}'.format(svg_name)))
            # inkscape --action-list | less
            # inkscape --verb-list | less
            svg_opt_name = os.path.join(out_dir, "{}.svg".format(name))
            print(sp.getoutput('scour -i {} -o {}'.format(svg_name, svg_opt_name)))
            # print(sp.getoutput('inkscape --export-plain-svg={} {}'.format(svg_name, svg_name)))


if __name__ == '__main__':
    build_container_image()
    hpgl_line_styles_symbols_patterns(filter_set=None)
