#!venv/bin/python

# -*- coding: utf-8 -*-
#
# Copyright (C) 2014    TestPlant UK Ltd
# Version 1.0
#

import os, sys, socket
import subprocess
import logging
import shlex
import urllib2, plistlib, tempfile, shutil, traceback

logger = logging.getLogger('iosinst')
logger.setLevel(logging.INFO)
# create file handler which logs even debug messages
# fh = logging.FileHandler('iosinst.log')
# fh.setLevel(logging.CRITICAL)
# create console handler with a higher log level
ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
# logger.addHandler(fh)
logger.addHandler(ch)

g_devicescvs = "devices.csv"

device_col=0
name_col=1
udid_col=2
fieldnames = ['Device', 'Name', 'UDID']

def setLogLevel(level):
    level = level.upper()
    if level == 'DEBUG' : ch.setLevel(logging.DEBUG)
    elif level == 'INFO' : ch.setLevel(logging.INFO)
    elif level == 'CRITICAL' : ch.setLevel(logging.CRITICAL)

iosDevicesByUdid = {}
class iosDevice:
    def __init__(self, UDID, product, name):
        self.udid = UDID
        self.product = product
        self.name = name

    def __str__(self):
        return 'name=%s prod=%s udid=%s'%(self.name, self.product, self.udid)

def runCmd(cmd, silent=False):
    if not silent:
        logger.info("cmd:" + cmd)
    s = ""
    try:
        s = unicode(subprocess.check_output(shlex.split(cmd)),'utf-8')
        if not silent:
            logger.debug(s)
    except subprocess.CalledProcessError, procError:
        s = procError.output
        logger.critical(str(procError))
    except Exception, e:
        logger.critical('Exception: ' + str(e))
    return s

def getAttachedDevices():
    iosDevicesByUdid = {}
    cmd = "./ios-deploy -c -t1"
    lines = runCmd(cmd).splitlines()
    logger.info(lines)
    for line in lines:
        pos = line.find(" Found ")
        if pos > 0:
            pos1 = line.find("'") # find start of device name
            name = line[pos1+1 : line.rfind("'")]
            product = line[pos+7 : pos1-1]
            udid = line[line.find("' (")+3 : line.rfind(")")]
            if product and udid and name.find('(null)') == -1:
                iosDevicesByUdid[udid] = iosDevice(udid, product, name)

    return iosDevicesByUdid


def getDevNameFromCsv(udid):
    with open(g_devicescvs, 'rb') as csvfile:
        for row in csv.DictReader(csvfile):
            if row[fieldnames[udid_col]] == udid.strip():
                return row[fieldnames[name_col]]
    return None

def getUdid(devName):
    for dev in iosDevicesByUdid.values():
        if (dev.name == devName):
            return dev.udid
    getUdidFromCsv(devName)

def getDevName(udid):
    if iosDevicesByUdid.has_key(udid):
        return iosDevicesByUdid[udid].name
    return getUdidFromCsv(udid)

def getassetDir():
    dir = "assets"
    if not os.path.exists(dir):
        os.mkdir(dir)
    return os.path.abspath(dir)

def readInChunks(url, file):
    req = urllib2.urlopen(url)
    CHUNK = 16*1024
    i = 0
    with open(file, 'wb') as fp:
        while True:
            chunk = req.read(CHUNK)
            if not chunk: break
            fp.write(chunk)
#             i += len(chunk)
#             print '\r%s'%(i),
#             sys.stdout.flush()

def getAppFromPlist(path):
    pos = path.lower().find("http")
    if pos == -1:
        logger.critical("Path does not contain http")
        return ""

    if (pos > 0):
        path = path[pos:] # strip before http

    dir = getassetDir()

    assetUrls = []
    bundle_identifier = ''
    tmpdir = tempfile.mkdtemp()

    try:
        if path.lower().startswith("http"):
            if path.lower().endswith(".plist"):
                data = urllib2.urlopen(path).read()
                plist = plistlib.readPlistFromString(data)
                items = plist['items']
                #for item in items:
                item = items[0]
                assets = item['assets']
                for asset in assets:
                    assetUrls.append(asset['url'])

                metadata = item['metadata']
                #print 'metadata', metadata
                bundle_identifier = metadata['bundle-identifier']
            else:
                assetUrls.append(path) # path to ipa file?

        logger.info('assetUrls=%s bundle_identifier=%s'%(assetUrls, bundle_identifier))
        assetFiles = []
        for url in assetUrls:
            fname = os.path.basename(url)
            assetFiles.append(fname)
            target = os.path.join(dir, fname)
            if os.path.exists(target):
                logger.info("asset %s already exists, not downloading"%(fname))
                continue

            fpath = os.path.join(tmpdir, fname)
            logger.info("downloading asset %s to fname %s"%(url, fpath))
            readInChunks(url, fpath)

            if os.path.exists(target):
                os.remove(target)
            shutil.move(fpath, dir)

        logger.info('assetFiles %s'%(assetFiles))
        for fname in assetFiles:
            if os.path.splitext(fname)[1].lower() in ['.ipa', '.app']:
                return os.path.join(dir, fname), bundle_identifier
            else:
                logger.critical("failed to find ipa or app file in assets " + assetFiles)

    except Exception, e:
        logger.critical("getAppFromPlist: " + str(e))
        logger.critical(traceback.print_exc())
    finally:
        shutil.rmtree(tmpdir)


