import asyncio
import os
import stat
import types
import re
from Dxr_mqtt.dxr_log import *


# 判断系统类型，如果是windows则引入wexpect，如果是linux则引入pexpect
if os.name == 'nt':
    import wexpect as pexpect
else:
    import pexpect
password_key = '.*assword.*'
is_input_yes = '.*yes/no.*'
import threading
import time

# 写一个线程，一直来对比文件大小，并且打印进度条，如果文件大小一样了，就结束线程
class MyThread(threading.Thread):
    def __init__(self, file_size, file_name):
        super(MyThread, self).__init__()
        # 进度条的长度
        self.bar_length = 50
        self.is_stop = False
        self.process_ = 0
        self.file_size = file_size
        if self.file_size.endswith('M'):
            self.file_size = int(float(self.file_size[:-1]) * 1024 * 1024)
        elif self.file_size.endswith('G'):
            self.file_size = int(float(self.file_size[:-1]) * 1024 * 1024 * 1024)
        self.file_name = file_name
        print('文件名：', self.file_name)
        self.daemon = True
        self.start()

    def get_process(self):
        yield self.process_

    def print_progress_bar(self, percent):
        # 进度条的长度
        bar_length = 50
        # 计算进度条的长度
        hashes = '#' * int(percent / 100 * bar_length)
        # 计算空格的长度
        spaces = ' ' * (bar_length - len(hashes))
        # 打印进度条
        print('\rPercent: [%s] %d%%' % (hashes + spaces, percent), end='')

    def run(self):
        print('开始下载文件：', self.file_name)
        while not self.is_stop:
            try:
                time.sleep(0.5)
                # 下载的文件为临时文件，会在原来的文件名后面加上.随机字符串，所以需要获取临时文件的大小
                # 获取文件名
                file_path = os.path.dirname(self.file_name)
                file_name = os.path.basename(self.file_name)
                # 获取临时文件名
                file_name_list = os.listdir(file_path)
                # print(file_name_list)
                file_name = [i for i in file_name_list if i.startswith(file_name)]
                file_name = file_name[0] if file_name else None
                # 如果为空，则continue
                if not file_name:
                    continue
                # 获取文件名
                # 获取文件大小
                file_size = os.path.getsize(file_name)
                # 计算百分比
                percent = file_size / self.file_size * 100
                # 四舍五入取整
                percent = 100 if int(round(percent)) > 97 else int(round(percent))
                self.process_ = percent
                # self.print_progress_bar(self.process_)
                # 如果文件大小一样了，就结束线程
                if file_size == self.file_size:
                    break
            except Exception as e:
                print(e)

    def stop(self):
        self.process_ = 100
        # self.print_progress_bar(self.process_)
        time.sleep(1)
        self.is_stop = True


def print_process(tmp_thread, callback=None):
    while not tmp_thread.is_stop:
        if callback:
            file_name = tmp_thread.file_name
            # file_name是一个绝对路径，需要截取出来，并且判断平台，如果是windows则需要把\替换成/
            if os.name == 'nt':
                file_name = file_name.split('\\')[-1]
            else:
                file_name = file_name.split('/')[-1]
            callback(tmp_thread.process_, file_name)
        time.sleep(1)


# 写一个装饰器，用来装饰下载文件的函数，并对函数的返回值进行迭代出来
def download_file(func):
    def wrapper(*args, **kwargs):
        # 获取传参中的callback
        callback = kwargs.get('callback')
        # 获取函数的返回值
        res = func(*args, **kwargs)
        # 迭代出来
        for thread_tmp in res:
            # 如果返回的是一个线程，则开辟一个线程打印日志
            if isinstance(thread_tmp, MyThread):
                threading.Thread(target=print_process, args=(thread_tmp, callback), daemon=True).start()
            else:
                return thread_tmp

    return wrapper


