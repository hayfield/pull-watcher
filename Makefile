install-deps:
	curl http://python-distribute.org/distribute_setup.py | sudo python
	curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | sudo python
	sudo pip install requests
