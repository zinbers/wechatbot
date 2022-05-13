#!/usr/bin/env python
# coding:utf8
import sys
# reload(sys)
# sys.setdefaultencoding( "utf8" )

import itchat
from itchat.content import *
import time
import random
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import copy
import logging
import hashlib
import datetime

#@itchat.msg_register(itchat.content.TEXT)
#def text_reply(msg):
#    return msg['Text']
chatroom_info = {}
msg_hash_cache_dict={}
my_lock = threading.Lock()
def getNotifyQunMap(rooms,src_key,dst_key):
	src_id=None
	dst_list=[]
	dst_name_list=[]
	src_name=""
	for item in rooms:
		#print(item['NickName'],item['UserName'])
		if src_key in item['NickName']:
			src_id = item['UserName']
			src_name = item['NickName']
			#print("#####src_id:",src_id)
			continue
		if dst_key in item['NickName'] and (item['UserName'] not in dst_list):
			dst_list.append(item['UserName']) 
			dst_name_list.append(item['NickName'])
			#print("####dst_id:",item['UserName'])
	return src_id,dst_list,src_name,dst_name_list

def updateRoomID():
	global chatroom_info
	logging.info("刷新群列表！！")
	# 获取所有通讯录中的群聊
	# 需要在微信中将需要同步的群聊都保存至通讯录
	chatrooms = itchat.get_chatrooms(update=True, contactOnly=True)
	# chatroom_info ={
	# 	'@@79ab4f63df6233aa8f9596f50133a222de8108a8e3564e81719c8195e5a3b4f1':{
	# 		'name':"我是机器人",
	# 		 'dst':['@@d093472a1b0934e2b1adbcc11ce99ecc16934f842c5d83d0ce07cf668c4dc134']
	# 	},
	# 	# '@@d8852dc48e92c9c92c7d0e3eaa6c023bfd1a2626eda3d9131a78d1b0aa7e6572':{
	# 	# 	'name':"g2",
	# 	# 	 'dst':['@@4812a8c55aa6812bb06b6eca12fc631499e4721d14107dd7480388ae459ed770']
	# 	# }
	# }
	src_qun_key=[]
	dst_qun_key=[]
	robot_name_list=[]
	limit_dispatch_list=[]
	def addMonitorQunInfo(src_key,dst_key,name, limit_list=[]):
		if src_key and dst_key and name:
			src_qun_key.append(src_key)
			dst_qun_key.append(dst_key)
			robot_name_list.append(name)
			limit_dispatch_list.append(limit_list)
	#chatroom_rename={}
	logging.info ('正在监测的群聊：{} 个'.format(len(chatrooms)))
	addMonitorQunInfo('联络员', '799', '联络员机器人转述',['25-杨','Bosco Zhu']) #25-yang,zhou
	addMonitorQunInfo('团购', '799', '团购机器人转述')
	addMonitorQunInfo('test_dst', 'test_src', '我是测试机器人',['媳妇']) #hello
	# src_qun_key=['联络员','团购','test_dst']
	# dst_qun_key=['799','799','test_src']
	# robot_name_list=['我是联络员机器人','我是团购机器人',"我是测试机器人"]
	my_lock.acquire()
	for i in range(len(src_qun_key)):
		s,l, s_name,l_name = getNotifyQunMap(chatrooms,src_qun_key[i],dst_qun_key[i])
		if s:
			chatroom_info[s]={
				'name': robot_name_list[i],
				'dst':l,
				'src_name':s_name,
				'dst_name_list':l_name,
				'primary_key':src_qun_key[i],
				'relate_key':dst_qun_key[i],
				'limit_user':limit_dispatch_list[i]
			}

	logging.info(chatroom_info)
	my_lock.release()

# 自动回复文本等类别消息
# isGroupChat=False表示非群聊消息
# @itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING], isGroupChat=False)
# def text_reply(msg):
# 	print("here we are!")
	# itchat.send('稍后会给您回复!', msg['FromUserName'])

# # 自动回复图片等类别消息
# # isGroupChat=False表示非群聊消息
# @itchat.msg_register([PICTURE, RECORDING, ATTACHMENT, VIDEO], isGroupChat=False)
# def download_files(msg):
# 	itchat.send('稍后会给您回复！', msg['FromUserName'])

