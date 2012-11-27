#! /usr/bin/env python

import argparse
import requests
import json

def get_args():
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

def fetch_url(url):
	print url
	if url.find('https://api.github.com') == 0:
		r = requests.get(url + '?access_token=' + get_args().token)
		print r.text

def url_base():
	return 'https://api.github.com/'

def fetch_repo():
	fetch_url( url_base() + 'repos/' + get_args().user + '/' + get_args().repo )

def main():
	args = get_args()

	print args

	fetch_url('henry')
	fetch_url('https://api.github.com/rate_limit')
	fetch_repo()

if __name__ == "__main__":
	main()