def ssh_is_file_exist(remote_path, ip, user_name, password, port=22):
    ssh = pexpect.spawn('ssh -p %s %s@%s ls %s' % (port, user_name, ip, remote_path))
    try:
        # i = ssh.expect([password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        # 添加yes/no的判断
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        file_list_str = ssh.before
        if isinstance(file_list_str, bytes):
            file_list_str = file_list_str.decode('utf-8')
        if 'No such file or directory' in file_list_str:
            return False
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False


# 获取列表下所有文件以及文件夹，并且获取这些文件的大小以及更新时间, 自动输入密码
def ssh_get_file_list(remote_path, ip, user_name, password, port=22):
    # ssh = pexpect.spawn('ssh %s@%s ls -l %s' % (user_name, ip, remote_path))
    ssh = pexpect.spawn('ssh -p %s %s@%s ls -l %s' % (port, user_name, ip, remote_path))
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        file_list_str = ssh.before
        # 如果file_list_str是bytes类型，则转换成str类型
        if isinstance(file_list_str, bytes):
            file_list_str = file_list_str.decode('utf-8')
        if 'No such file or directory' in file_list_str:
            return None
        file_list = file_list_str.split('\r\n')
        for i in file_list:
            if i.count('drwxr') > 1:
                new_i =[f'drwxr{o}' for o in i.split('drwxr')]
                file_list = new_i + file_list
        # print(f'file_list11: {file_list}')
        file_list = file_list[1:-1] if os.name != 'nt' else file_list[1:]
        # 对列表进行处理成一个字典的列表，键分别为权限，文件个数，所有者，所属组，大小，更新时间，文件名
        file_list_dict = []
        for f in file_list:
            file_dict = {}
            f = f.split()
            if len(f) != 9:
                continue
            file_dict['permissions'] = f[0]
            file_dict['number'] = f[1]
            file_dict['owner'] = f[2]
            file_dict['group'] = f[3]
            file_dict['size'] = f[4]
            file_dict['time'] = f[5] + ' ' + f[6] + ' ' + f[7]
            file_dict['name'] = f[8]
            file_list_dict.append(file_dict)
        return file_list_dict
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return None
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return None

@download_file
def ssh_download_file(remote_path, local_path, ip, user_name, password, port=22, callback=None):
    # 使用scp下载文件，同时使用-c参数，使用压缩传输，提高传输速度
    cmd = 'scp -P %s %s@%s:%s %s' % (port, user_name, ip, remote_path, local_path)
    # cmd = 'scp -c -P %s %s@%s:%s %s' % (port, user_name, ip, remote_path, local_path)
    print(cmd)
    ssh = pexpect.spawn(cmd)
    # 不设置超时时间，因为下载文件的时间不确定
    try:
        get_file_size_index = 0
        file_size = ssh_get_file_size(remote_path, ip, user_name, password, port)
        # 获取文件大小
        while True:
            if file_size:
                break
            get_file_size_index += 1
            if get_file_size_index > 3:
                print('获取文件大小失败')
                file_size = '0M'
        # 开启进度条打印线程
        file_name = remote_path.split('/')[-1]
        # 如果local_path没有以/结尾，则添加/
        if local_path[-1] != '/':
            local_path += '/'
        local_file_path = local_path + file_name
        # 如果本地文件已经存在，则删除
        if os.path.exists(local_file_path):
            # 删除localfile的只读属性
            # 如果是windows系统
            if os.name == 'nt':
                os.system(f"attrib -r {local_file_path}")
            else:
                # 给文件添加可写权限
                os.chmod(local_file_path, stat.S_IWRITE)
            os.remove(local_file_path)
            time.sleep(1)
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT])
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        process_thread = MyThread(file_size=file_size, file_name=local_file_path)
        yield process_thread
        ssh.expect(pexpect.EOF, timeout=6000)
        process_thread.stop()
        # 如果下载失败
        before_str = ssh.before
        if isinstance(before_str, bytes):
            before_str = before_str.decode('utf-8')
        if 'rsync error' in before_str:
            print('rsync error')
            ssh.close()
            yield False
        else:
            print('rsync success')
            ssh.close()
        yield True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        yield False

    
        

