# A Script for Checking Services Status and Alert automatically
# By Gopppog - ichaff@163.com
# Rebuilt Code in 2020-07-29

import os
import ssl
import datetime
import argparse
import logging
import time
import smtplib
import json
import traceback
from email.mime.text import MIMEText
from email.header import Header
from telnetlib import Telnet
from urllib import request
from pathlib import Path

class Head:

    def version(self):
        describe = "Braum @ Freljord is a Script for Checking Services Status and Alert automatically"
        author = "Gopppog"
        build_ver = "1.1"
        build_date = "2020.07.31"
        contact = "ichaff@163.com"
        print(describe)
        print("Version " + build_ver + " - build on " + build_date)
        print("by " + author + " # contact " + contact)
        exit(0)

    def getargs(self):
        parse = argparse.ArgumentParser()
        parse.add_argument("-s", "--silence", action="store_true", help="Running and dumping logs into /var/log/braum.log")
        parse.add_argument("-c", "--config", help="Use custom configuration path of CONFIG")
        parse.add_argument("-i", "--item", help="Use custom configuration path of ITEMS")
        parse.add_argument("-v", "--version", action="store_true", help="Output version and exit")
        return parse.parse_args()

    def getlog(self, log_path=None):
        log_format = "%(message)s"
        if log_path:
            logging.basicConfig(filename=log_path, level=logging.INFO, format=log_format)
        else:
            logging.basicConfig(level=logging.INFO, format=log_format)
        return logging.getLogger()

    def getjson(self, path):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None


class GetServiceStatus:

    def ping(self, host):
        retry = 3
        time_out = 3
        cmd = "ping " + host + " -c 1 -W " + time_out + " >/dev/null 2>&1"
        for n in range(retry):
            if os.system(cmd) == 0:
                return True
        return False

    def telnet(self, host, p):
        retry = 3
        time_out = 3
        for n in range(retry):
            try:
                with Telnet(host, port=p, timeout=time_out) as tel:
                    return True
            except:
                e = traceback.format_exc()
                pass
        logger.debug(e)
        return False

    def url(self, u):
        ssl._create_default_https_context = ssl._create_unverified_context
        retry = 3
        time_out = 3
        for n in range(retry):
            try:
                with request.urlopen(u, timeout=time_out) as resp:
                    if resp.code == 200:
                        return True
            except:
                e = traceback.format_exc()
                pass
        logger.debug(e)
        return False


