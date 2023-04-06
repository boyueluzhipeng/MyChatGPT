"""
hikvision.api
~~~~~~~~~~~~~~~~~~~~

Provides methods for interacting with hikvision

Copyright (c) 2015 Finbarr Brady <https://github.com/fbradyirl>
Licensed under the MIT license.
"""

import logging
from xml.etree import ElementTree
import re

import requests
from requests.exceptions import ConnectionError as ReConnError
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .error import HikvisionError, MissingParamError
from .constants import DEFAULT_PORT, DEFAULT_HEADERS, XML_ENCODING
from .constants import DEFAULT_SENS_LEVEL

_LOGGING = logging.getLogger(__name__)

# pylint: disable=too-many-arguments
# pylint: disable=too-many-instance-attributes


def build_url_base(host, port, is_https):
    """
    Make base of url based on config
    """
    base = "http"
    if is_https:
        base += 's'

    base += "://"
    base += host

    if port:
        base += ":"
        base += str(port)

    return base


def log_response_errors(response):
    """
    Logs problems in a response
    """

    _LOGGING.error("status_code %s", response.status_code)


def enable_logging():
    """ Setup the logging for home assistant. """
    logging.basicConfig(level=logging.INFO)


def remove_namespace(response):
    """ Removes namespace element from xml"""
    return re.sub(' xmlns="[^"]+"', '', response)


def tree_no_ns_from_string(response):
    """ Removes namespace element from response"""
    text = remove_namespace(response)
    return ElementTree.fromstring(text)


class CreateDevice:

    """
    Creates a new camera api device
    """

    def __init__(self, host=None, port=DEFAULT_PORT,
                 username=None, password=None, is_https=False,
                 sensitivity_level=DEFAULT_SENS_LEVEL,
                 digest_auth=True, strict_isapi=True):
        enable_logging()
        # _LOGGING.info("Initialising new hikvision camera client")

        if not host:
            # _LOGGING.error('Missing hikvision host!')
            raise MissingParamError('Connection to hikvision failed.', None)

        if not digest_auth and not is_https:
            # _LOGGING.warning("%s: HTTP Basic Auth without SSL is insecure",
            #                  host)
            pass

        self._username = username
        self._host = host
        self._password = password
        self._sensitivity_level = sensitivity_level
        self._digest_auth = digest_auth
        self._strict_isapi = strict_isapi
        self._auth_fn = HTTPDigestAuth if self._digest_auth else HTTPBasicAuth
        self.xml_motion_detection_off = None
        self.xml_motion_detection_on = None

        # Now build base url
        self._base = build_url_base(host, port, is_https)

        # need to support different channel
        if self._strict_isapi:
            self.motion_url = (
                '%s/ISAPI/System/Video/Inputs/channels/1/motionDetection' %
                self._base)
            self.deviceinfo_url = '%s/ISAPI/System/deviceInfo' % self._base
            self.ptzctrl_url = '%s/ISAPI/PTZCtrl/channels/1/continuous' % self._base
            self.ptzpreset_url = '%s/ISAPI/PTZCtrl/channels/1/presets' % self._base
            self.pic_url = '%s/ISAPI/Streaming/channels/1/picture' % self._base
            self.rtsp_url = '%s/ISAPI/Streaming/channels/101' % self._base
            self.ptz_senior_url = '%s/ISAPI/PTZCtrl/channels/1/absoluteExt' % self._base
            self.set_preset_url = '%s/ISAPI/PTZCtrl/channels/1/presets' % self._base
            self.ptzfocus_url = '%s/ISAPI/System/Video/inputs/channels/1/focus' % self._base
            # self.ir_url = '%s/ISAPI/Thermal/channels/2/thermometry/pixelToPixelParam/capabilities' % self._base
            self.ir_url = '%s/ISAPI/Thermal/channels/2/thermometry/jpegPicWithAppendData?format=json' % self._base
            self.capabilities_url = '%s/ISAPI/PTZCtrl/channels/1/absoluteEx/capabilities' % self._base
            self.ptz_absoluteEx_url = '%s/ISAPI/PTZCtrl/channels/1/absoluteEx' % self._base
            self.onepushfocus_url = '%s/ISAPI/PTZCtrl/channels/1/onepushfoucs/start' % self._base
            self.absoluteStatus_url = '%s/ISAPI/PTZCtrl/channels/1/status' % self._base
            self.imageFocus_url = '%s/ISAPI/Image/channels/1/focusConfiguration' % self._base
            self.ptz_capabilities_url = '%s/ISAPI/PTZCtrl/capabilities' % self._base
            self.ptz_autopan_url = '%s/ISAPI/PTZCtrl/channels/1/autopan' % self._base
            self.streamParam_url = '%s/ISAPI/Thermal/channels/2/streamParam' % self._base

        else:
            self.motion_url = '%s/MotionDetection/1' % self._base
            self.deviceinfo_url = '%s/System/deviceInfo' % self._base
            self.ptzctrl_url = '%s/PTZCtrl/capabilities' % self._base
            self.ptzpreset_url = '%s/PTZCtrl/channels/1/presets' % self._base
            self.pic_url = '%s/System/Video/channels/1/picture' % self._base
            self.rtsp_url = '%s/Streaming/channels/1' % self._base
            self.ptz_senior_url = '%s/PTZCtrl/channels/1/absoluteExt' % self._base
            self.ir_url = '%s/Thermal/channels/2/thermometry/pixelToPixelParam/capabilities?format=json' % self._base