# @download_file
# def ssh_download_file(remote_path, local_path, ip, user_name, password, port=22, callback=None):
#     # cmd = 'scp %s@%s:%s %s' % (user_name, ip, remote_path, local_path)
#     cmd = 'scp -P %s %s@%s:%s %s' % (port, user_name, ip, remote_path, local_path)
#     print(cmd)
#     ssh = pexpect.spawn(cmd)
#     # 不设置超时时间，因为下载文件的时间不确定
#     try:
#         # 获取文件大小
#         file_size = ssh_get_file_size(remote_path, ip, user_name, password, port)
#         # 开启进度条打印线程
#         file_name = remote_path.split('/')[-1]
#         # 如果local_path没有以/结尾，则添加/
#         if local_path[-1] != '/':
#             local_path += '/'
#         local_file_path = local_path + file_name
#         # 如果本地文件已经存在，则删除
#         if os.path.exists(local_file_path):
#             os.remove(local_file_path)
#             time.sleep(1)
#         i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT])
#         if i == 0:
#             ssh.sendline('yes')
#             ssh.expect(password_key)
#             ssh.sendline(password)
#         elif i == 1:
#             ssh.sendline(password)
#         process_thread = MyThread(file_size=file_size, file_name=local_file_path)
#         yield process_thread
#         ssh.expect(pexpect.EOF, timeout=6000)
#         process_thread.stop()
#         # 如果下载失败
#         before_str = ssh.before
#         if isinstance(before_str, bytes):
#             before_str = before_str.decode('utf-8')
#         # print(f'ssh before: {before_str}')
#         if 'scp:' in before_str:
#             yield False
#         yield True
#     except pexpect.EOF:
#         print('EOF')
#         ssh.close()
#         yield False


def ssh_upload_file(local_path, remote_path, ip, user_name, password, port=22):
    # cmd = 'scp %s %s@%s:%s' % (local_path, user_name, ip, remote_path)
    # 先判断文件是否存在，如果存在，则把原来文件名重命名成_bak
    if ssh_is_file_exist(remote_path + '/' + local_path, ip, user_name, password, port):
        ssh_rename_file(remote_path + '/' + local_path, remote_path + '/' + local_path + '_bak', ip, user_name,
                        password, port)
    cmd = 'scp -P %s %s %s@%s:%s' % (port, local_path, user_name, ip, remote_path)
    ssh = pexpect.spawn(cmd)
    # 不设置超时时间，因为下载文件的时间不确定
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        before_str = ssh.before
        if isinstance(before_str, bytes):
            before_str = before_str.decode('utf-8')
        print(f'ssh before: {before_str}')
        # 如果100%都没有出现，则说明上传失败
        if '100%' not in before_str:
            ssh.close()
            return False
        ssh.close()
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False


def ssh_rename_file(old_path, new_path, ip, user_name, password, port=22):
    # 先判断文件是否存在
    if not ssh_get_file_list(old_path, ip, user_name, password, port):
        return False
    # cmd = 'ssh %s@%s mv %s %s' % (user_name, ip, old_path, new_path)
    cmd = 'ssh -p %s %s@%s mv %s %s' % (port, user_name, ip, old_path, new_path)
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh_before = ssh.expect(pexpect.EOF)
        print(f'ssh before: {ssh_before}')
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return False


def ssh_delete_file(path, ip, user_name, password, port=22):
    # 先判断文件是否存在
    if not ssh_get_file_list(path, ip, user_name, password, port):
        return False
    # cmd = 'ssh %s@%s rm -rf %s' % (user_name, ip, path)
    cmd = 'ssh -p %s %s@%s rm -rf %s' % (port, user_name, ip, path)
    # print(f'delete file cmd: {cmd}')
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh_before = ssh.expect(pexpect.EOF)
        print(f'ssh before: {ssh_before}')
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return False

