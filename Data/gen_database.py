#!/usr/bin/python
import json
import re
import requests

import sys
import time
import traceback

f = open("elec1.json", 'r')
data = f.read().split("\n")
data_buffer = ""
f.close()

visited = []

for l in range(0, len(data), 5):
    d = json.loads(data[l])
    if d["asin"] not in visited:
        try:
            url = "https://www.amazon.com/dp/" + d["asin"]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}
            item = requests.get(url, headers=headers).content

            item_name = re.search(r"""<title>Amazon.com(.*)<\/title>""", item)
            item_img = re.search(
                r"""[\s]*\'colorImages\':.*""", item)
            item = item.replace("\n", "")
            item_desc = re.search(
                r"""<div id=\"productDescription\" class.*<p>.*<\/p>""", item)
            item_cat = re.search(
                r"""\<li class="a-breadcrumb-divider"\>(.*?)\<a(.*?)\>(.*?)<\/a>""", item)

            name = item_name.group(1)
            name = name.split(":")[1].strip()
            img = item_img.group(0)
            img = re.sub("_.*_", "_SX200_", img[img.find("https"):img.find("jpg")+3])
            desc = item_desc.group(0)
            desc = desc[desc.find("p>") + 2:desc.find("</p")]
            cat = item_cat.group(3)
            cat = filter(lambda a: a != "", cat.split("  "))[0]

            reviewrs = []
            review_text = []
            for i in range(l, l + 3):
                r = json.loads(data[i])
                reviewrs.append(r["reviewerName"])
                review_text.append(r["reviewText"])

            rs = ">>>".join(reviewrs)
            rs_txt = "<<<".join(review_text)

            # print name
            # print img
            # print desc
            # print cat
            s = ":::".join([name, d["asin"].decode('utf-8'), cat, desc, img, rs, rs_txt, url])
            print s
            data_buffer = data_buffer + s + "\n"
        except Exception, e:
            # exc_type, exc_value, exc_traceback = sys.exc_info()
            # print("*** extract_tb:")
            # print(repr(traceback.extract_tb(exc_traceback)))
            # print("EXCEPTION:"+e.__str__())
            traceback.print_exc()
            print "\n OOPS:" + data[l] + "\n"
            pass

        time.sleep(2)
    visited.append(d["asin"])
target = open("1_amazon.txt", 'w')
target.truncate()
target.write(data_buffer)
target.close()
