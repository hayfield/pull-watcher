#! /usr/bin/env python

import argparse

def main():
	parser = argparse.ArgumentParser(description='Create a fetcher.')
	parser.add_argument('-u', type=str, nargs=1)
	parser.add_argument('-repo', type=str, nargs=1)
	args = parser.parse_args()

	print args
	print args.u[0]
	print args.repo[0]
	print('Hello World!')

if __name__ == "__main__":
	main()
