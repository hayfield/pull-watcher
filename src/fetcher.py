#! /usr/bin/env python

import argparse
import requests

def get_args():
	parser = argparse.ArgumentParser(description='Create a fetcher.')
	parser.add_argument('-u', type=str, nargs=1)
	parser.add_argument('-repo', type=str, nargs=1)
	parser.add_argument('-token', type=str, nargs=1)
	args = parser.parse_args()

	print args

	if args.token == None:
		f = open('../github-token.elephant', 'r')
		args.token = f.readline()

	return args

def main():
	args = get_args()

	print args

if __name__ == "__main__":
	main()
