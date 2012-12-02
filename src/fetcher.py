#!/usr/bin/env python

import argparse
import requests
import json
from datetime import datetime
import os
import zipfile
import subprocess

READ_ARGS = False

class MessageType:
	NOT_MERGED_BASE = 1
	INSTALL_DEPS_FAIL = 2
	BUILD_FAIL = 3
	RUN_TESTS_FAIL = 4
	BUILD_SUCCESSFUL = 5
	PENDING = 6
	MAKE_FAIL = 7

def get_args():
	global READ_ARGS

	if type(READ_ARGS) is bool:
		parser = argparse.ArgumentParser(description='Create a fetcher.')
		parser.add_argument('-user', type=str, nargs=1)
		parser.add_argument('-repo', type=str, nargs=1)
		parser.add_argument('-token', type=str, nargs=1)
		parser.add_argument('-maketargets', type=str, nargs=argparse.REMAINDER)
		args = parser.parse_args()

		args.user = args.user[0]
		args.repo = args.repo[0]
		#print args

		if args.token == None:
			f = open(os.path.join('..', 'github-token.elephant'), 'r')
			args.token = f.readline()
			f.close()
		else:
			args.token = args.token[0]

		if args.maketargets == None:
			args.maketargets = []

		READ_ARGS = args
	
	return READ_ARGS

def fetch_url(url):
	print url
	if url.find( url_base() ) == 0:
		headers = {'Authorization': 'token ' + get_args().token}
		r = requests.get( url, headers=headers )
		return r

def url_base():
	return 'https://api.github.com/'

def get_val(file, defaultValue):
	if os.path.exists(file):
		f = open(file, 'r')
		line = f.readline()
		f.close()
		return line
	else:
		return defaultValue

def store_val(file, val):
	f = open(file, 'w')
	f.write(val)
	f.close()

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
	if dateNow > lastDate:
		repo_store_last_update(dateNow)
		fetch_pull_reqs()

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

def repo_url_statuses(sha):
	return repo_url_base() + '/statuses/' + sha + '?access_token=' + get_args().token

def post_status(state, desc, sha):
	data = {"state": state, "description": desc}
	r = requests.post( repo_url_statuses(sha), data=json.dumps(data) )

def post_pending_status(sha):
	post_status('pending', 'Downloading content and running build', sha)

def post_success_status(sha):
	post_status('success', 'Build and tests ran successfully', sha)

def post_error_status(sha, msg):
	post_status('error', msg, sha)

def post_failure_status(sha, msg):
	post_status('failure', msg, sha)

def post_build_status(num, type, sha):
	msg = ''
	if type == MessageType.NOT_MERGED_BASE:
		msg += 'The contents of the base branch have not been merged into this branch. No building or testing has been attempted.\n'
		post_failure_status(sha, msg)
	elif type == MessageType.INSTALL_DEPS_FAIL:
		msg += 'There was a problem installing dependencies. Building the code and running tests was not attempted.\n'
		post_error_status(sha, msg)
	elif type == MessageType.BUILD_FAIL:
		msg += 'There code did not build successfully. Tests not run.\n'
		post_error_status(sha, msg)
	elif type == MessageType.RUN_TESTS_FAIL:
		msg += 'The tests did not run successfully.\n'
		post_error_status(sha, msg)
	elif type == MessageType.BUILD_SUCCESSFUL:
		post_success_status(sha)
	elif type == MessageType.PENDING:
		post_pending_status(sha)