#            self._xml_namespace = "{http://www.hikvision.com/ver10/XMLSchema}"
        self._xml_namespace = ""

    
    def get_ptz_capabilities(self, element_to_query=None):
        response = requests.get(
            self.ptz_capabilities_url,
            auth=self._auth_fn(self._username, self._password),
            headers={'Content-Type': 'application/json'}
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            # print(response.text)
            # 返回的是json格式的数据，返回的是一个字典
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                

                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None
    

    def get_absolutestatus(self, element_to_query=None):
        response = requests.get(
            self.ptz_absoluteEx_url,
            auth=self._auth_fn(self._username, self._password),
            headers={'Content-Type': 'application/json'}
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            # print(response.text)
            # 返回的是json格式的数据，返回的是一个字典
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                

                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None
    
    def set_ptzabsoluteEx(self,elevation,azimuth,absoluteZoom ,focus,focalLen,horizontalSpeed=10.00,verticalSpeed=10.00,zoomType='focalLen',element_to_query=None):
        data_xml = '<?xml version="1.0" encoding="UTF-8"?>' +\
                    '<PTZAbsoluteEx version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">' +\
                    '<elevation>'+ str(elevation) +'</elevation>'+\
                    '<azimuth>'+ str(azimuth) +'</azimuth>'+\
                    '<absoluteZoom>'+ str(absoluteZoom) +'</absoluteZoom>'+\
                    '<focus>'+ str(focus) +'</focus>'+\
                    '<focalLen>'+ str(focalLen) +'</focalLen>'+\
                    '<horizontalSpeed>'+ str(horizontalSpeed) +'</horizontalSpeed>'+\
                    '<verticalSpeed>'+ str(verticalSpeed) +'</verticalSpeed>'+\
                    '<zoomType>'+ str(zoomType) +'</zoomType>'+\
                    '</PTZAbsoluteEx>'
        # 转换为UTF-8编码
        data_xml = data_xml.encode('utf-8')
        # print(data_xml)
        response = requests.put(
            self.ptz_absoluteEx_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            print('http code:',response.status_code)
            print('response:',response.text)
            # log_response_errors(response)
            return None

        if element_to_query is None:
            # print(response.status_code)
            # print(response.text)
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
        except AttributeError as attib_err:
            return None
        return None
    
    def set_onepushfocus(self,element_to_query=None):
        response = requests.put(
            self.onepushfocus_url,
            auth=self._auth_fn(self._username, self._password),
            headers={'Content-Type': 'application/json'}
            )
        if response.status_code != 200:
            return response.text

        if element_to_query is None:
            # 返回的是json格式的数据，返回的是一个字典
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                

                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None
    
    def set_auopan(self,autoPan=0,element_to_query=None):
        autoPan = 60 * autoPan
        data_xml = '<?xml version="1.0" encoding="UTF-8"?><autoPanData><autoPan>' + str(autoPan) + '</autoPan></autoPanData> '
        # 转换为UTF-8编码
        data_xml = data_xml.encode('utf-8')
        # print(data_xml)
        response = requests.put(
            self.ptz_autopan_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            print('http code:',response.status_code)
            print('response:',response.text)
            # log_response_errors(response)
            return None

        if element_to_query is None:
            # print(response.text)
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
        except AttributeError as attib_err:
            return None
        return None
    
    def ir_test(self, element_to_query=None):
        response = requests.get(
            self.ir_url,
            auth=self._auth_fn(self._username, self._password),
            headers={'Content-Type': 'application/json'}
            )
        if response.status_code != 200:
            log_response_errors(response)
            return None

        if element_to_query is None:
            # 返回的是json格式的数据，返回的是一个字典
            return response.json()
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                

                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None
    
    def get_pic(self, element_to_query=None):
        response = requests.get(
            self.pic_url,
            auth=self._auth_fn(self._username, self._password),
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None
    
    def set_preset(self,  preset_number: int, element_to_query=None):
        set_p_url = self.set_preset_url + '/' + str(preset_number)
        data_xml = '<?xml version: "1.0" encoding="UTF-8"?>'+\
        '<PTZPreset xmlns="http://www.isapi.org/ver20/XMLSchema" version="2.0">'+\
            '<id>'+str(preset_number)+'</id>'+\
            '<presetName>预置点 '+str(preset_number)+'</presetName>'+\
        '</PTZPreset>'
        # 转换为UTF-8编码
        data_xml = data_xml.encode('utf-8')
        response = requests.put(
            set_p_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            print('something wrong',response)
            # log_response_errors(response)
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
        except AttributeError as attib_err:
            return None
        return None
    
    def goto_preset(self,  preset_number: int, element_to_query=None):
        ptz_preset_url = self.ptzpreset_url + '/' + str(preset_number) + '/goto'
        response = requests.put(
            ptz_preset_url,
            auth=self._auth_fn(self._username, self._password),
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()

        except AttributeError as attib_err:
            return None
        return None
    
    def delete_preset(self,preset_number: int, element_to_query=None):
        ptz_preset_url = self.ptzpreset_url + \
            '/' + str(preset_number)
        response = requests.delete(
            ptz_preset_url,
            auth=self._auth_fn(self._username, self._password),
        )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()

        except AttributeError as attib_err:

            return None
        return None
    
    # 聚焦控制 0-停止 1-聚焦+ -1-聚焦-
    def ptz_focus(self,add_sub = 0,element_to_query=None):
        focus = 60 * add_sub
        data_xml = '<?xml version: "1.0" encoding="UTF-8"?><FocusData><focus>'+ str(focus) +'</focus></FocusData>'
        response = requests.put(
            self.ptzfocus_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            print(response)
            return response.text

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()

        except AttributeError as attib_err:
            return None
        return None
    
    def ptz_senior(self, element_to_query=None):
        data_xml = '<?xml version="1.0" encoding="UTF-8"?>'+\
        '<PTZAbsoluteEx xmlns="http://www.isapi.org/ver20/XMLSchema" version="2.0">'+\
            '<elevation>0.000</elevation>'+\
            '<azimuth>0.000</azimuth>'+\
            '<absoluteZoom>0</absoluteZoom>'+\
            '<focus>1</focus>'+\
            '<focalLen>1</focalLen>'+\
            '<horizontalSpeed>0.00</horizontalSpeed>'+\
            '<verticalSpeed>0.00</verticalSpeed>'+\
            '<zoomType>%s</zoomType>'+\
        '</PTZAbsoluteEx>'
        response = requests.get(
            self.ptz_senior_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            log_response_errors(response)
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()

        except AttributeError as attib_err:
            return None
        return None
    
    # 设置图像参数,聚焦模式,聚焦限制 focusStyle: SEMIAUTOMATIC 半自动, MANUAL 手动, AUTO 自动，focusLimited: 聚焦限制 int, [10#10厘米,50#50厘米,100#1米,150#1.5米,300#3米,600#6米,1000#10米,2000#20米,5000#50米,20000#200米,50000#500米,65535#655.35米] 
    def set_image_capabilities(self,focusStyle='SEMIAUTOMATIC',focusLimited=10, element_to_query=None):
        data_xml = '<?xml version: "1.0" encoding="UTF-8"?>' +\
        '<FocusConfiguration>' +\
        '<focusStyle>'+ str(focusStyle) +'</focusStyle>' +\
        '<focusLimited>'+ str(focusLimited) +'</focusLimited>'+\
        '</FocusConfiguration>' 
        
        response = requests.put(
            self.imageFocus_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            print(response)
            return response.text

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()

        except AttributeError as attib_err:
            return None
        return None
    
    def set_ptz(self, element_to_query=None, up_down=0, left_right=0, zoom=0):
        pan =left_right * 15
        tilt = -up_down * 15
        zoom_ = zoom * 15
        data_xml = '<?xml version: "1.0" encoding="UTF-8"?><PTZData><pan>%s</pan><tilt>%s</tilt><zoom>%s</zoom></PTZData>' % (pan, tilt, zoom_)
        response = requests.put(
            self.ptzctrl_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
        except AttributeError as attib_err:
            return None
        return None
    
    def get_streamParam(self, element_to_query=None):
        response = requests.get(
            self.streamParam_url,
            auth=self._auth_fn(self._username, self._password),
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None
    
    # 配置指定通道热成像码流参数 videoCodingType:thermal_raw_data#热成像裸数据,pixel-to-pixel_thermometry_data#全屏测温数据,real-time_raw_data#实时裸数据,spectrogramData#科学仪器谱图数据（包括检测物质中的光谱波长与能量值） 
    def set_streamParam(self, element_to_query=None, videoCodingType='pixel-to-pixel_thermometry_data'):
        data_xml = '<?xml version: "1.0" encoding="UTF-8"?><ThermalStreamParam xmlns="http://www.isapi.org/ver20/XMLSchema" version="2.0">' +\
            '<videoCodingType>'+ str(videoCodingType) +'</videoCodingType>' +\
            '</ThermalStreamParam>'
            
        print(data_xml)
            
        response = requests.put(
            self.streamParam_url,
            auth=self._auth_fn(self._username, self._password),
            data=data_xml,
            )
        if response.status_code != 200:
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                return result[0].text.strip()
        except AttributeError as attib_err:
            return None
        return None
    
    def get_version(self):
        """
        Returns the firmware version running on the camera
        """
        return self.get_about(element_to_query='firmwareVersion')

    def get_about(self, element_to_query=None):
        """
        Returns ElementTree containing the result of
        <host>/System/deviceInfo
        or if element_to_query is not None, the value of that element
        """

        response = requests.get(
            self.deviceinfo_url,
            auth=self._auth_fn(self._username, self._password))

        if response.status_code != 200:
            log_response_errors(response)
            return None

        if element_to_query is None:
            return response.text
        try:
            tree = tree_no_ns_from_string(response.text)

            element_to_query = './/%s%s' % (
                self._xml_namespace, element_to_query)
            result = tree.findall(element_to_query)
            if len(result) > 0:
                

                return result[0].text.strip()
            

        except AttributeError as attib_err:
            
            return None
        return None

    def is_motion_detection_enabled(self):
        """Get current state of Motion Detection.

        Returns False on error or if motion detection is off."""

        response = requests.get(self.motion_url, auth=self._auth_fn(
            self._username, self._password))


        if response.status_code != 200:
            return False

        try:

            tree = tree_no_ns_from_string(response.text)
            enabled_element = tree.findall(
                './/%senabled' % self._xml_namespace)
            sensitivity_level_element = tree.findall(
                './/%ssensitivityLevel' % self._xml_namespace)
            if len(enabled_element) == 0:
                return False
            if len(sensitivity_level_element) == 0:
                return False

            result = enabled_element[0].text.strip()
            
            if int(sensitivity_level_element[0].text) == 0:
                sensitivity_level_element[0].text = str(
                    self._sensitivity_level)

            if result == 'true':
                # Save this for future switch off
                self.xml_motion_detection_on = ElementTree.tostring(
                    tree, encoding=XML_ENCODING)
                enabled_element[0].text = 'false'
                self.xml_motion_detection_off = ElementTree.tostring(
                    tree, encoding=XML_ENCODING)
                return True
            # Save this for future switch on
            self.xml_motion_detection_off = ElementTree.tostring(
                tree, encoding=XML_ENCODING)
            enabled_element[0].text = 'true'
            self.xml_motion_detection_on = ElementTree.tostring(
                tree, encoding=XML_ENCODING)
            return False

        except AttributeError as attib_err:
            return False

    def enable_motion_detection(self):
        """ Enable Motion Detection """

        self.put_motion_detection_xml(self.xml_motion_detection_on)

    def disable_motion_detection(self):
        """ Disable Motion Detection """

        self.put_motion_detection_xml(self.xml_motion_detection_off)

    def put_motion_detection_xml(self, xml):
        """ Put request with xml Motion Detection """



        headers = DEFAULT_HEADERS
        headers['Content-Length'] = str(len(xml))
        headers['Host'] = self._host
        response = requests.put(self.motion_url, auth=self._auth_fn(
            self._username, self._password), data=xml, headers=headers)


        if response.status_code != 200:

            return

        try:
            tree = tree_no_ns_from_string(response.text)
            enabled_element = tree.findall(
                './/%sstatusString' % self._xml_namespace)
            if len(enabled_element) == 0:
                
                return

            if enabled_element[0].text.strip() == 'OK':
                pass

        except AttributeError as attrib_err:
            return