def installApp(udid=None, devName=None, appPath=None, deleteApp=False):

    bundle_identifier = ''
    appPath = appPath.strip(' ;"\'')
    if os.path.splitext(appPath)[1].lower() in [".plist", ".ipa"] and appPath.lower().find("http") != -1:
        appPath, bundle_identifier = getAppFromPlist(appPath)
        msg = "file: %s not found"%(appPath)

    elif os.path.basename(appPath) == appPath:
        # this is just a filename - look for it in the assets folder
        msg = "file: %s not found in cache"%(appPath)
        appPath = os.path.join(getassetDir(), appPath)

    if not os.path.exists(appPath):

        logger.critical(msg)
        return 'error', msg
    if devName:
        udid = getUdid(devName)

    # uninstall if bundle ID found
    bundleOpts = '-r -1 ' + bundle_identifier if (deleteApp and bundle_identifier) else ""
    cmd = './ios-deploy -i %s -t1 %s -b "%s"'%(udid, bundleOpts, appPath)
    s = runCmd(cmd)
    if (s):
        msg = s
        if s.find('[100%] Installed package') > 0:
            msg = 'Successfully installed: "%s"'%(os.path.basename(appPath))
            if bundle_identifier:
                msg = msg + '\nBundle ID: "%s"'%(bundle_identifier)
            logger.debug(msg)
            return 'success', msg
        elif s.rfind('Timed out waiting for device') > 0:
            msg = 'error', 'Timed out waiting for device. Device may be disconected'
            logger.critical(msg)
        else:
            try:
                msg = 'error', s.splitlines()[-1:][0]
                logger.critical(msg)
            except:
                msg = 'error', s
                logger.critical(msg)
        return msg
        logger.critical(s)

    return 'error', s

def uninstallApp(udid, bundle_identifier):
    bundle_identifier = bundle_identifier.strip(' ;"\'')
    if not bundle_identifier:
        return 'error', 'You must enter a bundle ID'
    cmd = './ios-deploy -i %s -t1 -1 %s -r -m'%(udid, bundle_identifier)
    s = runCmd(cmd)
    if (s):
        msg = 'error', s
        if s.find('[ OK ] Uninstalled package') > 0:
            msg = 'success', "Successfully requested uninstall of bundle ID %s"%(bundle_identifier)
            logger.critical(msg)
        elif s.rfind('Timed out waiting for device') > 0:
            msg = 'error', "Timed out waiting for device. Device may be disconected"
            logger.critical(msg)
        else:
            s = s.replace('[ ERROR ] ', '')
            try:
                msg = 'error', s.splitlines()[-1:][0]
                logger.critical(msg)
            except:
                msg = 'error', s
                logger.critical(msg)

        return msg

    return 'error', "No data from uninstallApp()"

if __name__ == "__main__":
    #getAppFromPlist("https://41a602a99c96a99c4944-028454c70616f158a194ead314c2e535.ssl.cf1.rackcdn.com/manifest.plist")
    #sys.exit()
    getAttachedDevices()

    udid = "ea48696f1d31b9ca0d9e7b0483c5f1695de6e3a3" # 4s
    #udid = "8df684ed92a5e40c7a5a2d8a1cd7f040de035e7a" # 5c
    #installApp(udid, appPath = '/Users/ian/Music/iTunes/iTunes Media/Mobile Applications/Nationwide 2.2.0.app')
    #print installApp(udid, appPath = '/Users/ian/Downloads/ios-deploy-master/demo.app')
    print installApp(udid, appPath = "https://41a602a99c96a99c4944-028454c70616f158a194ead314c2e535.ssl.cf1.rackcdn.com/manifest.plist")

