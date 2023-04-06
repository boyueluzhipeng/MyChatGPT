import os
import stat
import threading
import time
import requests


def ssh_download_file(remote_path, local_path, ip, user_name, password, port=22, callback=None):
    # 使用requests下载文件,并调用callback函数,持续返回进度
    url = 'http://' + ip + ':' + str(port) + '/download_file?remote_path=' + remote_path
    print(url)
    # 获取文件的大小
    file_size = requests.get(url=url, auth=(user_name, password), stream=True).headers['Content-Length']
    # 获取文件的名字
    file_name = remote_path.split('/')[-1]
    local_file_path = local_path + file_name
    # 判断文件是否存在
    if os.path.exists(local_file_path):
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
    # 下载文件
    response = requests.get(url=url, auth=(user_name, password), stream=True)
    # 如果response的状态码不是200,则抛出异常
    if response.status_code != 200:
        return False
    # 保存文件
    with open(local_file_path, 'wb') as f:
        # 记录下载的大小
        count = 0
        # 记录下载的时间
        start_time = time.time()
        # 以流的形式下载文件
        process = 0
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                count += len(chunk)
                # print(count, file_size)s
                # 每下载1M,调用一次callback函数
                if count / int(file_size) > 0.01:
                    # 调用callback函数
                    if callback:
                        process += count / int(file_size)
                        threading.Thread(target=callback, args=(process * 100, file_name)).start()
                    count = 0
        threading.Thread(target=callback, args=(100, file_name)).start()
                    
    print('下载完成')
    return True
    
def callback(process, filename):
    print(process, filename)
    
    
if __name__ == '__main__':
    res = ssh_download_file('/root/nav_ws/src/lidar_localization/Localization/data/latest/finalCloud.pcd', './', '10.10.11.10', 'root', '123456', 5000, callback)
    threading.Thread(target=ssh_download_file, args=('/root/nav_ws/src/lidar_localization/Localization/data/latest/', './', '10.10.11.10', 'root', '123456', 5000, callback,)).start()