import requests

# 使用requests库，发送get请求
def ssh_create_dir(path, ip, *args, **kwargs):
    # 通过requests库，发送POST请求, path是文件的绝对路径
    url = 'http://%s:5000/add_user' % ip
    data = {'user_name': path}
    try:
        r = requests.post(url, data=data, timeout=1)
        print(r.json())
        if r.json()['code'] == 200:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False
    
# 使用requests库，发送post请求
def ssh_delete_dir(path, ip, *args, **kwargs):
    # 通过requests库，发送POST请求, path是文件的绝对路径
    url = 'http://%s:5000/delete_user' % ip
    data = {'user_name': path}
    try:
        r = requests.post(url, data=data, timeout=1)
        print(r.json())
        if r.json()['code'] == 200:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False
    
def ssh_delete_file(path, ip, *args, **kwargs):
    # 通过requests库，发送POST请求, path是文件的绝对路径
    url = 'http://%s:5000/delete_image' % ip
    data = {'user_name': path}
    try:
        r = requests.post(url, data=data, timeout=1)
        print(r.json())
        if r.json()['code'] == 200:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False
    
def ssh_upload_file(local_path, remote_path, ip, *args, **kwargs):
    # 通过requests库，发送POST请求, local_path是本地文件的绝对路径，remote_path是远程文件的绝对路径
    url = 'http://%s:5000/upload_image' % ip
    data = {'user_name': remote_path}
    files = {'file': open(local_path, 'rb')}
    try:
        r = requests.post(url, data=data, files=files, timeout=1)
        print(r.json())
        if r.json()['code'] == 200:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False
    
if __name__ == '__main__':
    print('删除文件夹')
    res = ssh_delete_dir('/root/DXR_Project/DXR_FaceRec/face/database/test', '10.10.11.93','root', '123456', port=22)
    print(res)
    # print('创建文件夹')
    # res = ssh_create_dir('/root/DXR_Project/DXR_FaceRec/face/database/test', '10.10.11.93','root', '123456', port=22)
    # print(res)
    # print('上传文件')
    # res = ssh_upload_file('dxr_ssh.py', '/root/DXR_Project/DXR_FaceRec/face/database/test', '10.10.11.93','root', '123456', port=22)
    # print(res)
    # print('删除文件')
    # res = ssh_delete_file('/root/face_tmp/dxr_ssh.py', '10.10.11.93','root', '123456', port=22)
    # print(res)
    
    