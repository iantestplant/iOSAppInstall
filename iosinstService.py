#!venv/bin/python

# -*- coding: utf-8 -*-
#
# Copyright (C) 2014    TestPlant UK Ltd
# Version 1.0
#

from flask import Flask, jsonify, abort, request, make_response, url_for
from flask.views import MethodView
from flask.ext.restful import Api, Resource, reqparse, fields, marshal
from flask.ext.httpauth import HTTPBasicAuth

from iosinst_utils import *

app = Flask(__name__, static_url_path = "")
api = Api(app)
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == 'eggbox':
        return 'testplant'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify( { 'message': 'Unauthorized access' } ), 403)
    # return 403 instead of 401 to prevent browsers from displaying the default auth dialog

devices = []

device_fields = {
    'product': fields.String,
    'name': fields.String,
    'udid': fields.String,
    'uri': fields.Url('device')
}

def findDevices():
    global devices
    devices = []
    iosDevicesByUdid = getAttachedDevices()

    for dev in iosDevicesByUdid.values():
        devices.append( {
           'id': (devices[-1]['id'] + 1 if devices else 1),
           'name': dev.name,
           'product': dev.product,
           'udid': dev.udid
        })


class DeviceListAPI(Resource):
    #~ decorators = [auth.login_required]

    def __init__(self):
        super(DeviceListAPI, self).__init__()

    def get(self):
        # get the list of attached devices
        findDevices()
        return { 'devices': map(lambda t: marshal(t, device_fields), devices) }

    def put(self):
        # Install an app
        req = reqparse.RequestParser()
        req.add_argument('udid', type = str, required = True, help = 'No udid provided', location = 'json')
        req.add_argument('appPath', type = str, required = True, help = 'No app path provided', location = 'json')
        #req.add_argument('deleteApp', type = bool, required = True, help = 'No delete flag included', location = 'json')
        args = req.parse_args()
        s = installApp(args['udid'], appPath=args['appPath'])#, deleteApp=args['deleteApp'])
        return {'status': s[0], 'message':s[1]}

    def delete(self):
        # Uninstall an app
        req = reqparse.RequestParser()
        req.add_argument('udid', type = str, required = True, help = 'No udid provided', location = 'json')
        req.add_argument('bundleID', type = str, required = True, help = 'No bundleID provided', location = 'json')
        args = req.parse_args()
        s = uninstallApp(args['udid'], args['bundleID'])
        return {'status': s[0], 'message':s[1]}

class HostNameAPI(Resource):
    def __init__(self):
        super(HostNameAPI, self).__init__()
    def get(self):
        return { 'hostname': socket.gethostname() }

class DeviceAPI(Resource):
    #decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('name', type = str, location = 'json')
        self.reqparse.add_argument('product', type = str, location = 'json')
        self.reqparse.add_argument('udid', type = str, location = 'json')
        super(DeviceAPI, self).__init__()
#
#     def get(self, id):
#         print devices
#         device = filter(lambda t: t['id'] == id, devices)
#         if len(device) == 0:
#             abort(404)
#         return { 'device': marshal(device[0], device_fields) }

#     def put(self, id):
#         device = filter(lambda t: t['id'] == id, devices)
#         if len(device) == 0:
#             abort(404)
#         device = device[0]
#         args = self.reqparse.parse_args()
#         for k, v in args.iteritems():
#             if v != None:
#                 device[k] = v
#         return { 'device': marshal(device, device_fields) }
#
#     def delete(self, id):
#         device = filter(lambda t: t['id'] == id, devices)
#         if len(device) == 0:
#             abort(404)
#         device.remove(device[0])
#         return { 'result': True }

api.add_resource(DeviceListAPI, '/iosinst/api/v1.0/devices', endpoint = 'devices')
api.add_resource(HostNameAPI, '/iosinst/api/v1.0/hostname', endpoint = 'hostname')
api.add_resource(DeviceAPI, '/iosinst/api/v1.0/devices/<int:id>', endpoint = 'device')

from argparse import ArgumentParser
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', dest='port', default=5000, type=int, help='listening port')
    parser.add_argument('-d', '--logging_level', dest = 'level', default='DEBUG')
    args = parser.parse_args()
    setLogLevel(args.level)

    app.run(debug = False, host='0.0.0.0', port=args.port)
