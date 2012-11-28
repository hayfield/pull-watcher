#! /usr/bin/env python

import argparse
import requests
import json
from datetime import datetime
import os
import zipfile
import subprocess

READ_ARGS = False
MASTER_SHA = False

class MessageType:
	NOT_MERGED_MASTER = 1
	INSTALL_DEPS_FAIL = 2
	BUILD_FAIL = 3
	RUN_TESTS_FAIL = 4
	BUILD_SUCCESSFUL = 5
	PENDING = 6

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
	if type == MessageType.NOT_MERGED_MASTER:
		msg += 'The contents of master have not been merged into this branch. No building or testing has been attempted.\n'
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
			lastSha = pull_req_get_last_sha(num)
			isMerged = merged_master( master_sha(), shaHead )
			# check to see if master has been properly merged
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
				# if master hasn't been merged in, tell someone to sort it out
				post_build_status(num, MessageType.NOT_MERGED_MASTER, shaHead)

def zipball_file(sha):
	return os.path.join(repo_build_dir(), sha + '.zip')

def zipball_extract_dir_name(sha):
	return get_args().user + '-' + get_args().repo + '-' + sha

def zipball_extract_dir(sha):
	return os.path.join(repo_build_dir(), zipball_extract_dir_name(sha))

def download_zipball(num, sha):
	post_build_status(num, MessageType.PENDING, sha)
	headers = {'Authorization': 'token ' + get_args().token}
	r = requests.get( repo_url_base() + '/zipball/' + sha, headers=headers )
	store_val( zipball_file(sha), r.content )
	file = zipfile.ZipFile(zipball_file(sha))
	file.extractall(repo_build_dir())
	build(num, sha)

def build_output(sha, name, type):
	dir = os.path.join(pull_reqs_dir(), sha)
	setup_folder(dir)
	return os.path.join(dir, name + '-' + type + '.out')

def clean_data(sha):
	p = subprocess.Popen(['rm', sha + '.zip'], cwd=repo_build_dir())
	p.wait()
	p = subprocess.Popen(['rm', '-r', zipball_extract_dir_name(sha)], cwd=repo_build_dir())
	p.wait()

def build(num, sha):
	fout = open(build_output(sha, 'installdeps', 'out'), 'w')
	ferr = open(build_output(sha, 'installdeps', 'err'), 'w')
	p = subprocess.Popen(['make', 'install-deps'], stdout=fout, stderr=ferr, cwd=zipball_extract_dir(sha))
	p.wait()
	#print p.returncode

	if p.returncode != 0:
		post_build_status(num, MessageType.INSTALL_DEPS_FAIL, sha)
	else:
		fout = open(build_output(sha, 'buildall', 'out'), 'w')
		ferr = open(build_output(sha, 'buildall', 'err'), 'w')
		p = subprocess.Popen(['make', 'build-all'], stdout=fout, stderr=ferr, cwd=zipball_extract_dir(sha))
		p.wait()
		#print p.returncode

		if p.returncode != 0:
			post_build_status(num, MessageType.BUILD_FAIL, sha)
		else:
			fout = open(build_output(sha, 'testall', 'out'), 'w')
			ferr = open(build_output(sha, 'testall', 'err'), 'w')
			p = subprocess.Popen(['make', 'test-all'], stdout=fout, stderr=ferr, cwd=zipball_extract_dir(sha))
			p.wait()

			if p.returncode != 0:
				post_build_status(num, MessageType.RUN_TESTS_FAIL, sha)
			else:
				post_build_status(num, MessageType.BUILD_SUCCESSFUL, sha)

	clean_data(sha)

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

def build_dir():
	return os.path.join('..', 'build')

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
	return get_val(os.path.join('..', 'sha.elephant'), '')

def main():
	args = get_args()
	setup_folders()

	print args
	#post_pending_status(elephant_sha())
	#print repo_url_statuses(elephant_sha())
	fetch_repo()
	#build(1, elephant_sha())
	#fetch_pull_reqs()
	#fetch_url('https://api.github.com/rate_limit')
	#fetch_repo()

if __name__ == "__main__":
	main()
