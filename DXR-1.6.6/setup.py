from setuptools import setup

setup(
    name='DXR',
    version='1.6.6',
    packages=['Dxr_mqtt', 'Dxr_log', 'Dxr_bytes', 'Dxr_utils', 'Dxr_video', 'Dxr_serial', 'Dxr_yaml', 'Dxr_file', 'Dxr_grpc', 'Dxr_isapi', 'Dxr_voice', 'Dxr_Chat'],
    install_requires=['paho-mqtt', 'pyyaml', 'pyserial', 'loguru','tabulate', 'pymysql', 'sqlalchemy', 'oss2', 'imagezmq', 'simplejpeg', 'pexpect', 'aiortsp'],
    author='luzhipeng',
    author_email='402087139@qq.com',
    license='MIT',
    url='http://pycn.me',
    description='DXR is a python library for DXR_mqtt',
)
