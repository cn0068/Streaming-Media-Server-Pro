#!/usr/bin python3
# -*- coding: utf-8 -*-
import time
import aiohttp
import datetime
import asyncio

from xml.dom.minidom import Document

from app.settings import idata
from app.modules.DBtools import cur


def generatehead(tvdoc):
    tv = tvdoc.createElement("tv")
    tv.setAttribute("generator-info-name", "Generated by Naihe, 239144498@qq.com ")
    tv.setAttribute("generator-info-url", "qq 239144498")
    tvdoc.appendChild(tv)
    return tv


def generatebody1(tvdoc, tv, var):
    # channel 标签
    channel = tvdoc.createElement("channel")
    channel.setAttribute("id", str(var['fs4GTV_ID']))

    # display-name
    display_name = tvdoc.createElement("display-name")
    display_name.setAttribute("lang", "zh")
    # display-name 标签中的值
    display_name_var = tvdoc.createTextNode(var['fsNAME'])
    display_name.appendChild(display_name_var)
    # 添加到channel节点
    channel.appendChild(display_name)
    # 添加到根标签
    tv.appendChild(channel)


def generatebody2(tvdoc, tv, channel, data):
    TIME_ZONE = " +0800"
    for var in eval(data):
        start = var['sdate'].replace("-", "") + var['stime'].replace(":", "")
        stop = var['edate'].replace("-", "") + var['etime'].replace(":", "")
        pname = var['title']

        programme = tvdoc.createElement("programme")
        title = tvdoc.createElement("title")
        text = tvdoc.createTextNode(pname)

        programme.setAttribute("start", start + TIME_ZONE)
        programme.setAttribute("stop", stop + TIME_ZONE)
        programme.setAttribute("channel", channel)

        title.setAttribute("lang", "zh")

        title.appendChild(text)
        programme.appendChild(title)

        tv.appendChild(programme)


def generateprog(tvlist):
    tvdoc = Document()
    tv = generatehead(tvdoc)
    for var1 in tvlist:
        generatebody1(tvdoc, tv, var1)

    cursor1, data1 = cur.hscan(str(datetime.date.today()), cursor=0, count=70)
    cursor2, data2 = cur.hscan(str(datetime.date.today()), cursor=cursor1, count=70)
    data1.update(data2)
    tvs = data1
    for k, v in tvs.items():
        generatebody2(tvdoc, tv, k, v)
    return tvdoc.toprettyxml(indent="\t", encoding="UTF-8")


async def download(fid, now, i=0):
    if i > 10:
        raise Exception(f"下载节目单{fid}失败")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"https://www.4gtv.tv/proglist/{fid}.txt") as res:
                res.encoding = "utf-8"
                return cur.hset(now, fid, await res.text())
    except:
        return await download(fid, now, i + 1)


async def postask():
    start = time.time()
    print(start)
    now = str(datetime.date.today())
    fids = str(cur.hkeys(now))
    print(fids)
    tasks = []
    for fid in idata.keys():
        if fid in fids:
            continue
        tasks.append(download(fid, now))
    await asyncio.gather(*tasks)
    end = time.time()
    print("耗时: %s" % (end - start))
    cur.expire(now, 432000)


if __name__ == '__main__':
    # 不会用就用我做好的 https://agit.ai/239144498/demo/raw/branch/master/4gtvchannel.xml
    import platform

    if "Windows" in platform.platform():
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(postask())
    else:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        loop = asyncio.get_event_loop()
        task = asyncio.ensure_future(postask())
        loop.run_until_complete(asyncio.wait([task]))