# 自动处理添加好友申请
# @itchat.msg_register(FRIENDS)
# def add_friend(msg):
# 	itchat.add_friend(**msg['Text']) # 该操作会自动将新好友的消息录入，不需要重载通讯录
# 	itchat.send_msg(u'您好', msg['RecommendInfo']['UserName'])
    
# 自动回复文本等类别的群聊消息
# isGroupChat=True表示为群聊消息
@itchat.msg_register([TEXT], isGroupChat=True)
def group_reply_text(msg):
	# 消息来自于哪个群聊
	content = None
	if msg['Type'] == TEXT:
		content = msg['Content']
	elif msg['Type'] == SHARING:
		content = msg['Text']
	# print("------------group message----------")
	# print(msg)
	if not content:
		return
	if '@所有人' not in content:
		return

	if "\n- - - - - - - - - - - - - - -\n" in content:
		return

	chatroom_id = msg['FromUserName']
	# 消息并不是来自于需要同步的群
	my_lock.acquire()
	if chatroom_id not in chatroom_info.keys():
		my_lock.release()
		return
	dict_info = copy.deepcopy(chatroom_info.get(chatroom_id))
	my_lock.release()
	#print "chatroom_id" + chatroom_id
	# 发送者的昵称
	username = msg['ActualNickName']

	limit_user_list=dict_info.get('limit_user')
	if limit_user_list :
		b_find = False
		for v in limit_user_list:
			if v in username:
				b_find = True
				break
		if not b_find:
			return

	group_name= dict_info.get('name')
	content_hash=hashlib.md5(content.encode('utf-8')).hexdigest()
	logging.info("receive message,username:{},group_name:{},content:{},hash:{}".format(username,group_name,content,content_hash))
	if content_hash in msg_hash_cache_dict.keys():
		time_diff=datetime.datetime.now() - msg_hash_cache_dict[content_hash]
		diff_secs=time_diff.total_seconds()
		if diff_secs < 10 * 60:  #10分钟内连续的2条相同的消息不在转发
			logging.info("this message has been dispatched!!! ignore, diff_secs:{}".format(diff_secs))
			return

	msg_hash_cache_dict[content_hash]=datetime.datetime.now()
	
	undelivery_item_list=dict_info.get('dst')
	delivery_item_complete_list=[]
	# 根据消息类型转发至其他需要同步消息的群聊
	if msg['Type'] == TEXT:
		logging.info("start dispatch message")
		for item in undelivery_item_list:
			if item in delivery_item_complete_list:
				continue
			delivery_item_complete_list.append(item)
			itchat.send('%s—%s 的消息:\n%s' % (group_name,username, content), item)
			time.sleep(random.uniform(1.0,2.0))
	elif msg['Type'] == SHARING:
		for item in undelivery_item_list:
			if item in delivery_item_complete_list:
				continue
			delivery_item_complete_list.append(item)
			itchat.send('%s-%s 分享：\n%s\n%s' % (group_name,username, content, msg['Url']), item)
			time.sleep(random.uniform(1.0,2.0))

# 自动回复图片等类别的群聊消息
# isGroupChat=True表示为群聊消息          
@itchat.msg_register([PICTURE, ATTACHMENT, VIDEO], isGroupChat=True)
def group_reply_media(msg):
	# print("hahha")
	return
	# 消息来自于哪个群聊
	chatroom_id = msg['FromUserName']
	# 发送者的昵称
	username = msg['ActualNickName']
	
	# 消息并不是来自于需要同步的群
	if not chatroom_id in chatroom_info.keys():
		return

	# 如果为gif图片则不转发
	if msg['FileName'][-4:] == '.gif':
		return

	dict_info = chatroom_info.get(chatroom_id)
	# 下载图片等文件
	msg['Text'](msg['FileName'])
	# 转发至其他需要同步消息的群聊
	for item in dict_info.get('dst'):
		itchat.send('@%s@%s' % ({'Picture': 'img', 'Video': 'vid'}.get(msg['Type'], 'fil'), msg['FileName']), item)


logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(message)s')
# 扫二维码登录
itchat.auto_login(hotReload=True)

updateRoomID()
scheduler = BackgroundScheduler()
scheduler.add_job(updateRoomID, 'interval', seconds=30 * 60)
scheduler.start()

# 开始监测
itchat.run()