class Items:

    def __init__(self, items, config):
        self.services = [ name for name in items["SERVICES"] ]
        self.telnet_services = [ name for name in self.services if items["SERVICES"][name]["check_method"] == "telnet" ]
        self.url_services = [ name for name in self.services if items["SERVICES"][name]["check_method"] == "url" ]
        self.ping_services = [ name for name in self.services if items["SERVICES"][name]["check_method"] == "ping" ]
        for method in config:
            if  method == config["alert_method"]:
                self.alertness = method
                break
            self.alertness = None

    def alertsend(self, msg):
        if self.alertness == None:
            pass
        elif self.alertness == "dgsdk":
            for rec_phone in config["dgsdk"]["receive_phone"]:
                sts = Alert().dgsdk(msg, rec_phone, config["dgsdk"]["sdk_api"])
                if sts:
                    logger.info("发送报警短信 To "+ rec_phone + " <Successfully>")
                else:
                    logger.info("发送报警短信 To " + rec_phone + " <Failed>")
        elif self.alertness == "mail":
            for rec_mail in config["mail"]["receive_mail"]:
                sts = Alert().mail(msg, rec_mail, config["mail"]["auth_mail_setting"])
                if sts:
                    logger.info("发送报警短信 To " + rec_mail + " <Successfully>")
                else:
                    logger.info("发送报警短信 To " + rec_mail + " <Failed>")

    def check(self):
        getstatus = GetServiceStatus()
        global success_count, failed_count
        for name in self.url_services:
            url = items["SERVICES"][name]["input"]["url"]
            if getstatus.url(url):
                output = name + " Checked -- > [正常]"
                logger.info(output)
                success_count += 1
            else:
                output = name + " Checked -- > [Error]"
                msg = str(name + "故障，请及时处理 %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                logger.info(output)
                self.alertsend(msg)
                failed_count += 1
        for name in self.telnet_services:
            host = items["SERVICES"][name]["input"]["host"]
            port = items["SERVICES"][name]["input"]["port"]
            if getstatus.telnet(host, port):
                output = name + " Checked -- > [正常]"
                logger.info(output)
                success_count += 1
            else:
                output = name + " Checked -- > [Error]"
                msg = str(name + "故障，请及时处理 %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                logger.info(output)
                self.alertsend(msg)
                failed_count += 1
        for name in self.ping_services:
            host = items["SERVICES"][name]["input"]["host"]
            if getstatus.ping(host):
                output = name + " Checked -- > [正常]"
                logger.info(output)
                success_count += 1
            else:
                output = name + " Checked -- > [Error]"
                msg = str(name + "故障，请及时处理 %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                logger.info(output)
                self.alertsend(msg)
                failed_count += 1


class Alert:

    def mail(self, mesg, rec, auth):
        subject = "%s 故障报警" % (datetime.datetime.now().strftime("%Y-%m-%d"))
        message = MIMEText(mesg, "plain", "utf-8")
        message["To"] = Header(rec)
        message["Subject"] = Header(subject, "utf-8")
        try:
            smtpObj = smtplib.SMTP()
            smtpObj.connect(auth["mail_host"], 25)
            smtpObj.login(auth["mail_user"], auth["mail_pass"])
            smtpObj.sendmail(auth["mail_sender"], rec, message.as_string())
            return True
        except:
            logger.debug(traceback.format_exc())
            return False

    def dgsdk(self, mesg, rec, api):
        cmd = "curl -sd \"receive=" + rec + "&content=" + mesg + "\"" + " " + api
        try:
            res_str = os.popen(cmd).read()
            res_json = json.loads(res_str)
            if res_json["sendStatusCode"] == "1":
                return True
        except:
            logger.debug(traceback.format_exc())
            return False

if __name__ =='__main__':
    args = Head().getargs()
    if args.silence:
        logger = Head().getlog("/var/log/braum.log")
    logger = Head().getlog()
    if args.version:
        Head().version()
    if args.item:
        items = Head().getjson(Path(args.item))
        if not items:
            logger.info("Item配置文件: " + args.item + "导入失败，该文件不存在或该JSON文件语法有误")
            exit(0)
    else:
        items = Head().getjson(Path(os.path.join(os.path.dirname(__file__), "item.json")))
        if not items:
            logger.info("Item配置文件: " + os.path.join(os.path.dirname(__file__), "item.json") + "导入失败，该文件不存在或该JSON文件语法有误")
            exit(0)
    if args.config:
        config = Head().getjson(Path(args.config))
    else:
        config = Head().getjson(Path(os.path.join(os.path.dirname(__file__), "config.json")))
    if config["log_level"] == "DEBUG":
        logger.setLevel(logging.DEBUG)
    logger.info("xxxxxx[巡检开始]xxxxxx <-> 当前时间 {:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.today()))
    t0 = time.time()
    failed_count = 0
    success_count = 0
    logger.info(str(len(items["SERVICES"])) + " Items will be checked")
    if config:
        logger.info("Alert Method: " + config["alert_method"])
    else:
        logger.info("Alert Method: no")
    Items(items, config).check()
    t1 =time.time()
    delta_second = int(t1 - t0)
    total_count = success_count + failed_count
    healthy_rates = "%.2f%%" % (success_count / total_count * 100)
    logger.info("巡检总耗时：%s s" %(delta_second))
    logger.info("检查项目总数量： %s" %(total_count))
    logger.info("故障项目数量： %s" %(failed_count))
    logger.info("健康率： %s" %(healthy_rates))
    logger.info("xxxxxx[巡检结束]xxxxxx <-> 当前时间 {:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.today()))


















