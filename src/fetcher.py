#! /usr/bin/env python

import argparse
import requests
import json
from datetime import datetime
import os

READ_ARGS = False
MASTER_SHA = False

class MessageType:
	NOT_MERGED_MASTER=1

def get_args():
	global READ_ARGS

	if type(READ_ARGS) is bool:
		parser = argparse.ArgumentParser(description='Create a fetcher.')
		parser.add_argument('-user', type=str, nargs=1)
		parser.add_argument('-repo', type=str, nargs=1)
		parser.add_argument('-token', type=str, nargs=1)
		args = parser.parse_args()

		args.user = args.user[0]
		args.repo = args.repo[0]
		print args

		if args.token == None:
			f = open(os.path.join('..', 'github-token.elephant'), 'r')
			args.token = f.readline()
		else:
			args.token = args.token[0]

		READ_ARGS = args
	
	return READ_ARGS

def fetch_url(url):
	print url
	if url.find('https://api.github.com') == 0:
		r = requests.get(url + '?access_token=' + get_args().token)
		#print r.text
		return r

def url_base():
	return 'https://api.github.com/'

def get_val(file, defaultValue):
	if os.path.exists(file):
		f = open(file, 'r')
		return f.readline()
	else:
		return defaultValue

def store_val(file, val):
	f = open(file, 'w')
	f.write(val)

def repo_url_base():
	return url_base() + 'repos/' + get_args().user + '/' + get_args().repo

def repo_last_update_file():
	return os.path.join(repo_dir(), 'last-update')

def repo_get_last_update():
	return get_val( repo_last_update_file(), datetime.min.isoformat() )

def repo_store_last_update(lastUpdate):
	store_val( repo_last_update_file(), lastUpdate.isoformat() )

def fetch_repo():
	r = fetch_url( repo_url_base() )
	data = json.loads(r.text)
	updateDate = data['updated_at'][:-1]
	dateNow = datetime.strptime(updateDate, '%Y-%m-%dT%H:%M:%S')
	lastDate = datetime.strptime(repo_get_last_update(), '%Y-%m-%dT%H:%M:%S')
	if dateNow > lastDate or True:
		repo_store_last_update(dateNow)
		fetch_pull_reqs()

def master_sha():
	global MASTER_SHA
	
	if type(MASTER_SHA) is bool:
		r = fetch_url( repo_url_base() + '/git/refs/heads/master' )
		data = json.loads(r.text)
		MASTER_SHA = data['object']['sha']

	return MASTER_SHA
	

def pull_req_last_update_file(num):
	return os.path.join(pull_reqs_dir(), 'last-update-' + str(num))

def pull_req_get_last_update(num):
	return get_val( pull_req_last_update_file(num), datetime.min.isoformat() )

def pull_req_store_last_update(num, lastUpdate):
	store_val( pull_req_last_update_file(num), lastUpdate.isoformat() )

def pull_req_last_sha_file(num):
	return os.path.join(pull_reqs_dir(), 'last-sha-' + str(num))

def pull_req_get_last_sha(num):
	return get_val( pull_req_last_sha_file(num), '' )

def pull_req_store_last_sha(num, lastSha):
	store_val( pull_req_last_sha_file(num), lastSha )

def pull_req_error_status(num, err):
	return 5

def fetch_pull_reqs():
	r = fetch_url( repo_url_base() + '/pulls' )
	data = json.loads(r.text)
	# loop through the pull reqs
	for pullReq in data:
		num = pullReq['number']
		updateDate = pullReq['updated_at'][:-1]
		dateNow = datetime.strptime(updateDate, '%Y-%m-%dT%H:%M:%S')
		lastDate = datetime.strptime(pull_req_get_last_update(num), '%Y-%m-%dT%H:%M:%S')
		# with each one, check that it's been updated since we last checked
		if dateNow > lastDate or True:
			pull_req_store_last_update(num, dateNow)
			shaHead = pullReq['head']['sha']
			lastSha = pull_req_get_last_sha(num)
			# and that the commits inside have changed
			if shaHead != lastSha or True:
				pull_req_store_last_sha(num, shaHead)
				# if it's open and properly merged into master
				if pullReq['state'] == 'open' and merged_master( master_sha(), shaHead ):
					# do stuff
					print 'hi'
				else:
					# if master hasn't been merged in, tell someone to sort it out
					pull_req_error_status(num, MessageType.NOT_MERGED_MASTER)


	#updateDate = data['updated_at'][-1]
	#dateNow = datetime.strptime(updateDate, '%Y-%m-%dT%H:%M:%S')
	#lastDate = datetime.strptime(repo_get_last_update(), '%Y-%m-%dT%H:%M:%S')

def merged_master(base, head):
	r = fetch_url( repo_url_base() + '/compare/' + base + '...' + head )
	data = json.loads(r.text)
	if data['behind_by'] > 0:
		return False

	return True

def data_dir():
	return os.path.join('..', 'data')

def repo_dir():
	return os.path.join(data_dir(), get_args().user, get_args().repo)

def pull_reqs_dir():
	return os.path.join(repo_dir(), 'pull-requests')

def setup_folders():
	folders = [data_dir(), repo_dir(), pull_reqs_dir()]

	for folder in folders:
		if not os.path.exists(folder):
			os.makedirs(folder)

def main():
	args = get_args()
	setup_folders()

	print args

	fetch_pull_reqs()
	#fetch_url('https://api.github.com/rate_limit')
	#fetch_repo()

if __name__ == "__main__":
	main()
