#!/usr/bin/env python3

from importlib.metadata import version
from typing import Dict

from flask import Flask, request
from flask_restx import Api, Resource, fields  # type: ignore

from lacus.lacus import Lacus

from .helpers import get_secret_key
from .proxied import ReverseProxied

app: Flask = Flask(__name__)

app.wsgi_app = ReverseProxied(app.wsgi_app)  # type: ignore

app.config['SECRET_KEY'] = get_secret_key()

api = Api(app, title='Lacus API',
          description='API to query lacus.',
          version=version('lacus'))

lacus: Lacus = Lacus()


@api.route('/redis_up')
@api.doc(description='Check if redis is up and running')
class RedisUp(Resource):

    def get(self):
        return lacus.check_redis_up()


http_creds_model = api.model('HttpCredentialtModel', {
    'username': fields.String(),
    'password': fields.String()
})

viewport_model = api.model('ViewportModel', {
    'width': fields.Integer(),
    'height': fields.Integer()
})

geolocation_model = api.model('GeolocalisationModel', {
    'longitude': fields.Float(),
    'latitude': fields.Float()
})


submit_fields_post = api.model('SubmitFieldsPost', {
    'url': fields.Url(description="The URL to capture"),
    'document': fields.String(description="A base64 encoded document, it can be anything a browser can display."),
    'document_name': fields.String(description="The name of the document."),
    'depth': fields.Integer(description="Depth of the capture, based on te URLs that can be found in the rendered page."),
    'rendered_hostname_only': fields.Boolean(description="If depth is >0, which URLs are we capturing (only the ones with the same hostname as the rendered page, or all of them.)"),
    'browser': fields.String(description="Use this browser. Must be chromium, firefox or webkit.", example=''),
    'device_name': fields.String(description="Use the pre-configured settings for this device. Get a list from /json/devices.", example=''),
    'user_agent': fields.String(description="User agent to use for the capture", example=''),
    'proxy': fields.Url(description="Proxy to use for the capture. Format: [scheme]://[username]:[password]@[hostname]:[port]", example=''),
    'general_timeout_in_sec': fields.Integer(description="General timeout for the capture. It will be killed regardless the status after that time."),
    'cookies': fields.String(description="JSON export of a list of cookies as exported from an other capture", example=''),
    'headers': fields.String(description="Headers to pass to the capture", example='Accept-Language: en-US;q=0.5, fr-FR;q=0.4'),
    'http_credentials': fields.Nested(http_creds_model, description="HTTP Authentication settings"),
    'geolocation': fields.Nested(geolocation_model, description="The geolocalisation of the browser"),
    'viewport': fields.Nested(viewport_model, description="The viewport of the capture"),
    'timezone_id': fields.String(description="The timesone ID of the browser"),
    'locale': fields.String(description="The locale of the browser"),
    'color_scheme': fields.String(description="The color scheme of the browser"),
    'referer': fields.String(description="Referer to pass to the capture", example=''),
    'force': fields.Boolean(description="Force a capture, even if the same one was already done recently"),
    'recapture_interval': fields.Integer(description="The nimomal interval to re-trigger a capture, unless force is True"),
    'priority': fields.Integer(description="Priority of the capture, the highest, the better"),
})


@api.route('/enqueue')
class Enqueue(Resource):

    @api.doc(body=submit_fields_post)
    @api.produces(['text/text'])
    def post(self):
        to_query: Dict = request.get_json(force=True)
        perma_uuid = lacus.core.enqueue(
            url=to_query.get('url'),
            document_name=to_query.get('document_name'),
            document=to_query.get('document'),
            depth=to_query.get('depth', 0),
            browser=to_query.get('browser'),
            device_name=to_query.get('device_name'),
            user_agent=to_query.get('user_agent'),
            proxy=lacus.global_proxy if lacus.global_proxy else to_query.get('proxy'),
            general_timeout_in_sec=to_query.get('general_timeout_in_sec'),
            cookies=to_query.get('cookies'),
            headers=to_query.get('headers'),
            http_credentials=to_query.get('http_credentials'),
            viewport=to_query.get('viewport'),
            geolocation=to_query.get('geolocation'),
            timezone_id=to_query.get('timezone_id'),
            locale=to_query.get('locale'),
            color_scheme=to_query.get('color_scheme'),
            referer=to_query.get('referer'),
            rendered_hostname_only=to_query.get('rendered_hostname_only', True),
            force=to_query.get('force', False),
            recapture_interval=to_query.get('recapture_interval', 300),
            priority=to_query.get('priority', 0),
            uuid=to_query.get('uuid', None)
        )
        return perma_uuid


@api.route('/capture_status/<string:capture_uuid>')
@api.doc(description='Get the status of a capture.',
         params={'capture_uuid': 'The UUID of the capture'})
class CaptureStatusQuery(Resource):

    def get(self, capture_uuid: str):
        return lacus.core.get_capture_status(capture_uuid)


@api.route('/capture_result/<string:capture_uuid>')
@api.doc(description='Get the result of a capture.',
         params={'capture_uuid': 'The UUID of the capture'})
class CaptureResult(Resource):

    def get(self, capture_uuid: str):
        return lacus.core.get_capture(capture_uuid)