def fetch_pull_reqs():
	r = fetch_url( repo_url_base() + '/pulls' )
	data = json.loads(r.text)
	# loop through the pull reqs
	for pullReq in data:
		# only care if the pull req is open
		if pullReq['state'] == 'open':
			# with each one...
			num = pullReq['number']
			shaHead = pullReq['head']['sha']
			shaBase = pullReq['base']['sha']
			lastSha = pull_req_get_last_sha(num)
			isMerged = merged_base( shaBase, shaHead )
			# check to see if the base has been properly merged
			if isMerged:
				updateDate = pullReq['updated_at'][:-1]
				dateNow = datetime.strptime(updateDate, '%Y-%m-%dT%H:%M:%S')
				lastDate = datetime.strptime(pull_req_get_last_update(num), '%Y-%m-%dT%H:%M:%S')
				# check that it's been updated since we last checked
				if dateNow > lastDate:
					pull_req_store_last_update(num, dateNow)
					
					# and that the commits inside have changed
					if shaHead != lastSha:
						pull_req_store_last_sha(num, shaHead)
						# all seems ok, so go on to download and build it
						download_zipball(num, shaHead)
							
			else:
				# if the base hasn't been merged in, tell someone to sort it out
				post_build_status(num, MessageType.NOT_MERGED_BASE, shaHead)

def zipball_file(sha):
	return os.path.join(repo_build_dir(), sha + '.zip')

def zipball_extract_dir_name(sha):
	return get_args().user + '-' + get_args().repo + '-' + sha

def zipball_extract_dir(sha):
	return os.path.join(repo_build_dir(), zipball_extract_dir_name(sha))

def download_zipball(num, sha):
	post_build_status(num, MessageType.PENDING, sha)
	r = fetch_url( repo_url_base() + '/zipball/' + sha )
	store_val( zipball_file(sha), r.content )
	file = zipfile.ZipFile(zipball_file(sha))
	file.extractall(repo_build_dir())
	build(num, sha)

def build_output(sha, name, type):
	dir = os.path.join(pull_reqs_dir(), sha)
	setup_folder(dir)
	return os.path.join(dir, name + '-' + type + '.out')

def zip_dir(dir):
	zip = zipfile.ZipFile(dir + '.zip', 'w', zipfile.ZIP_DEFLATED)
	rootlen = len(dir) + 1
	for base, dirs, files in os.walk(dir):
		for file in files:
			fn = os.path.join(base, file)
			zip.write(fn, fn[rootlen:])

def clean_data(sha):
	p = subprocess.Popen(['rm', sha + '.zip'], cwd=repo_build_dir())
	p.wait()
	p = subprocess.Popen(['rm', '-r', zipball_extract_dir_name(sha)], cwd=repo_build_dir())
	p.wait()
	zip_dir(os.path.join(pull_reqs_dir(), sha))

def build(num, sha):
	msg = ''
	for target in get_args().maketargets:
		fout = open(build_output(sha, target, 'out'), 'w')
		ferr = open(build_output(sha, target, 'err'), 'w')
		p = subprocess.Popen(['make', target], stdout=fout, stderr=ferr, cwd=zipball_extract_dir(sha))
		p.wait()

		#print p.returncode
		if p.returncode != 0:
			msg += 'Error making ' + target + ' - returned: ' + str(p.returncode) + '\n'

		fout.close()
		ferr.close()

	if len(msg) == 0:
		post_build_status(num, MessageType.BUILD_SUCCESSFUL, sha)
	else:
		post_error_status(sha, msg)

	clean_data(sha)

def merged_base(base, head):
	r = fetch_url( repo_url_base() + '/compare/' + base + '...' + head )
	data = json.loads(r.text)
	if data['behind_by'] > 0:
		return False

	return True

def data_dir():
	return os.path.join('data')

def repo_dir():
	return os.path.join(data_dir(), get_args().user, get_args().repo)

def pull_reqs_dir():
	return os.path.join(repo_dir(), 'pull-requests')

def build_dir():
	return os.path.join('build')

def repo_build_dir():
	return os.path.join( build_dir(), get_args().repo )

def setup_folder(name):
	if not os.path.exists(name):
		os.makedirs(name)

def setup_folders():
	folders = [data_dir(), repo_dir(), pull_reqs_dir(), build_dir(), repo_build_dir()]

	for folder in folders:
		setup_folder(folder)

def elephant_sha():
	return elephant_val('sha')

def elephant_val(name):
	return get_val(os.path.join('..', name + '.elephant'), '')

def main():
	args = get_args()
	setup_folders()

	print args
	fetch_repo()

if __name__ == "__main__":
	main()