def ssh_delete_dir(path, ip, user_name, password, port=22):
    # cmd = 'ssh %s@%s rm -rf %s' % (user_name, ip, path)
    cmd = 'ssh -p %s %s@%s rm -rf %s' % (port, user_name, ip, path)
    # print(f'delete dir cmd: {cmd}')
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return False


def ssh_create_file(path, ip, user_name, password, port=22):
    # 先判断path是否存在
    if ssh_get_file_list(path, ip, user_name, password, port):
        return False
    # cmd = 'ssh %s@%s touch %s' % (user_name, ip, path)
    cmd = 'ssh -p %s %s@%s touch %s' % (port, user_name, ip, path)
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return False


def ssh_create_dir(path, ip, user_name, password, port=22):
    # 先判断path是否存在
    if ssh_get_file_list(path, ip, user_name, password, port):
        return False
    # cmd = 'ssh %s@%s mkdir %s' % (user_name, ip, path)
    cmd = 'ssh -p %s %s@%s mkdir %s' % (port, user_name, ip, path)
    print(f'create dir cmd: {cmd}')
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        # 执行完命令后，会有一个EOF，需要expect一下，并打印出来
        ssh_before = ssh.expect(pexpect.EOF)
        print(f'ssh before: {ssh_before}')
        ssh.close()
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return False


def ssh_get_file_size(path, ip, user_name, password, port=22):
    # cmd = 'ssh %s@%s du -sh %s' % (user_name, ip, path)
    cmd = 'ssh -p %s %s@%s du -sh %s' % (port, user_name, ip, path)
    print(f'get file size cmd: {cmd}')
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        print(f'get file size i: {i}')
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        before_str = ssh.before
        # 判断before_str是为bytes类型还是str类型
        if isinstance(before_str, bytes):
            before_str = before_str.decode('utf-8')
        file_size = before_str.split('\r\n')[1].split()[0]
        return file_size
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return None
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return None
    
# 写一个异步下载文件的方法，使用回调函数能够实时获取下载进度以及下载速度
async def ssh_download_file_async(path, local_path, ip, user_name, password, port=22, callback=None):
    # 先判断path是否存在
    if not ssh_get_file_list(path, ip, user_name, password, port):
        return False
    # cmd = 'scp %s@%s:%s %s' % (user_name, ip, path, local_path)
    cmd = 'scp -P %s %s@%s:%s %s' % (port, user_name, ip, path, local_path)
    print(f'download file cmd: {cmd}')
    ssh = pexpect.spawn(cmd)
    try:
        i = ssh.expect([is_input_yes, password_key, pexpect.EOF, pexpect.TIMEOUT], timeout=60)
        print(f'download file i: {i}')
        if i == 0:
            ssh.sendline('yes')
            ssh.expect(password_key)
            ssh.sendline(password)
        elif i == 1:
            ssh.sendline(password)
        ssh.expect(pexpect.EOF)
        return True
    except pexpect.EOF:
        print('EOF')
        ssh.close()
        return False
    except pexpect.TIMEOUT:
        print('TIMEOUT')
        ssh.close()
        return False
        


def process_callback(p, f):
    print(p, f)


if __name__ == '__main__':
    ip = '39.101.69.111'
    user_name = 'root'
    password = 'Dxr85578595'
    # res = ssh_download_file('/root/test.zip', './', ip, user_name, password, callback=process_callback)
    # print(ssh_is_file_exist('/root/test1.zip', ip, user_name, password))
    # print(ssh_get_file_list('/root1', ip, user_name, password))
    # print(ssh_upload_file('./error.log', '/root', ip, user_name, password))
    # print(ssh_rename_file('/root/error1.log', '/root/error.log', ip, user_name, password))
    # print(ssh_delete_file('/root/error.log', ip, user_name, password))
    # print(ssh_create_dir('/root/test', ip, user_name, password))
    print(ssh_delete_dir('/root/test', ip, user_name, password))