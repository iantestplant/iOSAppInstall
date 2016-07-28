#  Create the virtual python environment

python virtualenv.py venv
venv/bin/pip install -r requirements.txt
echo "To run the service execute: ./venv/bin/python iosinstService.py"

