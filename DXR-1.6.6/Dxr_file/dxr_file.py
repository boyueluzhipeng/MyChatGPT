#!usr/bin/python
# _*_ coding:utf-8 _*_
"""python
Created on 2020/08/14
@author: luzhipeng
"""
import os
import time
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure

class dxr_file:
    def __init__(self, ip='10.10.8.156', port=445, user_name='smbuser', passwd='123456', return_port=80):
        self.ip = ip
        self.port = port
        self.user_name = user_name
        self.passwd = passwd
        self.return_port = return_port
        self.samba, self.status = self.connect()
        if self.status:
            print('连接成功')
        else:
            print('连接失败')
        self.service_name = 'secret'
        
        
    def connect(self):
        '''
        建立smb服务连接
        :param user_name:
        :param passwd:
        :param ip:
        :param port: 445或者139
        :return:
        '''
        status = False
        try:
            print(f'开始连接smb服务器, ip:{self.ip}, port:{self.port}, user_name:{self.user_name}, passwd:{self.passwd}')
            samba = SMBConnection(self.user_name, self.passwd, '', '', use_ntlm_v2=True)
            samba.connect(self.ip, self.port)
            status = samba.auth_result
        except Exception as e:
            print(e)
            samba.close()
        return samba, status
        
    def all_shares_name(self):
        '''
        列出smb服务器下的所有共享目录
        :param samba:
        :return:
        '''
        share_names = list()
        sharelist = self.samba.listShares()
        for s in sharelist:
            share_names.append(s.name)
        return share_names
    
    def all_file_names_in_dir(self, dir_name):
        '''
        列出文件夹内所有文件名
        :param dir_name: 二级目录及以下的文件目录
        :return:
        '''
        f_names = list()
        for e in self.samba.listPath(self.service_name, dir_name):
            if e.filename[0] != '.':   # （会返回一些.的文件，需要过滤）
                f_names.append(e.filename)
        return f_names
    
    def get_last_updatetime(self, file_path):
        '''
        返回samba server上的文件更新时间（时间戳），如果出现OperationFailure说明无此文件，返回0
        :param samba:
        :param file_path:
        :return:
        '''
        try:
            sharedfile_obj = self.samba.getAttributes(self.service_name, file_path)
            return sharedfile_obj.last_write_time
        except OperationFailure:
            return 0
        
    def download(self, f_names, smb_dir, local_dir):
        '''
        下载文件
        :param samba:
        :param f_names:文件名
        :param smb_dir: smb文件夹
        :param local_dir: 本地文件夹
        :return:
        '''
        assert isinstance(f_names, list)
        # 如果local_dir不存在，则创建
        if not os.path.exists(local_dir):
            print('本地文件夹不存在，创建文件夹', local_dir)
            os.makedirs(local_dir)
        try:
            for f_name in f_names:
                f = open(os.path.join(local_dir, f_name), 'wb')
                self.samba.retrieveFile(self.service_name, os.path.join(smb_dir, f_name), f)
                f.close()
            return True
        except:
            return False
        
    def createDir(self, path):
        """
        创建文件夹
        :param samba:
        :param path:
        :return:
        """
        try:
            self.samba.createDirectory(self.service_name, path)
            return True
        except OperationFailure:
            # 判断连接
            return False
        
    def deleteDir(self, path):
        """
        删除文件夹
        :param samba:
        :param path:
        :return:
        """
        try:
            # path 是用多级目录的形式，如：/test/1/2/3
            print('删除文件夹', path)
            self.samba.deleteDirectory(self.service_name, path)
            return True
        except Exception as e:
            print(e)
            return False

    def upload(self, smb_dir, local_dir, f_name):
        '''
        上传文件
        :param samba:
        :param smb_dir: smb文件夹
        :param local_dir: 本地文件列表所在目录
        :param f_name: 本地文件名
        :return: 返回http://ip:port/服务名/文件夹名/文件名
        '''
        try:
            f = open(os.path.join(local_dir, f_name), 'rb')
            shares_list = self.samba.listShares()
            # 如果smb_dir不存在，则创建
            # 如果smb_dir中包含/，则需要创建多级目录
            if smb_dir.count('/') > 0:
                smb_dir_list = smb_dir.split('/')
                for i in range(len(smb_dir_list)):
                    if smb_dir_list[i] not in self.all_file_names_in_dir('/'.join(smb_dir_list[:i])):
                        self.createDir('/'.join(smb_dir_list[:i+1]))
                        print('创建目录：', '/'.join(smb_dir_list[:i+1]))
            self.samba.storeFile(self.service_name, os.path.join(smb_dir, f_name), f)
            f.close()
            # 如果self.return_port为80,则不拼接
            if int(self.return_port) == 80:
                return 'http://{}/{}/{}'.format(self.ip, smb_dir, f_name)
            else:
                return 'http://{}:{}/{}/{}'.format(self.ip, self.return_port, smb_dir, f_name)
        except Exception as e:
            print(e)
            return ''
        
if __name__ == '__main__':
    smb = dxr_file('10.10.10.53', 445, 'smbuser', '123456', return_port=880)
    # 上传本文件夹下的lu.wav文件
    # for i in range(10):
    #     print(smb.upload('dxr/test', 'test', 'requirements.txt'))
    #     # 下载test/test文件夹下的lu.wav文件
    #     current_dir = os.path.dirname(__file__)
    #     time.sleep(1)
    #     print(smb.download(['requirements.txt'], 'dxr/test', current_dir.join('t1')))
    print(smb.deleteDir('dxr'))