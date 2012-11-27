#! /usr/bin/env python

import argparse
import requests
import json
from datetime import datetime
import os

READ_ARGS = None

def get_args():
	global READ_ARGS

	if READ_ARGS == None:
		parser = argparse.ArgumentParser(description='Create a fetcher.')
		parser.add_argument('-user', type=str, nargs=1)
		parser.add_argument('-repo', type=str, nargs=1)
		parser.add_argument('-token', type=str, nargs=1)
		args = parser.parse_args()

		args.user = args.user[0]
		args.repo = args.repo[0]
		print args

		if args.token == None:
			f = open('../github-token.elephant', 'r')
			args.token = f.readline()
		else:
			args.token = args.token[0]

		return args
	else:
		return READ_ARGS

def fetch_url(url):
	print url
	if url.find('https://api.github.com') == 0:
		r = requests.get(url + '?access_token=' + get_args().token)
		print r.text
		return r

def url_base():
	return 'https://api.github.com/'

def fetch_repo():
	r = fetch_url( url_base() + 'repos/' + get_args().user + '/' + get_args().repo )
	data = json.loads(r.text)
	updateDate = data['updated_at']
	date = datetime.strptime('2012-11-27T16:22:34Z', '%Y-%m-%dT%H:%M:%SZ')
	print date

def data_dir():
	return os.path.join('..', 'data')

def repo_dir():
	return os.path.join(data_dir(), get_args().user, get_args().repo)

def setup_folders():
	# the main data folder
	dataDir = data_dir()
	if not os.path.exists(dataDir):
		os.makedirs(dataDir)

	# the repo folder
	repoDir = repo_dir()
	if not os.path.exists(repoDir):
		os.makedirs(repoDir)

def main():
	args = get_args()

	print args

	fetch_url('henry')
	fetch_url('https://api.github.com/rate_limit')
	fetch_repo()
	setup_folders()

if __name__ == "__main__":
	main()
